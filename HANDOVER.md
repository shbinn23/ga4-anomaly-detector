# GA4 Anomaly Detector — AI 인수인계 프롬프트

> 이 문서는 프로젝트를 처음 접하는 AI 또는 개발자가 즉시 작업을 이어받을 수 있도록 작성된 완전한 컨텍스트 문서입니다.
> 작성 기준일: 2026-05-04

---

## 1. 프로젝트 개요 및 목적

**GA4 Anomaly Detector**는 Google Analytics 4(GA4) 트래픽 이상 징후를 자동으로 탐지하고 시각화하는 AI 모니터링 시스템이다.

### 배경

- 다수의 GA4 Property(웹사이트/앱)를 운영하며 트래픽 급락·급등을 매일 수동으로 확인하는 작업을 자동화하기 위해 제작
- N8N 워크플로우가 매일 GA4 데이터를 수집하여 이 API로 전송 → AI(Prophet)가 이상 여부를 판별 → Streamlit 대시보드에서 시각화

### 핵심 가치

- **자동화**: N8N이 스케줄링 → 사람이 수동 확인 불필요
- **AI 탐지**: Facebook Prophet 시계열 예측 기반 통계적 이상치 탐지
- **경량 배포**: GCP e2-micro(1GB RAM) 단일 서버에서 Docker Compose로 운영

---

## 2. 전체 기술 스택

| 레이어 | 기술 | 버전 | 비고 |
|---|---|---|---|
| API 프레임워크 | FastAPI | 0.128.8 | REST API 서버 |
| ASGI 서버 | Uvicorn | 0.39.0 | workers=1 (메모리 절약) |
| ML 라이브러리 | Prophet (Facebook) | 1.3.0 | 시계열 예측 + 신뢰구간 |
| Stan 컴파일러 | CmdStanPy | 1.3.0 | Prophet 백엔드, 빌드 시 컴파일 |
| 데이터 처리 | Pandas | 2.3.3 | DataFrame 변환 |
| 데이터 검증 | Pydantic | 2.12.5 | 요청/응답 스키마 |
| 설정 관리 | pydantic-settings | 2.11.0 | .env 파일 로드 |
| 대시보드 | Streamlit | 1.50.0 | 웹 UI |
| 차트 | Plotly | 6.6.0 | 인터랙티브 시계열 차트 |
| 환경변수 | python-dotenv | 1.2.1 | .env 파일 |
| 테스트 | pytest | 8.x | 단위 테스트 |
| 컨테이너 | Docker + Docker Compose | - | 2-컨테이너 구성 |
| 런타임 | Python | 3.11 (Docker) / 3.9 (로컬) | |
| 서버 | GCP e2-micro | - | 1GB RAM, 단일 인스턴스 |

---

## 3. 디렉토리 구조

```
ga4-anomaly-detector/
│
├── app/                          # FastAPI 백엔드 (핵심 패키지)
│   ├── main.py                   # FastAPI 앱 생성, 라우터 등록
│   ├── api/
│   │   └── routers/
│   │       ├── analyze.py        # POST /api/v1/analyze (분석 요청)
│   │       └── management.py     # GET /api/v1/health, POST /api/v1/reset
│   ├── core/
│   │   ├── config.py             # 환경변수 → Settings 객체 (싱글턴)
│   │   ├── dependencies.py       # FastAPI Depends 의존성 주입 팩토리
│   │   └── logging.py            # 로거 설정 (Prophet 로그 억제 포함)
│   ├── domain/
│   │   ├── models.py             # 도메인 내부 모델 (dataclass)
│   │   ├── schemas.py            # API 입출력 Pydantic 스키마
│   │   └── exceptions.py         # 커스텀 예외 클래스
│   ├── ml/
│   │   ├── base_detector.py      # 탐지기 추상 인터페이스 (ABC)
│   │   ├── prophet_detector.py   # Prophet 구현체
│   │   └── detector_factory.py   # 탐지기 생성 팩토리 (확장 포인트)
│   ├── services/
│   │   └── anomaly_service.py    # 비즈니스 로직 오케스트레이터
│   └── infrastructure/
│       ├── storage.py            # 저장소 추상 인터페이스 (ABC)
│       └── json_storage.py       # JSON 파일 저장소 구현체
│
├── dashboard/                    # Streamlit 대시보드 (별도 컨테이너)
│   ├── dashboard.py              # 메인 앱 진입점
│   ├── components/
│   │   └── charts.py             # Plotly 차트 렌더러
│   └── utils/
│       └── data_loader.py        # JSON 파일 로드 + 이상치 필터링
│
├── tests/
│   └── unit/
│       └── test_prophet_detector.py  # Prophet 탐지 단위 테스트
│
├── data/                         # 런타임 생성 (gitignore됨)
│   └── results_db.json           # 분석 결과 영속 저장소
│
├── static/reports/               # 런타임 생성 (현재 미사용)
│
├── Dockerfile.api                # API 멀티스테이지 빌드 (CmdStan 사전 컴파일)
├── Dockerfile.dashboard          # 대시보드 단순 빌드
├── docker-compose.yml            # 2-서비스 오케스트레이션
├── .dockerignore                 # Docker 빌드 제외 목록
│
├── requirements.txt              # 로컬 개발용 전체 의존성 (정상 버전)
├── requirements-api.txt          # API 컨테이너 전용 의존성 ⚠️ 버전 수정 필요
├── requirements-dashboard.txt    # 대시보드 컨테이너 전용 의존성 ⚠️ 버전 수정 필요
│
├── main.py                       # 루트 진입점 (로컬 개발용, reload=True)
├── __init__.py
├── .env                          # 실제 환경변수 (gitignore됨)
├── .env.example                  # 환경변수 템플릿
└── .gitignore
```

