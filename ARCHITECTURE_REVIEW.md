# GA4 Anomaly Detector Architecture Review

작성 기준: 2026-05-13  
작성 범위: 현재 브랜치의 실제 코드, n8n workflow JSON, 테스트 결과 기준  
권장 파일명: `ARCHITECTURE_REVIEW.md`

## 1. 오늘 작업 소회

오늘 작업의 핵심은 기존 GA4 세션 이상 탐지 앱을 "테마별 운영 모니터링 시스템"으로 확장하면서, n8n workflow와 backend contract가 같은 구조를 바라보도록 맞춘 것이다. 단순히 노드를 추가한 작업이 아니라, sessions, ecommerce, unassigned traffic이라는 서로 다른 업무 의미를 같은 분석 엔진으로 흘려보내기 위해 계층 경계를 다시 확인한 작업이었다.

가장 중요한 설계 결정은 GA4의 의미를 ML 엔진으로 끌고 가지 않는 것이다. `app/ml` 아래에는 sessions, ecommerce, eventName, sessionDefaultChannelGroup, sessionSourceMedium 같은 GA4 도메인 키워드가 없어야 하며, 실제로 `tests/unit/test_ml_boundary.py`가 이 경계를 테스트한다. GA4 raw rows 해석, derived metric 계산, diagnosis task 분해, alert policy 적용은 service layer에서 처리하고, Prophet 엔진은 `ds`와 `y`만 받는다.

오늘의 주요 구현 및 정리 내용은 다음과 같다.

- n8n workflow에 Unassigned Traffic branch를 추가하고, detection/diagnosis 모두 loop 구조를 갖도록 정리했다.
- Ecommerce branch가 sessions loop의 완료 경로에 의존하던 구조를 공통 property list에서 직접 시작하도록 수정했다.
- GA4 `batchRunReports` URL에서 `property_id`가 빠져 `/properties/:batchRunReports`로 호출되던 문제를 점검하고, workflow의 GA4 URL expression을 `{{$json.property_id || $json.propertyId}}` 형태로 맞췄다.
- n8n 내부 DB와 저장소 JSON 파일이 서로 다른 workflow를 바라보는 문제를 확인했다.
- 삭제된 credential ID `D6XutmOM59kZ1fXk`를 실제 n8n DB에 존재하는 `ieceYHg2RYukMAsP` credential로 교체했다.
- n8n workflow JSON 기준 source/target 연결 무결성을 검증했다.
- backend/frontend 테스트를 실행해 현재 contract가 깨지지 않았음을 확인했다.

시행착오는 대부분 n8n 운영 모델에서 발생했다. 저장소의 `n8n/workflows/*.json` 파일을 수정해도, n8n 화면에서 실행되는 workflow는 n8n 내부 SQLite DB의 draft workflow일 수 있다. 이 때문에 파일 기준으로는 정상인데 실제 실행에서는 stale connection, stale credential, 이전 branch 구조를 사용하는 상황이 있었다. 오늘 발생한 `a.ok(from)`, `Node was not executed`, credential not found 오류는 모두 이 관점에서 해석해야 한다.

SQLite에 대해서는 명확한 운영 원칙이 필요하다. n8n SQLite는 workflow 실행 상태와 credential 참조를 담는 내부 저장소이므로, 정상 운영에서는 직접 write 대상으로 삼지 않아야 한다. 오늘은 로컬 개발 환경에서 파일 workflow와 UI workflow가 어긋난 긴급 정합성 문제를 확인하고 복구하기 위해 SQLite를 조회하고 일부 값을 맞췄지만, 장기적으로는 import/export와 UI 재연결 절차로 관리하는 편이 안전하다. SQLite 직접 write는 read-only 진단 또는 최후의 로컬 복구 수단으로만 제한해야 한다.

프론트엔드 고도화에서 얻은 결론은 대시보드가 새로운 분석 의미를 만들면 안 된다는 점이다. Next.js dashboard는 FastAPI의 Dashboard Results API가 내려주는 `alert_status`, `target_point`, `group_key`, `theme_id`, `metric_type`을 시각화해야 한다. 화면에서 다시 GA4 의미를 추론하거나 ML 결과를 재해석하면 backend contract와 어긋난다.

Unassigned Traffic 테마 추가에서 가장 중요한 교훈은 "수집은 raw, 판단은 backend" 원칙이다. n8n은 `date + sessionDefaultChannelGroup + sessions` raw rows를 가져오고, `unassigned_session_share = unassigned_sessions / total_sessions` 계산은 backend service layer가 담당한다. 이 설계 덕분에 n8n workflow는 단순해지고, derived ratio의 all-zero 처리, upper-only alert policy, source/medium diagnosis pruning 같은 비즈니스 규칙은 테스트 가능한 Python 코드로 남는다.

## 2. 애플리케이션의 기획 목적

