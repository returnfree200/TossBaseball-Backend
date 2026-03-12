from sqlalchemy.orm import Session
from app import models

# 순수 계산 로직
def calculate_rating_change(current_rating: int, is_correct: bool):
    K = 32  # 점수 변동의 기본 폭 (스타크래프트의 K-Factor와 유사)
    
    if is_correct:
        # 정답 시: 1000점 기준 약 32점 상승
        new_rating = current_rating + K
    else:
        # 오답 시: 약 20점 하락 (상승폭보다 적게 잡아서 유저의 의욕을 유지)
        new_rating = current_rating - 20
        
    # 레이팅 하한선 설정 (예: 800점 밑으로는 안 내려감)
    return max(800, new_rating)

# 2. 실제 DB에 반영하는 서비스 로직 (엔진)
def settle_user_rating(db: Session, user_id: int, is_correct: bool):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None

    # 지호님의 계산 로직을 여기서 사용합니다!
    user.rating = calculate_rating_change(user.rating, is_correct)
    
    # 예측 횟수 증가 (있다면)
    if hasattr(user, 'total_predictions'):
        user.total_predictions += 1
        
    # main.py에서 db.commit()을 하므로 여기선 add만
    db.add(user)
    return user