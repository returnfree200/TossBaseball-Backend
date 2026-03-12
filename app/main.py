import uuid
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from . import models, schemas, database, services
from app.database import get_db

# DB 테이블 생성 (실전 초기화)
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="TossBaseball")

# --- 회원가입 (2.1) ---
@app.post("/users", response_model=schemas.UserOut)
def register_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    # 1. 중복 유저 체크
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "username already exists"} # 명세서 규격 준수
        )
    
    # 2. 유저 생성 및 secret_key 발급
    # 실제 실전에선 비밀번호를 암호화(Hash)해야 하지만, 우선 명세를 따라 저장합니다.
    new_secret_key = str(uuid.uuid4())
    new_user = models.User(
        username=user.username,
        password=user.password, # 클라이언트가 해시해서 보낸다고 가정
        secret_key=new_secret_key,
        role="user" # 기본값
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# --- 로그인 (2.2) ---
@app.post("/users/login")
def login(request: schemas.LoginRequest, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(
        models.User.username == request.username,
        models.User.password == request.password
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid username or password"}
        )
    
    return {"secret_key": user.secret_key}


# --- 2.3 팀 목록 조회 (로그인 불필요) ---
@app.get("/teams", response_model=List[schemas.TeamDTO])
def get_teams(db: Session = Depends(database.get_db)):
    teams = db.query(models.Team).all()
    return teams

# --- 관리자 인증용 헬퍼 함수 (내실 가이드) ---
def verify_admin(secret_key: str, db: Session):
    user = db.query(models.User).filter(models.User.secret_key == secret_key).first()
    if not user:
        raise HTTPException(status_code=401, detail={"error": "invalid secret_key"})
    if user.role != 'admin':
        raise HTTPException(status_code=403, detail={"error": "admin only"})
    return user

# --- 2.4 경기 관리 (Admin 전용) ---
@app.post("/matches", status_code=201)
def create_match(match_data: schemas.MatchCreate, db: Session = Depends(database.get_db)):
    # 1. 관리자 권한 체크 (Body의 secret_key 사용)
    verify_admin(match_data.secret_key, db)
    
    # 2. 경기 등록
    new_match = models.Match(
        team_a_id=match_data.team_a_id,
        team_b_id=match_data.team_b_id,
        game_date=match_data.game_date,
        game_no=match_data.game_no,
        start_time=match_data.start_time
    )
    db.add(new_match)
    db.commit()
    db.refresh(new_match)
    return {"match_id": new_match.id}

# [PATCH] 경기 종료 처리 (결과 입력)
@app.patch("/matches/{match_id}/finish")
def finish_match(
    match_id: int, 
    request: schemas.MatchUpdate, 
    db: Session = Depends(database.get_db)
):
    # 1. 관리자 권한 확인
    verify_admin(request.secret_key, db)
    
    # 2. 경기 존재 확인
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail={"error": "match not found"})
    
    # 3. winner_team_id 검증: 해당 경기의 팀(A or B)이 맞는지 확인
    if request.winner_team_id not in [match.team_a_id, match.team_b_id]:
        raise HTTPException(
            status_code=422, 
            detail={"error": "winner_team_id is not part of this match"}
        )
    
    # 4. 결과 업데이트
    match.winner_team_id = request.winner_team_id
    match.end_time = request.end_time
    db.commit()
    
    return {"match_id": match_id}

# [PATCH] 경기 취소 처리
@app.patch("/matches/{match_id}/cancel")
def cancel_match(
    match_id: int, 
    request: schemas.PredictionRequest, # secret_key만 필요하므로 이 스키마 재사용 가능
    db: Session = Depends(database.get_db)
):
    # 1. 관리자 권한 확인
    verify_admin(request.secret_key, db)
    
    # 2. 경기 존재 확인
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail={"error": "match not found"})
    
    # 3. 취소 처리
    match.is_canceled = True
    db.commit()
    
    return {"match_id": match_id}