---

## 4. 핵심 기능 목록 및 설명

### 4-1. Prophet 기반 이상치 탐지
- GA4에서 수집한 N일치 일별 세션 수를 입력받아, Prophet이 **마지막 날을 제외**한 과거 데이터로 학습 후 신뢰구간을 예측
- 마지막 날의 실제값이 `yhat_lower` ~ `yhat_upper` 범위를 벗어나면 이상치(`is_anomaly=True`)로 판별
- `PROPHET_INTERVAL_WIDTH=0.80`이 기본값 → 낮출수록 탐지 민감도 증가

### 4-2. 결과 영속화 (JSON 파일 DB)
- 분석 결과는 `data/results_db.json`에 `{property_id: AnalysisResult}` 형태로 저장
- API와 대시보드가 Docker volume(`ga4_data`)을 공유하여 동일 파일을 참조
- `POST /api/v1/reset`으로 전체 초기화 가능

### 4-3. Streamlit 실시간 모니터링 대시보드
- `data/results_db.json`을 직접 읽어 이상치 Property만 필터링
- 상단: 전체 Property 수 / 이상 탐지 수 / 최종 업데이트 시각 메트릭 카드
- 3열 그리드로 이상 Property별 Plotly 차트 렌더링 (AI 신뢰구간 + 실제값 비교)
- 이상치 없으면 "모든 Property 정상" 메시지 표시

### 4-4. 의존성 주입(DI) 아키텍처
- `DetectorFactory`로 탐지 모델을 교체 가능하게 설계 (현재 Prophet만 지원)
- `BaseStorage` 추상 인터페이스로 저장소 교체 가능 (현재 JSONStorage만 구현)
- `get_anomaly_service()` Depends 함수가 매 요청마다 `ProphetDetector` + `JSONStorage` 조립

---

## 5. 데이터 플로우

```
[GA4 API]
    │
    │  (N8N이 매일 스케줄 실행)
    ▼
[N8N 워크플로우]
    │  HTTP POST /api/v1/analyze
    │  Body: {
    │    "property_id": "123456789",
    │    "property_name": "My Website",
    │    "target_date": "2026-05-04",
    │    "history_data": [
    │      {"date": "2026-04-01", "sessions": 1200},
    │      {"date": "2026-04-02", "sessions": 1350},
    │      ...  (최소 30일 이상 권장)
    │      {"date": "2026-05-04", "sessions": 450}   ← 탐지 대상 날짜
    │    ]
    │  }
    ▼
[FastAPI API 서버 :8000]
    │
    ├─ AnomalyRequest 스키마 검증 (Pydantic)
    │
    ├─ AnomalyService.run_analysis()
    │    │
    │    ├─ Pandas DataFrame 변환 (date→ds, sessions→y)
    │    │
    │    ├─ ProphetDetector.train_and_predict()
    │    │    ├─ df.iloc[:-1] 로 학습 (마지막 날 제외)
    │    │    └─ df[['ds']] 전체에 대해 예측 → yhat, yhat_lower, yhat_upper
    │    │
    │    ├─ check_anomaly(actual, lower, upper) → bool
    │    │
    │    └─ JSONStorage.save(property_id, result)
    │         └─ data/results_db.json 업데이트
    │
    └─ {"status": "success", "is_anomaly": true/false} 반환
                                    │
                                    │ (N8N이 결과로 Slack 알림 발송 등 후속 처리)
                                    ▼
                              [N8N 후속 처리]

[Docker Volume: ga4_data]
    │  (API가 쓴 results_db.json을 대시보드가 읽음)
    ▼
[Streamlit 대시보드 :8501]
    │
    ├─ load_anomaly_data() → results_db.json 전체 로드
    ├─ filter_anomalies() → is_anomaly=True 필터링
    └─ render_anomaly_chart() → Plotly 차트 렌더링
```

