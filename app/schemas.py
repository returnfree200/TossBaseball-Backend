from pydantic import BaseModel, ConfigDict
from datetime import date, time, datetime
from typing import List, Optional

# --- 1. 유저 관련 (User) ---
class UserCreate(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    secret_key: str

    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    username: str
    password: str

# --- 2. 팀 관련 (TeamDTO) ---
class TeamDTO(BaseModel):
    id: int
    name: str
    rank: Optional[int] = None
    logo_url: Optional[str] = None
    win: int
    lose: int
    draw: int

    model_config = ConfigDict(from_attributes=True)

# --- 3. 경기 관련 (MatchDTO) ---
class MatchCreate(BaseModel):
    secret_key: str  # 관리자 인증용
    team_a_id: int
    team_b_id: int
    game_date: date
    game_no: int
    start_time: time

class MatchUpdate(BaseModel):
    secret_key: str
    winner_team_id: Optional[int] = None
    end_time: Optional[time] = None

class MatchDTO(BaseModel):
    match_id: int
    team_a: TeamDTO
    team_b: TeamDTO
    game_date: date
    game_no: int
    start_time: time
    end_time: Optional[time] = None
    winner_team_id: Optional[int] = None
    is_canceled: bool
    
    # 선발 투수 정보
    a_starting_pitcher: Optional[str] = None
    a_pitcher_win: Optional[int] = None
    a_pitcher_draw: Optional[int] = None
    a_pitcher_lose: Optional[int] = None
    
    b_starting_pitcher: Optional[str] = None
    b_pitcher_win: Optional[int] = None
    b_pitcher_draw: Optional[int] = None
    b_pitcher_lose: Optional[int] = None

    # 예측 관련 정보
    predicted_team_id: Optional[int] = None
    team_a_prediction_count: int = 0
    team_b_prediction_count: int = 0

    model_config = ConfigDict(from_attributes=True)

# --- 4. 승부 예측 관련 (Prediction) ---
class PredictionRequest(BaseModel):
    secret_key: str
    predicted_team_id: int

class PredictionSearchRequest(BaseModel):
    secret_key: str

# --- 5. 공통 에러 응답 ---
class ErrorResponse(BaseModel):
    error: str