# --- 2.5 승부 예측 (Upsert) ---
@app.post("/matches/{match_id}/predictions")
def predict_match(
    match_id: int, 
    request: schemas.PredictionRequest, 
    db: Session = Depends(database.get_db)
):
    # 1. 유저 인증 (Body의 secret_key로 유저 찾기)
    user = db.query(models.User).filter(models.User.secret_key == request.secret_key).first()
    if not user:
        raise HTTPException(status_code=401, detail={"error": "invalid secret_key"})
    
    # 2. 경기 존재 여부 확인
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail={"error": "match not found"})
    
    # 3. 예측한 팀이 해당 경기의 팀인지 검증 (내실 체크!)
    if request.predicted_team_id not in [match.team_a_id, match.team_b_id]:
        raise HTTPException(
            status_code=422, 
            detail={"error": "predicted_team_id is not part of this match"}
        )
    
    # 4. Upsert 로직: 이미 예측했는지 확인
    existing_prediction = db.query(models.Prediction).filter(
        models.Prediction.user_id == user.id,
        models.Prediction.match_id == match_id
    ).first()
    
    if existing_prediction:
        # 기존 예측 수정 (Update)
        existing_prediction.predicted_team_id = request.predicted_team_id
    else:
        # 새로운 예측 생성 (Insert)
        new_prediction = models.Prediction(
            user_id=user.id,
            match_id=match_id,
            predicted_team_id=request.predicted_team_id
        )
        db.add(new_prediction)
    
    db.commit()
    return {"match_id": match_id, "predicted_team_id": request.predicted_team_id}

# --- 2.5 승부 예측 취소 추가 ---
@app.delete("/matches/{match_id}/predictions")
def cancel_prediction(
    match_id: int, 
    request: schemas.PredictionRequest, # secret_key 포함된 스키마 사용
    db: Session = Depends(database.get_db)
):
    # 1. 유저 인증
    user = db.query(models.User).filter(models.User.secret_key == request.secret_key).first()
    if not user:
        raise HTTPException(status_code=401, detail={"error": "invalid secret_key"})
    
    # 2. 예측 데이터 삭제
    prediction = db.query(models.Prediction).filter(
        models.Prediction.user_id == user.id,
        models.Prediction.match_id == match_id
    ).first()
    
    if not prediction:
        raise HTTPException(status_code=404, detail={"error": "prediction not found"})
        
    db.delete(prediction)
    db.commit()
    return {"deleted": True}


# --- 2.6 내가 예측한 경기 조회 ---
@app.post("/users/predictions", response_model=List[schemas.MatchDTO]) # 명세상 GET이지만 Body(secret_key)를 쓰므로 실무에선 POST 권장
def get_my_predictions(request: schemas.PredictionSearchRequest, db: Session = Depends(database.get_db)):
    # 1. 유저 인증
    user = db.query(models.User).filter(models.User.secret_key == request.secret_key).first()
    if not user:
        raise HTTPException(status_code=401, detail={"error": "invalid secret_key"})

    # 2. 복합 쿼리 (JOIN): 내가 예측한 경기 목록 가져오기
    # predictions -> matches -> teams(a, b) 순으로 조인합니다.
    results = (
        db.query(models.Match)
        .join(models.Prediction, models.Match.id == models.Prediction.match_id)
        .filter(models.Prediction.user_id == user.id)
        .all()
    )

    # 3. 데이터 가공 (DTO 변환)
    # 실전 팁: 각 경기별 투표 집계 등은 나중에 쿼리 최적화(subquery)로 개선할 수 있습니다.
    output = []
    for match in results:
        # 해당 경기의 내 예측 데이터 찾기
        my_pred = db.query(models.Prediction).filter(
            models.Prediction.user_id == user.id,
            models.Prediction.match_id == match.id
        ).first()

        # 팀별 전체 예측 수 집계
        count_a = db.query(models.Prediction).filter(
            models.Prediction.match_id == match.id,
            models.Prediction.predicted_team_id == match.team_a_id
        ).count()
        count_b = db.query(models.Prediction).filter(
            models.Prediction.match_id == match.id,
            models.Prediction.predicted_team_id == match.team_b_id
        ).count()

        # MatchDTO 규격에 맞게 조립
        output.append({
            "match_id": match.id,
            "team_a": match.team_a, # Relationship 설정 시 자동 로드
            "team_b": match.team_b,
            "game_date": match.game_date,
            "game_no": match.game_no,
            "start_time": match.start_time,
            "end_time": match.end_time,
            "winner_team_id": match.winner_team_id,
            "is_canceled": match.is_canceled,
            "predicted_team_id": my_pred.predicted_team_id if my_pred else None,
            "team_a_prediction_count": count_a,
            "team_b_prediction_count": count_b,
            # 선발 투수 정보 등은 생략하거나 모델 속성으로 추가
        })

    return output

