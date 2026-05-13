# 작업 일지

> 이 문서는 개발 진행 과정, 기획 의도, 설계 결정, 검증 결과를 시간순으로 기록한다.
> 프로젝트 전체 구조와 운영 맥락은 `HANDOVER.md`, 작업 원칙은 `AGENTS.md`를 참고한다.

---

## 2026-05-13

### 작업 브랜치

- `generic-timeseries-infra`

### 배경

현재 운영 중인 `main` 브랜치에 영향을 주지 않기 위해 범용 분석 엔진 작업은 별도 브랜치에서 진행한다.

기존 서비스 흐름은 다음과 같다.

```text
GA4 API -> n8n -> FastAPI -> Prophet -> JSON Storage -> Dashboard
```

데이터 수집과 재호출 오케스트레이션은 n8n이 담당하고, FastAPI는 n8n이 전달한 payload를 검증한 뒤 Prophet 분석과 결과 저장을 담당한다.

### 기획 의도

세션, 채널, 이커머스, 이벤트, 매출 등 분석 대상이 늘어나더라도 ML 엔진이 도메인별 세부 의미를 알 필요는 없다.

ML 계층은 항상 단일 메트릭 시계열만 처리한다.

```text
analysis_id + dimensions + metric_name + date/value series
```

외부 입력의 구체적인 의미는 서비스/정규화 계층에서 표준 시계열 태스크로 변환한다.

```text
sessions       -> y
eventCount     -> y
purchaseRevenue -> y
activeUsers    -> y
```

Prophet은 기본적으로 단일 metric 시계열 분석에 적합하므로, 여러 metric 또는 여러 dimension 조합이 들어오면 내부적으로는 여러 개의 단일 시계열 task로 쪼개는 방향으로 간다.

### 이커머스 2단계 방어 체계 기획

리소스 효율성을 위해 이커머스 분석은 2단계로 설계한다.

1. Detection
   - 주요 퍼널 이벤트의 `eventCount` 합계를 단일 지표로 분석한다.
   - `eventName` dimension은 제외하여 payload와 연산량을 줄인다.
   - 법인/프로퍼티 단위 이커머스 엔진의 이상 여부를 먼저 감지한다.

2. Diagnosis
   - Detection에서 `is_anomaly: true`가 발생한 경우에만 n8n이 상세 리포트를 재호출한다.
   - 상세 호출에서는 `eventName` dimension을 포함한다.
   - 백엔드는 n8n이 전달한 `target_events` 목록을 기준으로 각 이벤트 시계열을 개별 분석한다.

주요 퍼널 이벤트 목록은 고정하지 않는다. 현재 예시는 `view_item`, `add_to_cart`, `begin_checkout`, `purchase`이지만, 운영 요구에 따라 n8n 또는 설정에서 바뀔 수 있다.

### 이번 작업

기존 운영 API는 변경하지 않고, 범용 단일 메트릭 분석을 위한 인프라를 새로 추가했다.

추가한 파일:

- `pytest.ini`
  - `pytest` 실행 시 루트 경로를 Python import path에 포함한다.

- `app/domain/generic_schemas.py`
  - `metric_name`, `dimensions`, `series[].value` 기반의 범용 요청 스키마를 정의한다.
  - `target_date`가 주어진 경우 마지막 series 날짜와 일치해야 한다.

- `app/domain/timeseries.py`
  - ML 계층이 받을 표준 `TimeSeriesTask`를 정의한다.
  - 분석 결과용 `TimeSeriesAnalysisResult`를 정의한다.

- `app/services/timeseries_normalizer.py`
  - 범용 요청 payload를 표준 단일 메트릭 task로 변환한다.
  - Prophet 입력 형태인 `ds`, `y` DataFrame으로 변환한다.

- `app/services/timeseries_analysis_service.py`
  - 표준 `TimeSeriesTask`를 받아 기존 `BaseDetector`로 분석한다.

- `tests/unit/test_timeseries_normalizer.py`
  - 범용 요청 정규화, `target_date` 검증, Prophet 입력 형태 변환을 테스트한다.

### 검증

실행 명령:

```bash
venv/bin/pytest -q
```

결과:

```text
5 passed
```

### 아직 하지 않은 것

- 새 generic API endpoint 연결
- n8n payload 변경
- 기존 `/api/v1/analyze`, `/api/v1/analyze/batch`, `/api/v1/update-channels` 변경
- Dashboard 변경
- 운영 `main` 브랜치 반영

### 다음 후보 작업

- `POST /api/v1/analyze/generic` 엔드포인트 추가
- generic 분석 결과 저장 스키마 설계
- n8n Detection/Diagnosis 응답 계약 정의
- 기존 sessions/channel 분석을 generic task 기반으로 점진 이관
- `.idea/workspace.xml` 커밋 제외 관리 검토