---

## 6. 주요 API 엔드포인트 목록 및 역할

모든 API는 `http://<SERVER_IP>:8000` 기준.

| 메서드 | 경로 | 역할 | 인증 |
|---|---|---|---|
| `GET` | `/` | 서버 상태 확인 (프로젝트명 반환) | 없음 |
| `POST` | `/api/v1/analyze` | GA4 세션 데이터 수신 → Prophet 분석 → 결과 저장 | 없음 |
| `GET` | `/api/v1/health` | 헬스체크 (Docker healthcheck용) | 없음 |
| `POST` | `/api/v1/reset` | `results_db.json` 전체 삭제 | 없음 |
| `GET` | `/docs` | FastAPI 자동 생성 Swagger UI | 없음 |

### `/api/v1/analyze` 요청 스키마

```json
{
  "property_id": "string",       // GA4 Property ID (저장 키로 사용)
  "property_name": "string",     // 표시용 이름
  "target_date": "YYYY-MM-DD",   // 분석 대상 날짜 (history_data의 마지막 날)
  "history_data": [
    { "date": "YYYY-MM-DD", "sessions": 1234.0 }
    // 최소 30개 이상 권장 (Prophet 학습 안정성)
  ]
}
```

### `/api/v1/analyze` 응답 스키마

```json
{ "status": "success", "is_anomaly": true }
```

> 상세 분석 결과(예측 시계열 전체)는 응답에 포함되지 않고 `results_db.json`에 저장됨.

---

## 7. 핵심 모듈별 역할 설명

### `app/core/config.py` — 설정 싱글턴
- `pydantic-settings`의 `BaseSettings`를 상속
- `.env` 파일을 자동 로드, 환경변수 우선
- `BASE_DIR`, `DATA_DIR`, `REPORT_DIR` 경로를 절대경로로 계산
- import 시점에 `data/`, `static/reports/` 디렉토리를 자동 생성

### `app/core/dependencies.py` — DI 팩토리
- `get_anomaly_service()` 함수가 `ProphetDetector` + `JSONStorage` → `AnomalyService`를 조립하여 반환
- 모델이나 저장소를 교체하려면 이 파일만 수정

### `app/ml/prophet_detector.py` — AI 탐지 엔진
- `BaseDetector` 추상 클래스를 구현
- `train_and_predict(df)`: `df.iloc[:-1]`(마지막 날 제외)으로 Prophet 학습 후 전체 시계열 예측
- `check_anomaly(actual, lower, upper)` → 실제값이 신뢰구간 밖이면 `True`
- `yearly_seasonality=False`, `daily_seasonality=False` (주간 패턴만 학습)

### `app/ml/detector_factory.py` — 확장 포인트
- 현재 `"prophet"` 타입만 지원
- 향후 `"timesfm"`, `"tft"` 등 다른 모델 추가 시 여기에 매핑만 추가하면 됨

### `app/services/anomaly_service.py` — 비즈니스 로직 오케스트레이터
- Pydantic 요청 객체 → Pandas DataFrame → 예측 → 이상치 판별 → 결과 저장의 전체 파이프라인 관리
- Detector와 Storage를 직접 생성하지 않고 주입받음 (테스트 용이)

### `app/infrastructure/json_storage.py` — 저장소 구현체
- `data/results_db.json`에 `{property_id: result_dict}` 구조로 저장
- `save()`: 전체 파일을 읽고 해당 키를 덮어쓴 뒤 전체 재저장
- `load_all()`: 파일 없으면 `{}` 반환 (안전한 초기화)
- `clear()`: 파일 자체를 삭제

### `app/domain/schemas.py` — API 경계 계약
- `AnomalyRequest`: API 입력 검증용 Pydantic 모델
- `AnalysisResult` + `ForecastData`: 저장 포맷 정의 (전체 시계열 포함)
- `DailySession`: history_data 배열의 원소 타입

### `dashboard/dashboard.py` — Streamlit 대시보드 진입점
- `load_anomaly_data()` → `filter_anomalies()` → 3열 그리드 렌더링
- `data/results_db.json`을 직접 읽음 (API를 HTTP로 호출하지 않음)
- 새로고침 시점에 파일을 다시 읽음 (자동 새로고침 없음)

