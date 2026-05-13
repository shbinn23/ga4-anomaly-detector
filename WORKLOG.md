# 작업 일지 요약

> 현재 브랜치의 핵심 설계, 구현 상태, 검증 결과만 남긴 요약본이다.
> 운영 맥락은 `HANDOVER.md`, 작업 원칙은 `AGENTS.md`를 참고한다.

## 현재 상태

- 브랜치: `generic-timeseries-infra`
- 목적: 운영 중인 `main`에 영향 없이 범용 시계열 분석 구조와 이커머스 2단계 분석을 개발한다.
- 로컬 서비스:

```text
API:       http://localhost:8000
Dashboard: http://localhost:8501
n8n:       http://localhost:5678
```

## 제품 컨셉

GA4 데이터를 n8n이 수집하고, FastAPI가 Prophet 기반 분석을 실행한 뒤, Dashboard가 이상 탐지 결과를 시각화한다.

```text
GA4 API -> n8n -> FastAPI -> Prophet -> JSON Storage -> Dashboard
```

역할:

- n8n: GA4 조회, reset, detection/diagnosis 오케스트레이션
- FastAPI: payload 검증, 분석 실행, 결과 저장
- Prophet: `ds/y` 단일 시계열 예측
- Dashboard: 실제값, 예측선, 신뢰구간, 이상 여부 표시

## 핵심 설계 원칙

ML/Prophet 엔진은 GA4 의미를 모른다.

```text
GA4 의미 해석: service / normalizer 계층
ML 입력: ds/y 단일 시계열
```

sessions, eventCount, revenue 등 metric이 달라도 내부 분석 흐름은 같다.

```text
AnalysisTask
  -> TimeSeriesAnalysisService.run_single_metric_analysis(task)
  -> AnalysisResult
```

현재 다음 네 흐름이 모두 같은 공통 분석 진입점을 사용한다.

```text
sessions detection
sessions diagnosis
ecommerce detection
ecommerce diagnosis
```

## 공통 데이터 계약

공통 모델:

- `AnalysisTask`
- `TimeSeriesPoint`
- `ForecastPoint`
- `AnalysisResult`

공통 forecast 계약:

```text
forecast_data.ds
forecast_data.y
forecast_data.yhat
forecast_data.yhat_lower
forecast_data.yhat_upper
forecast_data.is_anomaly
```

legacy JSON에 `forecast_data.is_anomaly`가 없으면 `False`로 채우지 않고 재계산한다.

```text
is_anomaly = y < yhat_lower or y > yhat_upper
```

보정 위치:

- API/Pydantic 모델 경계
- `dashboard/utils/data_loader.py`

`dashboard.py`는 화면 구성만 담당한다.

## Sessions 흐름

기존 세션 UX와 API 응답 구조는 유지했다.

```text
Overview
  -> Sessions
    -> property anomaly 목록
      -> channel diagnosis
```

저장소:

```text
data/results_db.json
data/channel_anomaly_db.json
```

## Ecommerce Events 흐름

세션과 같은 구조로 `ECOMMERCE EVENTS` 영역에 2단계 분석을 추가했다.

Detection:

- 주요 퍼널 이벤트 `eventCount` 합계를 단일 지표로 분석
- `eventName` dimension 제외
- 법인/프로퍼티 단위 이커머스 엔진 이상 여부 감지

Diagnosis:

- Detection에서 이상 발생 시에만 실행
- `eventName` dimension 포함
- 이벤트별 시계열을 각각 공통 분석 엔진에 전달

현재 예시 이벤트:

```text
view_item
add_to_cart
begin_checkout
purchase
```

저장소:

```text
data/generic_analysis_db.json
```

## n8n / Docker

Docker Compose에 n8n을 포함했다.

워크플로우 파일:

```text
n8n/workflows/Monitoring.json
n8n/workflows/Monitoring.generic-ecommerce.json
n8n/workflows/Monitoring.local-docker.json
```

로컬 Docker workflow endpoint:

```text
http://api:8000/api/v1/reset
http://api:8000/api/v1/analyze/batch
http://api:8000/api/v1/update-channels
http://api:8000/api/v1/analyze/generic
```

정리한 내용:

- 중복 import된 local workflow 제거
- local workflow endpoint를 `http://api:8000` 기준으로 정리
- workflow JSON parse 및 node reference 검증
- 불필요한 테스트 코드 조각 제거
- ecommerce detection input source를 `$input.all()` 기반으로 정리

## Reset / Storage

`POST /api/v1/reset`은 세 저장소를 모두 초기화한다.

```text
results_db.json
channel_anomaly_db.json
generic_analysis_db.json
```

generic 분석 key:

```text
{property_id}:{domain}:{mode}:{metric_name}:{dimensions_hash}
```

보장 사항:

- 동일 task는 동일 `analysis_id`를 만든다.
- 동일 key 저장은 append가 아니라 overwrite/upsert 된다.
- detection과 diagnosis는 `mode`가 key에 포함되어 충돌하지 않는다.
- JSON 저장 시 `date/datetime` 직렬화가 깨지지 않는다.

## 검증 상태

최근 검증:

```text
pytest -q: 19 passed
py_compile: passed
API health: 정상
Dashboard HTTP: 200
n8n HTTP: 200
```

확인한 검색:

```text
rg -n "\.dict\(" app dashboard tests
=> 0건

rg -n "is_anomaly.*yhat_lower|yhat_upper.*is_anomaly" dashboard/dashboard.py
=> 0건

rg "sessions|ecommerce|eventName|channel" app/ml -n
=> 0건
```

## 주요 커밋

```text
ee815bb feat: add generic ecommerce monitoring infra
01f3a06 fix: align reset and n8n workflow data flow
0076e2e refactor: unify single metric analysis flow
767de09 test: harden forecast data contract
a07322f test: verify storage idempotency and pydantic serialization
```

## 남은 주의사항

- n8n 실제 실행은 Google Analytics credential 연결 상태에 의존한다.
- 기존 저장 JSON 중 일부 generic key는 `mode`가 없는 예전 형식일 수 있다.
- dashboard 컨테이너는 `app/`을 복사하지 않아 forecast 보정 로직이 API 모델과 dashboard loader 양쪽에 존재한다.
- `.idea/workspace.xml`은 IDE 자동 변경으로 계속 dirty 상태가 될 수 있다.
- `TECH_STACK.md`, `design.md`는 현재 작업과 무관해 커밋 대상에서 제외 중이다.

## 다음 작업 후보

1. n8n local workflow end-to-end 실행 검증
2. legacy generic key 정리 필요 여부 판단
3. 새 분석 테마 확정
   - Campaign / Source-Medium
   - Landing Page / Content Health