### 추가 작업: 범용 분석 API 연결

목표는 기존 대시보드 차트 계약을 유지하면서 입력 구조만 범용화하는 것이다.

유지할 차트 계약:

```text
forecast_data.ds          -> x축 날짜
forecast_data.y           -> 실제 값
forecast_data.yhat        -> Prophet 예측 중심선
forecast_data.yhat_lower  -> 신뢰구간 하단
forecast_data.yhat_upper  -> 신뢰구간 상단
```

세션 외 metric이 들어와도 대시보드/차트 계층에서는 `forecast_data.y`를 실제 값으로 해석하면 된다.

추가/변경:

- `POST /api/v1/analyze/generic` 엔드포인트 추가
- `GenericAnalysisRequest` / `GenericAnalysisResponse` 연결
- `TimeSeriesAnalysisService.run_generic_analysis()` 추가
- generic 분석 결과를 `data/generic_analysis_db.json`에 저장하는 `JSONStorage.save_generic_analysis()` 추가
- Detection 모드에서 이상 탐지 및 `target_events`가 존재하면 n8n 재호출용 `next_action` 반환

Detection 응답 예시:

```json
{
  "status": "success",
  "analysis_id": "123:ecommerce:eventCount:...",
  "is_anomaly": true,
  "result": {
    "forecast_data": {
      "ds": ["2026-05-01"],
      "y": [150],
      "yhat": [100],
      "yhat_lower": [80],
      "yhat_upper": [120]
    }
  },
  "next_action": {
    "type": "request_diagnosis",
    "domain": "ecommerce",
    "property_id": "123",
    "metric_name": "eventCount",
    "dimensions": ["eventName"],
    "target_events": ["view_item", "add_to_cart", "purchase"]
  }
}
```

검증:

```bash
venv/bin/pytest -q
```

결과:

```text
7 passed
```

### 추가 작업: 이커머스 대시보드 2단계 화면 구현

목표는 세션 대시보드와 같은 UX 구조를 `ECOMMERCE EVENTS` 카드에 적용하는 것이다.

구현 흐름:

```text
Overview
  -> ECOMMERCE EVENTS 카드
    -> Detail to Ecommerce
      -> Detection에서 이상 감지된 프로퍼티 그래프 목록
        -> Analyze Events
          -> eventName별 Diagnosis 그래프
```

추가/변경:

- `dashboard/utils/data_loader.py`
  - `generic_analysis_db.json` 로더 추가
  - domain/mode/property 기준 필터 함수 추가

- `dashboard/dashboard.py`
  - `render_ecommerce_card()`를 개발 대기 카드에서 실제 카드로 전환
  - `view_ecommerce_detail()` 추가
  - `view_ecommerce_event_detail()` 추가
  - `current_view` 라우팅에 `ecommerce_detail`, `ecommerce_event_detail` 추가

대시보드도 기존 차트 계약을 그대로 사용한다.

```text
forecast_data.ds
forecast_data.y
forecast_data.yhat
forecast_data.yhat_lower
forecast_data.yhat_upper
```

로컬 Docker 확인:

```bash
docker compose up --build -d
```

접속:

```text
API: http://localhost:8000
Dashboard: http://localhost:8501
```

샘플 데이터 상태:

```text
ecommerce detection: 2 properties, 1 anomaly
ecom-kr-shop diagnosis: 4 events, 2 anomalies
```

샘플 이벤트:

```text
view_item: normal
add_to_cart: normal
begin_checkout: anomaly
purchase: anomaly
```

검증:

```bash
venv/bin/pytest -q
PYTHONPYCACHEPREFIX=/private/tmp/ga4-pycache venv/bin/python -m py_compile dashboard/dashboard.py dashboard/utils/data_loader.py
```

결과:

```text
7 passed
py_compile passed
```

### 시도 후 원복: 상세 그래프 가시성 개선

문제:

- `render_anomaly_chart()`가 신뢰구간과 AI Target을 이미 그리고 있었지만, 신뢰구간 경계선이 `width=0`이고 음영 투명도가 낮았다.
- 범례가 꺼져 있어 사용자가 실제값만 보인다고 느끼기 쉬웠다.
- 학습 구간에서는 `y`, `yhat`, `yhat_lower`, `yhat_upper`가 거의 겹쳐 실제선이 예측선과 신뢰구간을 가렸다.

시도한 변경:

- 신뢰구간 상단/하단 경계선을 얇은 파란 선으로 표시
- 신뢰구간 음영 투명도를 높여 `Expected Range`가 보이도록 조정
- `AI Target`을 더 굵은 보라색 점선과 마커로 표시
- `Actual`은 빨간 실선과 마커 유지
- 범례를 차트 하단에 표시
- hover에서 Actual, AI Target, Upper, Lower 값을 구분해 표시