이 앱은 단순 GA4 리포트 툴이 아니다. GA4 화면을 사람이 열어 metric을 확인하고, 전일 대비 또는 감각적으로 이상 여부를 판단하고, 다시 원인 후보 dimension을 파고드는 반복 작업을 자동화하는 운영 모니터링 시스템이다.

운영자가 해결하려는 문제는 다음과 같다.

- 여러 GA4 property를 매일 사람이 직접 확인해야 하는 부담
- 트래픽 급락, 급등, attribution 품질 저하, ecommerce funnel 이상을 늦게 발견하는 문제
- 전체 metric 이상과 원인 후보 dimension을 한 화면에서 연결해 보기 어려운 문제
- "과거에도 이상치가 있었는지"와 "오늘 운영 alert인지"가 섞이는 문제

현재 구조는 Detection -> Diagnosis 2-step으로 이 문제를 푼다.

- Detection은 property/theme 단위로 현재 이상 여부를 판단한다.
- Diagnosis는 detection 결과가 실제 alert일 때만 원인 후보 dimension을 더 잘게 분석한다.

즉, 모든 dimension 조합을 무조건 분석하는 것이 아니라, 먼저 운영 alert가 필요한 property/theme을 좁히고, 그다음 필요한 경우에만 원인 후보를 좁힌다. 이 구조는 GA4 API 호출량과 workflow 실행 시간을 줄이고, dashboard/report가 운영자가 실제로 봐야 할 항목에 집중하도록 만든다.

앱의 핵심 관점은 "정상 범위를 벗어난 움직임을 감지하고 원인 후보를 좁히는 시스템"이다. Prophet은 과거 시계열을 기준으로 기대 범위를 만들고, service layer는 target date 기준으로 현재 alert인지 판단하며, dashboard는 detection과 diagnosis를 `group_key`로 연결해서 운영자가 바로 볼 수 있는 상태로 보여준다.

## 3. 전체 아키텍처

현재 아키텍처의 기본 흐름은 다음과 같다.

```text
GA4 API
  -> n8n
  -> FastAPI
  -> Service Layer
  -> TimeSeries Analysis Service
  -> Prophet ML Engine
  -> JSON Storage
  -> Dashboard Results API
  -> Next.js Dashboard
```

각 계층의 책임은 분리되어 있다.

| 계층 | 책임 |
| --- | --- |
| GA4 API | property 목록, metric/dimension raw rows 제공 |
| n8n | GA4 query 실행, property loop, detection/diagnosis orchestration |
| FastAPI | API contract 검증, service layer 진입점 제공 |
| Service Layer | GA4 raw rows 해석, AnalysisTask 생성, alert policy 적용, 저장 |
| TimeSeries Analysis Service | canonical single-metric analysis 실행 |
| Prophet ML Engine | `ds/y` 시계열 예측과 point anomaly 판별 |
| JSON Storage | 분석 결과 파일 저장, idempotent key 기반 upsert |
| Dashboard Results API | legacy/generic 결과를 공통 dashboard item으로 변환 |
| Next.js Dashboard | 결과 contract 시각화, theme/detail/report 화면 제공 |

이 구조의 이유는 확장성보다 경계 명확성에 있다. 신규 테마를 추가할 때 ML 엔진을 수정하지 않고, n8n query와 service layer normalizer만 확장하면 된다. 반대로 dashboard는 theme별 특수 계산을 직접 만들지 않고, 저장된 결과와 dashboard contract를 화면으로 표현한다.

참고로 `docker-compose.yml`에는 기존 Streamlit dashboard 컨테이너(`ga4-dashboard`, port 8501)도 남아 있다. 현재 고도화된 운영 화면은 Next.js frontend(`ga4-frontend`, port 3000)가 담당하고, Streamlit dashboard는 초기/legacy dashboard 성격으로 보는 것이 현재 코드 구조에 가깝다.

## 4. n8n 역할

n8n은 데이터 수집과 workflow orchestration 담당이다. 현재 workflow 파일은 다음 두 개가 핵심이다.

- `n8n/workflows/Monitoring.local-docker.json`
- `n8n/workflows/Monitoring.generic-ecommerce.json`

현재 두 workflow 모두 39개 node와 36개 connection source를 가지며, JSON 기준 source/target 누락은 0건으로 확인했다.

n8n이 담당하는 일은 다음과 같다.

- GA4 Admin API에서 account summaries와 property list 조회
- property list 생성과 제외 property/subproperty 필터링
- theme branch별 property loop
- GA4 Data API `batchRunReports` 호출
- FastAPI detection endpoint 호출
- detection response의 `should_run_diagnosis` 또는 `is_anomaly` 기준으로 diagnosis branch 실행
- diagnosis GA4 query와 FastAPI diagnosis endpoint 호출

n8n이 계산하지 말아야 하는 것은 다음과 같다.

- Prophet 예측
- 이상 여부 최종 판단
- derived metric의 비즈니스 규칙
- alert/watch/normal 정책
- diagnosis top-N pruning
- dashboard group contract 생성

### Sessions Branch

Sessions branch는 기존 세션 모니터링 흐름이다.

