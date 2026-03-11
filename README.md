# ⚾ TossBaseball (Official Backend)
**KBO 리그 승부 예측 시스템: 앱인토스(App-in-Toss) 플랫폼 등재용 공식 API 서버**

본 프로젝트는 프로야구 팬들을 위한 실시간 승부 예측 서비스를 제공하는 'TossBaseball'의 공식 백엔드 시스템입니다. '앱인토스' 플랫폼의 기술 검증을 마치고, 실전 배포 및 대규모 유저 참여를 고려한 고성능 집계 처리를 목표로 개발되었습니다.

## 🎯 실전 아키텍처 핵심 (Key Engineering)

### 1. 관계형 데이터 모델링 (RDBMS Integrity)
- **Multi-Foreign Key Mapping**: 한 경기에 참여하는 두 팀(Home/Away)과 승리 팀 정보를 동일한 `teams` 테이블에서 참조하되, SQLAlchemy의 `relationship`과 `foreign_keys` 설정을 통해 데이터 모호성을 제거했습니다.
- **Strict Data Validation**: 서버 레벨에서 `predicted_team_id`가 실제 해당 경기에 배정된 팀인지 검증하여 논리적 오류를 원천 차단합니다.

### 2. 성능 최적화 (Performance & UX)
- **Atomic Upsert Logic**: `(user_id, match_id)` 복합키를 활용하여 예측 생성과 수정을 단일 API(`POST`)로 통합, 프론트엔드 연동의 복잡도를 낮추고 데이터 중복을 방지했습니다.
- **Index-Driven Query**: `game_date`와 `game_no`에 복합 인덱스를 적용하여 대량의 경기 일정 중 '다가올 경기(Upcoming)'를 밀리초 단위로 필터링합니다.

### 3. 보안 및 인증 (Security)
- **Secret Key Based Auth**: 회원가입 시 고유 `secret_key`를 발급하여 모든 API 요청 시 안전한 인증을 수행하며, RBAC(Role-Based Access Control)를 통해 관리자 전용 기능을 보호합니다.

## 🛠 Tech Stack
- **Framework**: FastAPI (Python 3.13)
- **ORM**: SQLAlchemy 2.0
- **Database**: PostgreSQL 16+
- **Infrastructure**: App-in-Toss Platform Deployment Ready