### `dashboard/components/charts.py` — 차트 렌더러
- Plotly `go.Figure` 반환
- 4개 레이어: 신뢰구간 상단선 → 하단선(fill) → AI 기대선(점선) → 실제값(실선)
- 빨간색(`#F43F5E`) = 실제값, 보라색(`#6366F1`) = AI 예측선

---

## 8. 환경변수 목록 및 용도

`.env.example` 기준. `.env` 파일을 프로젝트 루트에 생성하여 사용.

| 변수명 | 기본값 | 용도 | 필수 여부 |
|---|---|---|---|
| `PROJECT_NAME` | `GA4 Anomaly Detector` | FastAPI 앱 타이틀, 로거 이름 | 선택 |
| `DB_FILE_NAME` | `results_db.json` | 분석 결과 저장 JSON 파일명 | 선택 |
| `PROPHET_INTERVAL_WIDTH` | `0.80` | Prophet 신뢰구간 폭 (0~1). 낮을수록 민감도 증가 | 선택 |

> **주의**: 현재 API 인증 관련 환경변수(API_KEY 등)가 없음. 서버가 공개 IP를 가질 경우 보안 취약점.

---

## 9. Docker 배포 구조

### 컨테이너 구성

```
┌─────────────────────────────────────────────┐
│               GCP e2-micro (1GB RAM)         │
│                                              │
│  ┌──────────────────┐  ┌──────────────────┐  │
│  │   ga4-api        │  │  ga4-dashboard   │  │
│  │   :8000          │  │  :8501           │  │
│  │   700MB limit    │  │  256MB limit     │  │
│  │                  │  │                  │  │
│  │  FastAPI         │  │  Streamlit       │  │
│  │  + Prophet       │  │  + Plotly        │  │
│  │  + CmdStan       │  │                  │  │
│  └────────┬─────────┘  └────────┬─────────┘  │
│           │                     │            │
│           └──────────┬──────────┘            │
│                      │                       │
│             [ga4_data volume]                 │
│             /app/data/results_db.json         │
└─────────────────────────────────────────────┘
```

### `Dockerfile.api` — 멀티스테이지 빌드

```
Stage 1 (builder):
  - python:3.11-slim + build-essential + cmake + libgomp1
  - pip install requirements-api.txt
  - cmdstanpy.install_cmdstan() → CmdStan 컴파일 (빌드 시 ~1.5GB 필요)
  - ⚠️ 반드시 로컬(Mac/고사양)에서 빌드 후 이미지를 서버로 전송할 것

Stage 2 (runtime):
  - python:3.11-slim + libgomp1만 설치
  - builder의 site-packages + /root/.cmdstan만 복사
  - COPY app/ ./app/
  - CMD uvicorn app.main:app --workers 1
```

### `Dockerfile.dashboard`

```
- python:3.11-slim
- pip install requirements-dashboard.txt
- COPY dashboard/ ./dashboard/
- WORKDIR /app/dashboard  (상대 import 때문에 필수)
- CMD streamlit run dashboard.py --server.port=8501
```

### 빌드 및 배포 절차

```bash
# 1. 로컬에서 이미지 빌드 (CmdStan 컴파일 포함, 약 10~20분 소요)
docker compose build

# 2. 이미지를 tar로 압축 후 서버 전송 (또는 Docker Hub/GCR 사용)
docker save ga4-anomaly-api:latest | gzip > ga4-api.tar.gz
docker save ga4-anomaly-dashboard:latest | gzip > ga4-dashboard.tar.gz
scp ga4-api.tar.gz ga4-dashboard.tar.gz <user>@<SERVER_IP>:~/

# 3. 서버에서 이미지 로드 및 실행
ssh <user>@<SERVER_IP>
docker load < ga4-api.tar.gz
docker load < ga4-dashboard.tar.gz
docker compose up -d
```

### 헬스체크
- API 컨테이너: 30초 간격, `http://localhost:8000/` 응답 확인
- 대시보드는 API `service_healthy` 상태 후 시작 (`depends_on`)

---

## 10. 현재 미완성 / 개선 필요 부분

### 🔴 즉시 수정 필요

| 항목 | 파일 | 문제 | 해결책 |
|---|---|---|---|
| requirements-api.txt 버전 오류 | `requirements-api.txt` | `fastapi==0.135.3`, `uvicorn==0.44.0` 등 존재하지 않는 버전 | `requirements.txt`의 수정된 버전으로 동기화 필요 |
| requirements-dashboard.txt 버전 오류 | `requirements-dashboard.txt` | `streamlit==1.55.0`, `python-dotenv==1.2.2` 등 존재하지 않는 버전 | 마찬가지로 존재하는 버전으로 수정 필요 |

