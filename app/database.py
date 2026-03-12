import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. 로컬 환경용 .env 로드 (실전 서버에서는 무시됨)
load_dotenv()

# 2. 시스템 환경 변수에서 DATABASE_URL을 가져옴
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 3. [중요] Railway/Heroku 등의 PostgreSQL 주소 호환성 처리
# Railway가 주는 'postgres://'는 SQLAlchemy 1.4+에서 'postgresql://'로 바꿔줘야 에러가 안 납니다.
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 4. 방어 코드: 만약 주소가 없다면 에러 메시지를 명확히 출력
if not SQLALCHEMY_DATABASE_URL:
    print("❌ 에러: DATABASE_URL 환경 변수를 찾을 수 없습니다.")
    # 로컬 테스트용 백업 주소 (비밀번호는 지호님 것으로 수정하세요)
    # SQLALCHEMY_DATABASE_URL = "postgresql://postgres:1234@localhost/toss_baseball"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()