결론:

- 기존 차트 스타일이 더 적합하다는 판단으로 원복했다.
- 최종 상태는 기존 `render_anomaly_chart()` 스타일을 유지한다.

검증:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ga4-pycache venv/bin/python -m py_compile dashboard/components/charts.py dashboard/dashboard.py dashboard/utils/data_loader.py
venv/bin/pytest -q
docker compose up --build -d dashboard
```

결과:

```text
py_compile passed
7 passed
dashboard container restarted after revert
```

### 추가 확인: 이벤트 그래프 신뢰구간 미표시 원인

확인 결과, 세션과 이커머스 이벤트 대시보드는 동일한 `render_anomaly_chart()`를 사용한다.

사용 위치:

```text
Sessions detail      -> render_anomaly_chart()
Channel detail       -> render_anomaly_chart()
Ecommerce detail     -> render_anomaly_chart()
Ecommerce event detail -> render_anomaly_chart()
```

문제는 구현 차이가 아니라 샘플 데이터 차이였다.

기존 세션 샘플:

```text
yhat_lower/yhat_upper 폭이 yhat 대비 약 40%
```

기존 이커머스 샘플:

```text
상수 또는 완벽한 선형에 가까운 값
Prophet 예측구간 폭이 yhat 대비 0~0.03%
```

이 경우 신뢰구간 음영은 존재하지만 실제 화면에서는 거의 한 줄처럼 겹쳐 보여 식별하기 어렵다.

조치:

- 로컬 Docker volume의 `generic_analysis_db.json` 샘플을 변동성 있는 30일 데이터로 재적재
- Detection 2건, Diagnosis 4건 유지
- 정상/이상 케이스가 같이 보이도록 구성

보정 후 샘플 상태:

```text
ecommerce detection:
- KR Commerce Shop: anomaly, interval width ~= 24.1%
- JP Lifestyle Store: normal, interval width ~= 15.4%

ecom-kr-shop diagnosis:
- view_item: normal, interval width ~= 18.8%
- add_to_cart: normal, interval width ~= 27.6%
- begin_checkout: anomaly, interval width ~= 31.5%
- purchase: anomaly, interval width ~= 39.1%
```

### 설계 원칙 확정: 범용 입력과 단일 ML 처리

방향:

```text
어떤 dimension/metric 조합이 들어오더라도,
서비스/정규화 계층이 이를 표준 단일 시계열 분석 task로 변환한다.

ML 엔진은 dimension/metric의 의미나 개수를 알지 않고,
항상 동일한 ds/y 기반 단일 로직으로 예측값과 신뢰구간을 산출한다.
```

중요한 해석:

- ML 엔진이 모든 dimension/metric을 직접 이해하는 구조가 아니다.
- ML 엔진이 이해할 필요 없도록 서비스 계층이 입력을 정규화한다.
- Prophet 분석 단위는 계속 `단일 metric + 단일 dimension 조합`이다.
- 여러 metric 또는 여러 dimension 조합이 들어오면, 서비스 계층이 여러 개의 `TimeSeriesTask`로 분해한다.

예시:

```text
입력:
- dimensions: eventName, country, deviceCategory
- metrics: eventCount, totalRevenue

내부 task:
- eventName=purchase, country=KR, deviceCategory=mobile, metric=eventCount
- eventName=purchase, country=KR, deviceCategory=mobile, metric=totalRevenue
- eventName=add_to_cart, country=KR, deviceCategory=mobile, metric=eventCount
- ...
```

계층 책임:

```text
n8n payload
  -> API Schema
  -> Service / Normalizer
     - domain 확인
     - metric_name 확인
     - dimensions 보존
     - 여러 조합이면 task 여러 개로 분해
     - value -> y 변환
  -> ML Engine
     - ds/y만 분석
     - yhat/yhat_lower/yhat_upper 생성
  -> Storage
     - domain/metric/dimensions/forecast_data 저장
  -> Dashboard
     - forecast_data 공통 차트로 렌더링
```

이 원칙을 기준으로 세션, 채널, 이커머스 이벤트, 매출, 전환율을 같은 분석 파이프라인으로 확장한다.

### 추가 작업: 세션/이커머스 상세 카드 렌더링 공통화

문제:

- 세션 상세와 이커머스 상세가 같은 `forecast_data` 계약과 같은 차트 함수를 쓰는데도, 화면 렌더링 루프가 따로 구현되어 있었다.
- 데이터 종류가 달라진다고 대시보드 구현을 새로 만드는 방향은 유지보수에 좋지 않다.

변경:

- `dashboard/dashboard.py`에 `render_analysis_grid()` 공통 렌더러 추가
- `view_sessions_detail()`이 공통 렌더러를 사용하도록 변경
- `view_ecommerce_detail()`도 같은 공통 렌더러를 사용하도록 변경
- 차트 함수 `render_anomaly_chart()`는 기존 스타일 그대로 유지

공통 전제:

```text
forecast_data.ds
forecast_data.y
forecast_data.yhat
forecast_data.yhat_lower
forecast_data.yhat_upper
```

검증:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ga4-pycache venv/bin/python -m py_compile dashboard/dashboard.py dashboard/utils/data_loader.py dashboard/components/charts.py
venv/bin/pytest -q
docker compose up --build -d dashboard
```