- property loop: `Loop Over Items`
- detection GA4 request: `HTTP Request3`
- backend detection endpoint: `/api/v1/analyze/batch`
- diagnosis loop: `Loop Over Items1`
- diagnosis GA4 request: `HTTP Request4`
- backend channel endpoint: `/api/v1/update-channels`

Sessions는 legacy storage인 `results_db.json`과 `channel_anomaly_db.json`을 사용한다.

### Ecommerce Branch

Ecommerce branch는 공통 property list에서 직접 시작한다.

```text
Code in JavaScript
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

Detection은 `eventName in [view_item, add_to_cart, begin_checkout, purchase]` 조건으로 `eventCount`를 일자별 합산한다. Diagnosis는 같은 event set을 `date + eventName`으로 조회하고 eventName별 task로 나눠 `/api/v1/analyze/generic`에 보낸다.

오늘 수정의 핵심은 Ecommerce branch를 sessions loop 완료 경로에서 분리한 것이다. 이전 구조는 `Loop Over Items`의 path에 의존해 `Node was not executed`가 발생하기 쉬웠다. 현재 구조는 `Code in JavaScript`의 공통 property list에서 sessions, ecommerce, unassigned branch가 병렬로 갈라진다.

### Unassigned Traffic Branch

Unassigned Traffic branch도 공통 property list에서 직접 시작한다.

```text
[Unassigned] Build Properties
  -> Loop Unassigned Detection
  -> [Unassigned] GA4 Detection Report
  -> [Unassigned] Prepare Detection Payload
  -> [Unassigned] POST Detection
  -> [Unassigned] Filter should_run_diagnosis
  -> Loop Unassigned Diagnosis
  -> [Unassigned] GA4 Diagnosis Report
  -> [Unassigned] Prepare Diagnosis Payload
  -> [Unassigned] POST Diagnosis