from datetime import datetime

# --- 2.7 아직 시작되지 않은 경기 일정 조회 ---
@app.post("/matches/upcoming", response_model=List[schemas.MatchDTO])
def get_upcoming_matches(request: schemas.PredictionRequest, db: Session = Depends(database.get_db)):
    # 1. 유저 인증
    user = db.query(models.User).filter(models.User.secret_key == request.secret_key).first()
    if not user:
        raise HTTPException(status_code=401, detail={"error": "invalid secret_key"})

    # 2. 조건: 취소되지 않았고, 승리팀이 아직 없는(진행 전) 경기
    # 명세: game_date > today OR (game_date == today AND start_time > now)
    now = datetime.now()
    matches = db.query(models.Match).filter(
        models.Match.is_canceled == False,
        models.Match.winner_team_id == None,
        (models.Match.game_date > now.date()) | 
        ((models.Match.game_date == now.date()) & (models.Match.start_time > now.time()))
    ).all()
    
    # 3. DTO 변환 및 내 예측 데이터 결합 (2.6에서 만든 로직 활용)
    return [format_match_dto(m, user.id, db) for m in matches]

# --- 2.8 경기 결과가 확정된 경기 일정 조회 ---
@app.get("/matches/finished", response_model=List[schemas.MatchDTO])
def get_finished_matches(db: Session = Depends(database.get_db)):
    # 승리팀이 결정된 경기들만 조회
    matches = db.query(models.Match).filter(
        models.Match.winner_team_id != None,
        models.Match.is_canceled == False
    ).all()
    return [format_match_dto(m, None, db) for m in matches]

# --- 2.9 특정 팀의 전체 경기 조회 ---
@app.get("/teams/{team_id}/matches", response_model=List[schemas.MatchDTO])
def get_team_matches(team_id: int, db: Session = Depends(database.get_db)):
    # team_a 혹은 team_b에 해당 팀이 포함된 모든 경기
    matches = db.query(models.Match).filter(
        (models.Match.team_a_id == team_id) | (models.Match.team_b_id == team_id)
    ).all()
    return [format_match_dto(m, None, db) for m in matches]

# --- Helper: 반복되는 DTO 조립 로직을 함수로 분리 (내실 가이드) ---
def format_match_dto(match, user_id, db):
    # 각 팀별 예측 수 집계
    count_a = db.query(models.Prediction).filter(models.Prediction.match_id == match.id, models.Prediction.predicted_team_id == match.team_a_id).count()
    count_b = db.query(models.Prediction).filter(models.Prediction.match_id == match.id, models.Prediction.predicted_team_id == match.team_b_id).count()
    
    # 내 예측 정보 (로그인 시)
    my_pred = None
    if user_id:
        pred_obj = db.query(models.Prediction).filter(models.Prediction.user_id == user_id, models.Prediction.match_id == match.id).first()
        my_pred = pred_obj.predicted_team_id if pred_obj else None

    return {
        "match_id": match.id, "team_a": match.team_a, "team_b": match.team_b,
        "game_date": match.game_date, "game_no": match.game_no,
        "start_time": match.start_time, "end_time": match.end_time,
        "winner_team_id": match.winner_team_id, "is_canceled": match.is_canceled,
        "predicted_team_id": my_pred,
        "team_a_prediction_count": count_a, "team_b_prediction_count": count_b
    }

@app.post("/users/{user_id}/settle-test")
def settle_user_rating_test(user_id: int, is_correct: bool, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # services.py에 정의한 함수 호출
    user.rating = services.calculate_rating_change(user.rating, is_correct)
    user.total_predictions += 1
    
    db.commit()
    db.refresh(user)
    return {"username": user.username, "new_rating": user.rating}

# app/main.py

@app.on_event("startup")
def startup_event():
    from app.database import engine
    # 이 줄만 남겨두면, 이미 있는 테이블은 건드리지 않고 안전하게 유지됩니다.
    models.Base.metadata.create_all(bind=engine)
    print("🚀 서버가 안전한 모드로 시작되었습니다.")