결과:

```text
py_compile passed
7 passed
dashboard container restarted
```

### 추가 작업: n8n 이커머스 generic workflow 초안 생성

원본:

```text
n8n/workflows/Monitoring.json
```

수정본:

```text
n8n/workflows/Monitoring.generic-ecommerce.json
```

원칙:

- 원본 workflow는 수정하지 않는다.
- 기존 세션 Detection 및 채널 Diagnosis 흐름은 보존한다.
- 이커머스 generic 흐름을 별도 노드 묶음으로 추가한다.

현재 원본 n8n 흐름:

```text
GA4 Property 목록 조회
  -> Property 필터링
  -> sessions 조회
  -> /api/v1/analyze/batch
  -> session anomaly property 필터링
  -> sessionDefaultChannelGroup 조회
  -> /api/v1/update-channels
```

추가한 이커머스 흐름:

```text
기존 Property 목록
  -> Ecommerce - Build Detection Properties
  -> Loop Ecommerce Detection
  -> GA4 Ecommerce Detection Report
  -> Prepare Ecommerce Generic Detection Payloads
  -> POST Ecommerce Generic Detection
  -> Filter Ecommerce Detection Anomalies
  -> Loop Ecommerce Diagnosis
  -> GA4 Ecommerce Diagnosis Report
  -> Prepare Ecommerce Generic Diagnosis Payloads
  -> POST Ecommerce Generic Diagnosis
```

Detection GA4 요청:

```text
dimensions: date
metrics: eventCount
dimensionFilter: eventName in [view_item, add_to_cart, begin_checkout, purchase]
```

Diagnosis GA4 요청:

```text
dimensions: date, eventName
metrics: eventCount
dimensionFilter: eventName in [view_item, add_to_cart, begin_checkout, purchase]
```

FastAPI 요청:

```text
POST /api/v1/analyze/generic
```

주의:

- 수정본의 API URL은 현재 운영 서버 `http://34.172.65.42:8000` 기준이다.
- 로컬 n8n에서 테스트할 경우 `POST Ecommerce Generic Detection`, `POST Ecommerce Generic Diagnosis` URL을 변경해야 한다.
- n8n이 Docker에서 실행 중이면 `http://host.docker.internal:8000/api/v1/analyze/generic` 사용.
- n8n이 호스트에서 직접 실행 중이면 `http://localhost:8000/api/v1/analyze/generic` 사용.

검증:

```text
JSON parse passed
node count: 28
connection count: 26
missing node refs: none
```

### 추가 작업: 로컬 Docker n8n 구성

이유:

- n8n Cloud에서는 사용자의 로컬 `localhost` 또는 Docker 내부 `api` 서비스에 직접 접근할 수 없다.
- 로컬 FastAPI와 workflow를 함께 테스트하려면 n8n도 같은 Docker Compose 네트워크에 올리는 편이 가장 단순하다.

변경:

- `docker-compose.yml`에 `n8n` 서비스 추가
- n8n 포트: `5678`
- n8n 데이터 볼륨: `n8n_data`
- workflow 파일 mount: `./n8n/workflows:/files/workflows:ro`
- 로컬 workflow 파일 추가:

```text
n8n/workflows/Monitoring.local-docker.json
```

로컬 Docker workflow endpoint:

```text
http://api:8000/api/v1/reset
http://api:8000/api/v1/analyze/batch
http://api:8000/api/v1/update-channels
http://api:8000/api/v1/analyze/generic
```

접속:

```text
n8n:       http://localhost:5678
API:       http://localhost:8000
Dashboard: http://localhost:8501
```

검증:

```text
docker compose config passed
docker compose up -d n8n passed
n8n HTTP 200 OK
workflow files visible in /files/workflows
```

주의:

- n8n self-host community edition은 무료로 사용할 수 있지만, 운영 관리는 직접 해야 한다.
- n8n 공식 문서도 self-hosting에는 Docker/서버/보안/백업 지식이 필요하다고 안내한다.
- n8n Cloud의 Google Analytics credential은 로컬 Docker로 자동 이전되지 않는다.
- 로컬 n8n에서 Google Analytics OAuth credential을 새로 연결해야 한다.
