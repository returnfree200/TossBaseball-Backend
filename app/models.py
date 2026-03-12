from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime, ForeignKey, Time, Date, func, Index
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)
    secret_key = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- 📈 레이팅 시스템 ---
    # 기본 1000점 시작 (스타크래프트/바둑 방식)
    rating = Column(Integer, default=1000, nullable=False)
    
    # 랭킹 산출을 위해 총 예측 횟수 정도는 남겨두는 게 좋습니다. (신뢰도 지표)
    total_predictions = Column(Integer, default=0, nullable=False)

class Team(Base):
    __tablename__ = "teams"
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    rank = Column(Integer, nullable=True)
    logo_url = Column(String, nullable=True)
    win = Column(Integer, default=0, nullable=False)
    lose = Column(Integer, default=0, nullable=False)
    draw = Column(Integer, default=0, nullable=False)


from sqlalchemy.orm import relationship # 상단에 추가되어 있는지 확인하세요!

class Match(Base):
    __tablename__ = "matches"
    id = Column(BigInteger, primary_key=True, index=True)

    # 1. 외래키 컬럼 정의
    team_a_id = Column(BigInteger, ForeignKey("teams.id"), nullable=False)
    team_b_id = Column(BigInteger, ForeignKey("teams.id"), nullable=False)
    winner_team_id = Column(BigInteger, ForeignKey("teams.id"), nullable=True)

    # 2. 관계(Relationship) 정의: 모호함을 없애기 위해 foreign_keys를 명시합니다.
    # 이 설정을 해야 match.team_a.name 처럼 데이터를 편하게 꺼낼 수 있습니다.
    team_a = relationship("Team", foreign_keys=[team_a_id], backref="matches_as_a")
    team_b = relationship("Team", foreign_keys=[team_b_id], backref="matches_as_b")
    winner_team = relationship("Team", foreign_keys=[winner_team_id])

    # 3. 경기 정보 컬럼
    game_date = Column(Date, nullable=False)
    game_no = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=True)
    is_canceled = Column(Boolean, default=False, nullable=False)

    # 4. 선발 투수 및 기록 정보 (지호님의 명세 반영)
    a_starting_pitcher = Column(String, nullable=True)
    a_pitcher_win = Column(Integer, default=0, nullable=False)
    a_pitcher_draw = Column(Integer, default=0, nullable=False)
    a_pitcher_lose = Column(Integer, default=0, nullable=False)

    b_starting_pitcher = Column(String, nullable=True)
    b_pitcher_win = Column(Integer, default=0, nullable=False)
    b_pitcher_draw = Column(Integer, default=0, nullable=False)
    b_pitcher_lose = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 인덱스 설정: 날짜와 경기 번호로 빠른 조회가 가능하게 합니다.
    __table_args__ = (
        Index("idx_matches_date_no", "game_date", "game_no"),
    )

class Prediction(Base):
    __tablename__ = "predictions"
    
    # 복합 기본키 (user_id + match_id): 한 유저는 경기당 한 번만 예측 가능!
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    match_id = Column(BigInteger, ForeignKey("matches.id", ondelete="CASCADE"), primary_key=True)
    
    predicted_team_id = Column(BigInteger, ForeignKey("teams.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