> `requirements.txt`는 올바른 버전으로 이미 수정됨. Docker 빌드 전 반드시 두 파일도 수정할 것.

**올바른 버전 (requirements.txt 기준):**
```
# requirements-api.txt 수정본
fastapi==0.128.8
uvicorn==0.39.0
pydantic==2.12.5
pydantic-settings==2.11.0
python-dotenv==1.2.1
prophet==1.3.0
pandas==2.3.3

# requirements-dashboard.txt 수정본
streamlit==1.50.0
pandas==2.3.3
plotly==6.6.0
python-dotenv==1.2.1
```

### 🟡 구조적 개선 필요

1. **API 인증 없음**
   - 현재 모든 엔드포인트가 인증 없이 공개됨
   - 최소한 `X-API-Key` 헤더 인증 추가 필요
   - `POST /api/v1/reset`은 특히 위험 (누구나 DB 초기화 가능)

2. **저장소가 JSON 파일**
   - 동시 요청 시 race condition 가능성 (N8N이 여러 Property를 병렬로 전송 시)
   - SQLite 또는 PostgreSQL 전환 권장

3. **대시보드 자동 새로고침 없음**
   - Streamlit `st.rerun()` + `time.sleep()` 루프 또는 `st.autorefresh` 적용 필요
   - 현재는 브라우저 수동 새로고침 필요

4. **`static/reports/` 디렉토리 미사용**
   - `config.py`에서 생성하나 실제로 아무 기능도 없음
   - PDF/HTML 리포트 생성 기능 추가 예정이었던 것으로 보임

5. **N8N 연동 정보 코드베이스에 없음**
   - N8N 워크플로우 설정 (어느 GA4 Property를 어떻게 수집하는지)이 코드베이스에 문서화되지 않음

6. **CORS 설정 없음**
   - 브라우저에서 직접 API 호출 시 CORS 에러 발생
   - `fastapi.middleware.cors.CORSMiddleware` 추가 필요

7. **에러 핸들러 미등록**
   - `DetectionFailedError`, `InfrastructureError` 커스텀 예외가 정의되어 있으나
     `app/main.py`에 `@app.exception_handler` 등록이 누락됨

---

## 11. 서버 정보

| 항목 | 값 |
|---|---|
| 클라우드 | GCP (Google Cloud Platform) |
| 인스턴스 타입 | e2-micro |
| RAM | 1GB |
| API 포트 | `8000` (외부 공개) |
| 대시보드 포트 | `8501` (외부 공개) |
| 컨테이너 런타임 | Docker + Docker Compose |
| 서버 IP | 운영자에게 직접 확인 (코드베이스에 미포함) |
| SSH 접속 | `ssh <user>@<SERVER_IP>` |

> **GCP 방화벽 규칙**: 8000, 8501 포트를 인바운드 허용해야 외부에서 접근 가능.
> VPC 방화벽 또는 OS 방화벽(`ufw`) 모두 확인할 것.

---

## 12. 로컬 개발 환경 설정

```bash
# 1. 저장소 클론
git clone https://github.com/shbinn23/ga4-anomaly-detector.git
cd ga4-anomaly-detector

# 2. 가상환경 생성 (Python 3.9+)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경변수 설정
cp .env.example .env
# .env 파일은 기본값으로 동작 가능 (수정 불필요)

# 5. API 서버 실행 (루트 main.py로 실행, reload 모드)
python main.py
# 또는
uvicorn app.main:app --reload --port 8000

# 6. 대시보드 실행 (별도 터미널)
cd dashboard
streamlit run dashboard.py

# 7. 테스트 실행
pytest tests/ -v
```

---

## 13. N8N 연동 가이드

N8N에서 이 API를 호출하는 HTTP Request 노드 설정:

```
Method: POST
URL: http://<SERVER_IP>:8000/api/v1/analyze
Headers:
  Content-Type: application/json
Body (JSON):
{
  "property_id": "{{ $json.propertyId }}",
  "property_name": "{{ $json.propertyName }}",
  "target_date": "{{ $today.format('YYYY-MM-DD') }}",
  "history_data": {{ $json.historySessions }}
}
```

`history_data`는 `[{"date": "YYYY-MM-DD", "sessions": 숫자}]` 배열.
**최소 30개 이상**의 데이터 포인트 권장 (Prophet 학습 안정성).

---

*문서 끝 — 이 파일을 기반으로 작업을 이어받아 주세요.*