```

Detection loop는 `batchSize=5`, diagnosis loop는 `batchSize=1`이다. 이 구조는 sessions/ecommerce처럼 theme branch에도 명시적 loop를 둬 property별 GA4 호출과 backend 호출의 입력 item이 유지되도록 만든다.

### Credential / Import / Export 주의점

n8n workflow JSON에는 credential ID가 저장될 수 있다. 오늘 오류는 workflow가 삭제된 credential ID `D6XutmOM59kZ1fXk`를 참조하면서 발생했다. 현재 로컬 n8n DB에는 `googleAnalyticsOAuth2` credential로 `ieceYHg2RYukMAsP`가 존재했고, GA4 관련 node들이 이 ID를 참조하도록 맞췄다.

운영상 주의점은 다음과 같다.

- repository JSON과 n8n UI에서 실행되는 draft workflow가 다를 수 있다.
- `docker-compose.yml`은 `./n8n/workflows`를 `/files/workflows`에 read-only mount하지만, n8n UI 실행본은 내부 DB에 저장된다.
- workflow JSON import 후에는 credential을 n8n UI에서 재연결해야 할 수 있다.
- n8n SQLite 직접 write는 운영 절차가 아니라 로컬 진단/복구 수단으로만 제한해야 한다.

## 5. Backend / FastAPI 역할

FastAPI는 단순 proxy가 아니라 service layer 진입점이다. API router는 payload contract를 검증하고, 의존성 주입으로 detector/storage/service를 조립한 뒤, 실제 비즈니스 로직은 service layer에 위임한다.

현재 주요 endpoint는 `app/api/routers/analyze.py`, `management.py`, `dashboard.py`에 있다.

| Endpoint | 역할 |
| --- | --- |
| `POST /api/v1/analyze` | legacy sessions 단일 분석 |
| `POST /api/v1/analyze/batch` | sessions batch detection |
| `POST /api/v1/analyze/generic` | ecommerce 등 generic single-metric detection/diagnosis |
| `POST /api/v1/analyze/themes/unassigned-traffic/detection` | Unassigned raw rows -> derived ratio detection |
| `POST /api/v1/analyze/themes/unassigned-traffic/diagnosis` | Unassigned source/medium diagnosis |
| `POST /api/v1/update-channels` | sessions channel diagnosis |
| `GET /api/v1/dashboard/results` | dashboard 공통 result item 조회 |
| `POST /api/v1/reset` | analysis JSON 파일 초기화 |
| `GET /api/v1/health` | health check |

FastAPI가 service layer 진입점이어야 하는 이유는 API boundary에서 request shape를 안정화하고, 그 뒤의 domain/service/ML/storage를 독립적으로 테스트하기 위해서다. 실제 테스트도 router 등록, response contract, dashboard 변환, ML boundary를 각각 분리해 검증한다.

## 6. Domain 모델과 Contract

현재 domain contract의 중심은 `app/domain/timeseries.py`, `generic_schemas.py`, `dashboard_schemas.py`다.

### AnalysisTask

`AnalysisTask`는 ML layer가 소비하는 canonical unit이다. 하나의 property, 하나의 metric, 하나의 mode, 하나의 dimension 조합에 대한 단일 시계열 작업을 뜻한다.

주요 필드:

- `analysis_id`: storage key이자 결과 식별자. property, domain, mode, metric, dimensions, date range, filters, theme metadata의 signature로 만든다.
- `domain`: sessions, ecommerce, traffic_quality 같은 분석 domain.
- `mode`: detection 또는 diagnosis.
- `property_id`, `property_name`: GA4 property 식별과 표시명.
- `theme_id`: `unassigned_traffic`처럼 domain보다 구체적인 테마 식별자.
- `metric_name`: sessions, eventCount, unassigned_session_share 등 분석 metric.
- `metric_type`: raw_count, derived_ratio 같은 metric 성격.
- `alert_direction_policy`: two_sided 또는 upper_only.
- `dimensions`: diagnosis task의 대표 dimension 정보.
- `series`: `TimeSeriesPoint` 목록. ML에는 이 값만 `ds/y`로 변환되어 들어간다.
- `target_date`: 현재 이상 판단 기준일.
- `metadata`: dashboard/report/debug에 필요한 원본 의미와 필터 정보.

### TimeSeriesPoint

`TimeSeriesPoint`는 service layer에서 ML layer로 넘기는 최소 시계열 단위다.

- `date`: ISO date string
- `value`: numeric metric value

이 모델은 GA4 dimension 이름을 포함하지 않는다.

### ForecastPoint

`ForecastPoint`는 dashboard에서 일자별 예측 결과를 row 단위로 볼 때의 구조다.

- `ds`
- `y`
- `yhat`
- `yhat_lower`
- `yhat_upper`
- `is_anomaly`

### AnalysisResult

`AnalysisResult`는 service layer가 저장하는 분석 결과다.

- `analysis_id`, `domain`, `mode`, `property_id`, `theme_id`, `metric_name`, `metric_type`, `dimensions`, `metadata`는 task context 보존용이다.
- `is_anomaly`는 ML detector가 마지막 point 기준으로 계산한 legacy 성격의 boolean이다.
- `actual_value`, `lower_bound`, `upper_bound`, `target_date`는 target point 요약이다.
- `forecast_data`는 전체 시계열 예측 결과이며, `is_anomaly` 배열이 없으면 model validator가 `y < yhat_lower or y > yhat_upper` 기준으로 채운다.

### DashboardResultItem

`DashboardResultItem`은 Next.js dashboard가 소비하는 공통 item이다. legacy sessions result, channel result, generic result가 모두 이 형태로 변환된다.

핵심 필드:

- `id`: dashboard item 식별자.
- `source`: `results_db`, `channel_anomaly_db`, `generic_analysis_db`.
- `group_key`: detection과 diagnosis를 연결하는 key.
- `analysis_id`: storage 분석 ID.
- `domain`, `mode`, `theme_id`: theme/detail 화면 분류 기준.
- `metric_name`, `metric_type`: 표시와 formatting 기준.
- `dimension`, `dimension_value`, `dimensions`: diagnosis row 표시 기준.
- `target_date`, `target_point`, `latest_point`: 기준일과 표시 point.
- `has_anomaly`: 전체 forecast_data 중 point anomaly가 하나라도 있는지.
- `is_current_anomaly`: target_date의 anomaly가 business alert인지.
- `alert_status`: `alert`, `watch`, `normal`.
- `alert_direction_policy`: upper_only 같은 정책을 dashboard까지 전달.
- `historical_anomaly_count`, `recent_anomaly_count`: historical/watch 판단과 표시.
- `metadata`: filter, source dimension, raw dimension values 등 테마별 부가 정보.

이 contract가 중요한 이유는 dashboard가 storage를 직접 해석하지 않고, backend가 통일한 operational view만 소비하게 만들기 위해서다.

## 7. Service Layer 역할

Service layer는 GA4 의미와 ML engine 사이의 방화벽이다. 현재 주요 class는 다음과 같다.

- `AnomalyService`
- `TimeSeriesAnalysisService`
- `TimeSeriesNormalizer`
- `DashboardResultsService`
- `alert_policy`

Service layer가 담당하는 책임은 다음과 같다.

- GA4 raw rows 해석
- derived metric 계산
- `AnalysisTask` 생성
- dimension/metric 의미 해석
- detection/diagnosis task 분해
- top-N / min-volume pruning
- alert policy 적용
- storage key 생성
- dashboard result 변환

`TimeSeriesNormalizer`는 generic request, Unassigned detection request, Unassigned diagnosis request를 모두 `AnalysisTask`로 정규화한다. `TimeSeriesAnalysisService`는 정규화된 task를 ML detector에 넘기고, forecast 결과를 `AnalysisResult`로 만든다. `DashboardResultsService`는 JSON storage에 저장된 legacy/generic 결과를 dashboard contract로 변환한다.

ML engine이 절대 알면 안 되는 것은 다음과 같다.

- sessions/ecommerce/unassigned 같은 theme 이름
- `eventName`
- `sessionDefaultChannelGroup`
- `sessionSourceMedium`
- GA4 metric/dimension의 업무 의미

이 경계는 `tests/unit/test_ml_boundary.py`로 검증된다.

## 8. ML Engine 역할과 경계

ML engine은 `app/ml` 아래에 있으며 현재 구현체는 `ProphetDetector`다.

Prophet engine의 입력은 pandas DataFrame의 `ds`, `y`뿐이다. 내부 구현은 다음 원칙을 따른다.

- 마지막 target row를 제외하고 학습한다.
- 전체 `ds` 기간에 대해 예측한다.
- `yhat`, `yhat_lower`, `yhat_upper`를 반환한다.
- anomaly check는 `actual < lower or actual > upper`다.

저장되는 `forecast_data` 구조는 다음과 같다.

```text
ds
y
yhat
yhat_lower
yhat_upper
is_anomaly
```

모든 테마는 service layer에서 단일 시계열 task로 정규화된다. Sessions도 sessions time series, ecommerce도 eventCount time series, Unassigned도 derived ratio 또는 source/medium별 sessions time series가 된다.

ML 엔진 내부에 GA4 의미 분기가 없어야 하는 이유는 명확하다. GA4 metric이나 dimension의 의미가 ML 코드에 들어가면 신규 테마가 추가될 때마다 detector가 업무 규칙을 알아야 한다. 그러면 detector 테스트는 점점 도메인 테스트가 되고, 재사용 가능한 시계열 엔진이 아니라 GA4 전용 함수가 된다. 현재 구조는 이 결합을 막는다.

## 9. 이상 판단 기준

현재 이상 판단은 point anomaly와 operational alert를 구분한다.

Prophet은 모든 날짜에 대해 point anomaly를 계산한다.

```text
point anomaly = y < yhat_lower 또는 y > yhat_upper
```

하지만 property/theme의 현재 이상 여부는 전체 기간이 아니라 `target_date` 기준이다.

- 요청에 `target_date`가 있으면 해당 날짜를 사용한다.
- 없으면 마지막 `ds`를 사용한다.
- `has_anomaly`는 전체 `forecast_data.is_anomaly` 중 하나라도 true인지다.
- `is_current_anomaly`는 target_date 기준 anomaly가 business alert인지다.

`alert_status`는 `app/services/alert_policy.py`에서 계산된다.

- `alert`: target point가 현재 business alert일 때
- `watch`: target point는 alert가 아니지만 최근 7일 window 내 breach가 2회 이상일 때
- `normal`: 위 조건에 해당하지 않을 때

`upper_only` 정책에서는 target point의 `y > yhat_upper`만 current alert다. lower breach는 point anomaly일 수 있지만 business alert가 아닐 수 있다. Unassigned Traffic이 여기에 해당한다.

Historical anomaly와 current alert는 다르다. 과거 어느 날짜에 이상치가 있었기 때문에 `has_anomaly=true`일 수 있지만, target_date가 정상이라면 현재 운영 alert는 아니다. 따라서 report와 dashboard는 `has_anomaly`만 보면 안 되고, `alert_status`와 `is_current_anomaly`를 기준으로 판단해야 한다. 실제 report builder도 detection item 중 target date가 report date와 같고 `is_current_anomaly`인 항목을 사용한다.

## 10. 테마별 로직

### A. Sessions

목적은 GA4 property별 sessions 급등/급락을 감지하는 것이다. 기존 앱의 핵심 기능이며 legacy storage와 channel diagnosis 구조가 남아 있다.

Step 1 Detection:

- metric: `sessions`
- dimension: date
- backend endpoint: `/api/v1/analyze/batch`
- storage: `results_db.json`

Step 2 Diagnosis:

- metric: `sessions`
- dimension: channel 계열 grouping
- backend endpoint: `/api/v1/update-channels`
- storage: `channel_anomaly_db.json`

Dashboard에서는 Sessions theme detail에서 detection 결과를 보여주고, overview의 Sessions Trending에는 current alert 중 expected range보다 높거나 낮게 관측된 Top 5를 표시한다.

### B. Ecommerce Events

목적은 ecommerce funnel event 흐름의 이상을 property 단위로 감지하고, eventName별 원인 후보를 좁히는 것이다.

Step 1 Detection:

- GA4 metric: `eventCount`
- GA4 dimension: date
- event filter: `view_item`, `add_to_cart`, `begin_checkout`, `purchase`
- backend endpoint: `/api/v1/analyze/generic`
- domain: `ecommerce`
- mode: `detection`

이 단계는 funnel event 전체 합산 흐름을 본다. 특정 event만 보는 것이 아니라 주요 ecommerce funnel event set의 총량이 예상 범위 밖인지 확인한다.

Step 2 Diagnosis:

- GA4 metric: `eventCount`
- GA4 dimensions: date, eventName
- backend endpoint: `/api/v1/analyze/generic`
- domain: `ecommerce`
- mode: `diagnosis`
- dimensions: eventName별 task

주의할 해석은 detection의 이상이 곧 특정 eventName의 원인이라고 단정할 수 없다는 점이다. Diagnosis는 같은 날짜에 eventName별 이상 신호가 함께 확인되는지 보여주는 원인 후보 narrowing이다.

### C. Unassigned Traffic

Unassigned Traffic은 GA4 traffic attribution quality 테마다. 목적은 GA4가 traffic source/channel을 제대로 분류하지 못하고 Unassigned로 떨어지는 비율이 비정상적으로 높아졌는지 감지하는 것이다.

Detection raw input:

```text
date
sessionDefaultChannelGroup
sessions
```

Derived metric:

```text
unassigned_session_share = unassigned_sessions / total_sessions
```

이 계산은 n8n이 아니라 backend의 `TimeSeriesNormalizer.from_unassigned_traffic_detection()`이 수행한다. metadata에는 total sessions, unassigned sessions, numerator/denominator filter, source dimension/metric이 보존된다.

Diagnosis:

- GA4 filter: `sessionDefaultChannelGroup == Unassigned`
- GA4 dimension: `sessionSourceMedium`
- metric: `sessions`
- backend endpoint: `/api/v1/analyze/themes/unassigned-traffic/diagnosis`

`(not set)`, empty 값을 제거하지 않는 이유는 이 값들이 attribution 품질 저하의 중요한 원인 후보일 수 있기 때문이다. service layer는 `None`을 `(not set)`, 빈 문자열을 `(empty)`로 정규화하고 raw value도 metadata에 보존한다.

Unassigned Traffic은 `alert_direction_policy = upper_only`다. Unassigned 비율이 예상보다 낮은 것은 point anomaly일 수 있지만 일반적으로 운영 alert가 아니다. 반대로 예상보다 높은 경우는 traffic attribution 품질 저하 가능성이 있어 alert다.

All-zero derived ratio 처리도 별도 정책이 있다. Unassigned 비율이 전 기간 0이면 Prophet을 호출하지 않고 normal baseline result를 만든다. 이 예외는 `theme_id == "unassigned_traffic"`이고 `metric_type == "derived_ratio"`일 때만 적용되며, sessions/ecommerce all-zero series에는 적용되지 않는다.

Detection과 diagnosis는 `group_key`로 연결된다.

```text
{property_id}:traffic_quality:unassigned_traffic:{target_date}
```

## 11. Storage / JSON Storage

현재 저장소는 JSON 파일 기반이다. 구현은 `app/infrastructure/json_storage.py`에 있다.

역할:

- legacy sessions result 저장: `results_db.json`
- sessions channel diagnosis 저장: `channel_anomaly_db.json`
- generic/theme analysis 저장: `generic_analysis_db.json`
- reset 시 세 파일 초기화
- dashboard service가 읽을 수 있는 persisted result 제공

idempotency는 key 기반 upsert로 보장한다. generic analysis는 `analysis_id`를 key로 저장하고, 같은 property/domain/mode/metric/dimension/date range/filter/theme signature는 같은 key를 갖는다.

`analysis_id` signature에 다음 요소가 포함되는 이유는 서로 다른 분석 의미가 덮어써지면 안 되기 때문이다.

- `theme_id`
- `metric_type`
- `filters`
- `alert_direction_policy`
- `domain`
- `mode`
- `metric_name`
- `dimensions`
- `date_start`, `date_end`
- `aggregation_method`
- `property_id`, `property_name`, `corporation`

JSON write는 temp file 생성 후 `os.replace()`로 atomic write에 가깝게 처리한다. thread lock도 있다. 다만 JSON storage는 운영 DB로서는 한계가 있다.

한계:

- 동시 write가 많아지면 파일 단위 lock과 replace만으로 충분하지 않을 수 있다.
- query/filter/sort가 모두 애플리케이션 메모리에서 발생한다.
- execution history, backfill, audit trail 관리가 어렵다.
- 파일 크기가 커지면 dashboard read 비용이 커진다.

추후 전환 후보는 SQLite, PostgreSQL, Cloud SQL이다. 단기 로컬 개발에서는 JSON이 단순하고 충분하지만, 실제 운영 property 수와 실행 빈도가 늘면 relational storage로 전환할 시점이 온다.

## 12. Dashboard Results API

Dashboard가 storage를 직접 읽지 않는 이유는 storage format이 하나가 아니기 때문이다. 현재도 sessions legacy, channel legacy, generic analysis result가 서로 다른 파일과 shape를 가진다.

Next.js는 FastAPI의 `/api/v1/dashboard/results`를 통해 결과만 읽는다. 이 endpoint는 `DashboardResultsService`가 다음 저장소를 읽고 공통 item으로 변환한 결과를 반환한다.

- `results_db.json`
- `channel_anomaly_db.json`
- `generic_analysis_db.json`

Dashboard Results API의 핵심 역할:

- legacy/generic result를 `DashboardResultItem`으로 변환
- forecast_data contract 검증
- 누락된 point anomaly 보정
- alert policy 재계산
- target point, latest point, alert status 제공
- detection/diagnosis 연결용 group_key 생성

`target_point`는 현재 판단 기준이 되는 forecast point다. `latest_point`는 현재 구현에서 target point와 같은 의미로 쓰이는 경우가 많지만, dashboard contract에서 최신 point 참조용으로 분리되어 있다. `alert_status`는 화면과 report가 운영 판단에 쓰는 기본 상태값이다.

## 13. Frontend / Next.js Dashboard

Next.js dashboard는 `frontend/app/dashboard` 아래에 구현되어 있다. 주요 route는 다음과 같다.

- `/dashboard`: Monitoring Workspace overview
- `/dashboard/themes/sessions`: Sessions theme detail
- `/dashboard/themes/ecommerce`: Ecommerce theme detail
- `/dashboard/themes/unassigned-traffic`: Unassigned Traffic theme detail
- `/dashboard/themes/[theme]`: dynamic theme route
- `/dashboard/diagnosis/[groupKey]`: diagnosis detail
- `/dashboard/reports`: reports

View model은 `frontend/lib/view-models.ts`에 집중되어 있다. `THEME_REGISTRY`에는 현재 sessions, ecommerce, unassigned-traffic이 등록되어 있다.

주요 화면 구성:

- Summary cards
- Sessions Trending
- Theme summary cards
- Property Health Matrix
- Theme detail Chart/Table tabs
- Diagnosis detail Chart/Table tabs
- Reports 종합/세부 리포트

Chart는 `ForecastChart`가 Recharts 기반으로 렌더링한다. actual line, forecast center line, confidence interval, anomaly reference dot을 표시한다. 메인 overview에서는 chart를 과도하게 렌더링하지 않고, theme detail과 diagnosis detail에서 chart grid를 보여준다. 이는 많은 property가 있을 때 초기 dashboard 비용을 줄이기 위한 정책이다.

Derived ratio인 Unassigned 비율은 percentage formatting을 사용한다. `metric_type === "derived_ratio"` 또는 `metric_name === "unassigned_session_share"`이면 `formatRatio` 기반으로 표시한다.

Dashboard가 ML/GA4 의미를 새로 만들지 않아야 하는 이유는 backend contract와 화면 판단이 달라지는 것을 막기 위해서다. Frontend는 `alert_status`, `is_current_anomaly`, `target_point`, `group_key`, `theme_id`, `metric_type`을 받아 표시와 grouping을 담당한다.

기존 `dashboard/` 디렉터리의 Streamlit 구현도 repository에 남아 있다. `dashboard/dashboard.py`, `dashboard/components/charts.py`, `dashboard/utils/data_loader.py`는 JSON 결과를 직접 읽는 초기 대시보드 구조다. 현재 문서에서 설명하는 theme/detail/report 중심 운영 화면은 Next.js dashboard 기준이다.

## 14. Reports 기획

Reports는 raw anomaly dump가 아니라 운영 리포트다. 현재 구현은 `frontend/lib/view-models.ts`의 `buildReportsPage()`가 담당한다.

리포트의 기준은 detection alert다.

- detection item만 report 대상이다.
- report date는 저장된 target/latest point 중 가장 최신 날짜다.
- 해당 report date에 `is_current_anomaly`인 detection만 포함한다.
- diagnosis는 원인 후보로 연결된다.

종합 리포트는 property 기준으로 여러 theme alert를 묶는다. 특정 property에 sessions, ecommerce, unassigned traffic 이상이 동시에 발생하면 한 화면에서 겹침을 볼 수 있게 한다. 세부 리포트는 theme별 detection alert를 더 자세히 설명한다.

문장 톤은 GA4 운영 리포트에 가깝다. 예를 들어 "같은 날짜에 이상 신호가 함께 확인되었습니다"처럼 표현한다. 원인을 단정하지 않는 이유는 diagnosis 결과도 통계적 동시 이상 신호이지 인과 증명이 아니기 때문이다. 이 구조는 운영자가 원인 후보를 빠르게 좁히되, 자동 리포트가 과도하게 확정적인 결론을 내리지 않게 한다.

## 15. Tests / 검증 구조

현재 테스트 결과:

- Backend: `venv/bin/pytest tests/unit` -> 73 passed, 14 warnings
- Frontend: `npm run test` -> 3 files, 61 tests passed
- Frontend type check: `npm run lint` -> passed
- n8n workflow JSON 수동 검증: `Monitoring.local-docker.json`, `Monitoring.generic-ecommerce.json` 모두 source/target 누락 0건

테스트 범위:

- `test_prophet_detector.py`: Prophet detector 기본 동작
- `test_timeseries_analysis_service.py`: forecast contract, next_action, validation
- `test_timeseries_normalizer.py`: normalizer 동작
- `test_common_analysis_flow.py`: 공통 analysis flow
- `test_storage_idempotency.py`: storage key/idempotency/atomic behavior
- `test_dashboard_results_api.py`: dashboard result 변환
- `test_forecast_contract.py`: forecast_data contract
- `test_unassigned_traffic_detection.py`: Unassigned detection derived ratio, alert policy, all-zero 처리
- `test_unassigned_traffic_diagnosis.py`: Unassigned diagnosis task split, top-N/min-volume, group_key
- `test_ml_boundary.py`: `app/ml`에 GA4 의미 키워드가 없는지 검사
- frontend Vitest: view model, dashboard page, forecast chart contract

`app/ml`에 GA4 의미 키워드가 없는지 검사하는 이유는 ML engine이 domain-specific rule을 모르게 하기 위해서다. 이 테스트는 단순 문자열 검사지만, 경계가 무너지는 것을 빠르게 잡아준다.

Sample E2E와 실제 GA4 OAuth 검증은 다르다. 현재 unit/integration 성격의 테스트는 service contract와 dashboard 변환을 검증한다. 실제 n8n OAuth credential로 GA4 API를 호출해 end-to-end 실행하는 검증은 아직 별도 운영 확인이 필요하다.

## 16. 현재 남은 위험 요소

현재 남은 위험은 구현 미완성보다 운영 정합성에 가깝다.

- 실제 GA4 OAuth 기반 n8n 전체 실행 검증이 아직 완전히 끝나지 않았다.
- n8n workflow JSON과 n8n UI 내부 DB draft workflow가 어긋날 수 있다.
- workflow import/export 후 credential 연결은 수동 확인이 필요하다.
- n8n SQLite 직접 write는 운영 방식으로 쓰면 안 된다.
- JSON storage는 property 수와 실행 빈도가 늘면 한계가 있다.
- `group_key`는 현재 property/domain/theme/target_date 중심이며, date_range나 filter 차이까지 더 엄밀히 반영할 필요가 생길 수 있다.
- Geo Distribution 같은 신규 테마는 derived metric 설계를 먼저 해야 한다.
- all-zero / sparse series 정책은 Unassigned derived ratio에는 명확하지만, 신규 테마별로 별도 정책이 필요할 수 있다.
- GA4 API quota와 n8n workflow 실행 시간이 branch 추가에 따라 증가할 수 있다.
- n8n에서 "Node was not executed"는 조건상 정상인 경우와 구조 오류인 경우가 섞여 보일 수 있어 운영자 해석 가이드가 필요하다.

## 17. 다음 단계 제안

1. 실제 GA4 credential로 n8n Unassigned workflow를 끝까지 실행한다.
2. n8n workflow import/export 절차를 정리하고, UI DB와 repository JSON이 같은지 확인하는 운영 체크리스트를 만든다.
3. Ecommerce branch의 실제 GA4 응답과 `/api/v1/analyze/generic` 저장 결과를 확인한다.
4. Geo Distribution 테마를 기획하되, 먼저 metric/dimension과 alert direction policy를 정의한다.
5. Source/Medium 또는 Landing Page 테마는 diagnosis 후보가 너무 많아질 수 있으므로 top-N, min-volume, grouping 기준을 먼저 설계한다.
6. JSON storage가 충분하지 않은 시점에 SQLite/PostgreSQL/Cloud SQL 전환을 검토한다.
7. Reports는 alert summary, diagnosis candidate, property overlap 중심으로 더 고도화한다.
8. LLM briefing은 deterministic report가 안정화된 뒤 붙이는 것이 좋다. 먼저 현재 contract 기반 문장을 만들고, LLM은 그 결과를 요약하거나 운영자가 읽기 쉬운 문장으로 바꾸는 역할에 제한하는 편이 안전하다.

## 18. 현재 구현 상태 요약

현재 앱은 GA4 데이터를 n8n으로 수집하고, FastAPI service layer에서 단일 시계열 task로 정규화한 뒤, Prophet으로 point anomaly를 계산하고, JSON storage에 저장된 결과를 Next.js dashboard가 운영 화면으로 보여주는 구조다.

구현된 것:

- Sessions detection/diagnosis legacy flow
- Ecommerce generic detection/diagnosis flow
- Unassigned Traffic detection/diagnosis flow
- target_date 기반 current alert 판단
- `alert`, `watch`, `normal` 상태
- upper-only alert policy
- derived ratio all-zero normal baseline 처리
- dashboard 공통 result API
- Next.js overview/theme/diagnosis/report 화면
- backend/frontend 테스트

아직 명확히 남은 것:

- 실제 GA4 OAuth workflow 전체 smoke test
- n8n 운영 절차 문서화
- 저장소 DB 전환 판단
- 신규 테마 설계
- alert/report 문장 고도화
- quota와 실행 시간 관리

현재 설계의 핵심은 "n8n은 수집과 orchestration, backend service는 의미 해석과 판단, ML은 순수 시계열 예측, dashboard는 contract 시각화"라는 역할 분리다. 이 경계를 유지하면 신규 테마를 추가하더라도 ML engine과 dashboard가 불필요하게 흔들리지 않는다.
