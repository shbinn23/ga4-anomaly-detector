# GA4 Anomaly Detector Runbook

작성 기준: 2026-05-13  
목적: 다른 PC에서 clone 후 Docker Compose로 로컬 실행하고, n8n workflow와 GA4 OAuth credential을 연결하는 절차를 정리한다.

## 1. 전체 서비스 아키텍처

```text
GA4 API
  -> n8n workflow
  -> FastAPI API
  -> Service Layer
  -> Prophet ML Engine
  -> JSON Storage volume
  -> Dashboard Results API
  -> Next.js Dashboard

Legacy Streamlit Dashboard
  -> JSON Storage volume
```

현재 Docker Compose는 4개 서비스를 실행한다.

| Service | Container | 역할 | Port | URL |
| --- | --- | --- | --- | --- |
| `api` | `ga4-api` | FastAPI, Prophet 분석, JSON 저장 | `8000` | `http://localhost:8000` |
| `frontend` | `ga4-frontend` | Next.js 운영 대시보드 | `3000` | `http://localhost:3000` |
| `dashboard` | `ga4-dashboard` | Streamlit legacy dashboard | `8501` | `http://localhost:8501` |
| `n8n` | `ga4-n8n` | GA4 수집/workflow orchestration | `5678` | `http://localhost:5678` |

공유 volume:

| Volume | 용도 |
| --- | --- |
| `ga4_data` | API가 쓰는 JSON analysis 결과를 dashboard 계열이 읽는다. |
| `n8n_data` | n8n 내부 DB, credential, workflow draft 저장소다. |

중요한 경계:

- n8n은 GA4 query와 workflow orchestration만 담당한다.
- FastAPI service layer가 GA4 raw rows 해석, derived metric 계산, alert 판단을 담당한다.
- ML engine은 `ds/y` 시계열만 받는다.
- Next.js는 Dashboard Results API 결과를 시각화한다.
- Streamlit은 repository에 남아 있는 legacy dashboard이며, 현재 주 운영 UI는 Next.js다.

## 2. 다른 PC에서 최초 실행

필수 준비:

- Git
- Docker Desktop 또는 Docker Engine + Compose
- Node.js는 로컬 frontend test/build를 직접 돌릴 때 필요하다.
- Python 3.9+ 또는 3.11은 로컬 backend test를 직접 돌릴 때 필요하다.

Clone:

```bash
git clone <REPOSITORY_URL>
cd ga4-anomaly-detector
```

환경 파일 준비:

```bash
cp .env.example .env
```

현재 `.env.example`은 존재한다. 기본 로컬 실행에는 민감 정보가 거의 없고, 주요 값은 다음과 같다.

```text
PROJECT_NAME=GA4 Anomaly Detector
DB_FILE_NAME=results_db.json
PROPHET_INTERVAL_WIDTH=0.80
PRIORITY_WATCH_IDS=prop_id1,prop_id2
```

주의:

- GA4 OAuth credential은 `.env`가 아니라 n8n UI에서 생성/연결한다.
- `.env`는 Git에 올리지 않는다.
- 다른 PC에서는 n8n credential이 자동으로 따라오지 않는다.

Docker Compose build/start:

```bash
docker compose up -d --build
```

상태 확인:

```bash
docker compose ps
docker logs --tail 80 ga4-api
docker logs --tail 80 ga4-frontend
docker logs --tail 80 ga4-dashboard
docker logs --tail 80 ga4-n8n
```

API 확인:

```bash
curl http://localhost:8000/
curl http://localhost:8000/api/v1/health
```

브라우저 접속:

```text
FastAPI docs:        http://localhost:8000/docs
Next.js dashboard:  http://localhost:3000/dashboard
Streamlit legacy:   http://localhost:8501
n8n:                http://localhost:5678
```

중지:

```bash
docker compose down
```

데이터 volume까지 삭제하고 초기화:

```bash
docker compose down -v
```

## 3. FastAPI 로컬 실행/테스트

Docker 없이 backend를 직접 실행하려면 Python venv를 만든다.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-api.txt
```

로컬 API 실행:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

테스트:

```bash
venv/bin/pytest tests/unit
```

현재 확인된 결과:

```text
73 passed
```

주의:

- Prophet/CmdStan 설치는 시간이 걸릴 수 있다.
- Dockerfile.api는 builder stage에서 CmdStan을 설치한다.
- 메모리 작은 서버에서 이미지를 직접 build하면 CmdStan build 단계가 무거울 수 있다.

## 4. Next.js 로컬 실행/빌드/테스트

Frontend 경로:

```bash
cd frontend
```

의존성 설치:

```bash
npm install
```

개발 서버:

```bash
npm run dev
```

빌드:

```bash
npm run build
```

타입 체크:

```bash
npm run lint
```

테스트:

```bash
npm run test
```

현재 확인된 결과:

```text
vitest: 3 files, 61 tests passed
tsc --noEmit: passed
```

Docker Compose의 frontend는 내부 API URL을 다음으로 사용한다.

```text
API_BASE_URL=http://api:8000
```

로컬 `npm run dev`에서 API를 별도 실행한다면 기본값은 `http://localhost:8000`이다.

## 5. Streamlit 역할과 URL

Streamlit dashboard는 `dashboard/` 디렉터리에 남아 있는 legacy dashboard다.

Docker Compose 실행 시:

```text
http://localhost:8501
```

직접 실행:

```bash
pip install -r requirements-dashboard.txt
cd dashboard
streamlit run dashboard.py --server.port=8501 --server.address=0.0.0.0
```

현재 주 운영 dashboard는 Next.js다.

```text
http://localhost:3000/dashboard
```

Streamlit은 JSON storage를 직접 읽는 초기 구조라, theme/detail/report 중심의 최신 운영 화면은 Next.js에서 확인한다.

## 6. n8n Workflow Import / Export

Compose에서 n8n은 다음 volume mount를 가진다.

```text
./n8n/workflows:/files/workflows:ro
```

중요:

- `/files/workflows`는 n8n 컨테이너 안에서 workflow JSON을 볼 수 있게 하는 read-only mount다.
- 이 파일들이 n8n UI의 draft workflow와 자동 동기화되는 것은 아니다.
- n8n UI에서 실행되는 workflow는 `n8n_data` volume 내부 SQLite DB에 저장된 draft workflow다.

로컬 Docker용 workflow:

```text
n8n/workflows/Monitoring.local-docker.json
```

이 파일은 FastAPI endpoint가 Docker network 기준으로 `http://api:8000`을 바라본다.

Generic/deployed API용 workflow:

```text
n8n/workflows/Monitoring.generic-ecommerce.json
```

이 파일은 일부 endpoint가 배포 서버 URL을 바라본다. 로컬 Docker 테스트에는 `Monitoring.local-docker.json`을 사용한다.

### UI에서 Import

1. `http://localhost:5678` 접속
2. 최초 실행이면 owner account 생성
3. Workflows 화면에서 import 선택
4. `n8n/workflows/Monitoring.local-docker.json` 업로드
5. Google Analytics OAuth credential 재연결
6. 저장 후 Execute workflow 실행

### CLI Export

컨테이너 안의 workflow export:

```bash
docker exec ga4-n8n n8n export:workflow --all --output=/tmp/n8n-workflows-export.json
docker cp ga4-n8n:/tmp/n8n-workflows-export.json /tmp/n8n-workflows-export.json
```

현재 UI DB와 repository JSON이 같은지 확인하려면 export 후 node/connection/credential을 비교한다.

```bash
node -e "const fs=require('fs'); const wf=JSON.parse(fs.readFileSync('/tmp/n8n-workflows-export.json','utf8')); console.log(Array.isArray(wf)?wf.map(x=>x.name):wf.name)"
```

## 7. GA4 OAuth Credential 연결

n8n에서 GA4 HTTP Request node들은 `googleAnalyticsOAuth2` credential이 필요하다.

연결 절차:

1. n8n UI 접속: `http://localhost:5678`
2. Credentials 메뉴로 이동
3. Google Analytics OAuth2 credential 생성
4. Google Cloud OAuth client 정보 입력
5. OAuth consent/redirect 설정 확인
6. n8n의 모든 GA4 관련 node에 같은 credential 연결

GA4 관련 node 예시:

```text
HTTP Request
HTTP Request3
HTTP Request4
GA4 Ecommerce Detection Report
GA4 Ecommerce Diagnosis Report
[Unassigned] GA4 Detection Report
[Unassigned] GA4 Diagnosis Report
```

다른 PC에서 clone한 경우:

- repository JSON에 credential name/id가 있어도 실제 credential secret은 없다.
- n8n credential은 로컬 `n8n_data` volume에 저장된다.
- workflow import 후 반드시 credential을 UI에서 다시 선택/저장한다.

## 8. n8n SQLite 직접 Write 금지 원칙

n8n 내부 SQLite는 다음을 저장한다.

- workflow draft
- credential metadata
- execution metadata
- workflow history

운영 원칙:

- 직접 write 금지
- read-only 진단은 가능
- workflow 수정은 UI import/export 또는 n8n CLI import/export로 처리
- credential은 UI에서 재연결

이유:

- repository JSON과 n8n DB draft가 자동 동기화되지 않는다.
- 직접 write 중 n8n process가 동시에 DB를 사용하면 WAL/권한/캐시 문제가 생길 수 있다.
- credential secret은 단순 JSON 편집으로 복구되지 않는다.

로컬 긴급 진단용으로만 DB 조회를 고려한다.

```bash
docker exec ga4-n8n ls -la /home/node/.n8n
```

직접 write가 필요해 보이면 먼저 export/import로 해결 가능한지 확인한다.

## 9. Workflow 실행 방법

전체 workflow는 하나지만 branch가 theme별로 나뉜다.

```text
Shared property list
  -> Sessions branch
  -> Ecommerce branch
  -> Unassigned Traffic branch
```

### Sessions

역할:

- property별 sessions detection
- channel/sessionDefaultChannelGroup 계열 diagnosis

실행:

1. n8n에서 `Monitoring - Local Docker` workflow 열기
2. `Execute workflow`
3. `HTTP Request3`, `/api/v1/analyze/batch`, `HTTP Request4`, `/api/v1/update-channels` 실행 확인
4. Next.js `/dashboard/themes/sessions` 확인

### Ecommerce

역할:

- 주요 ecommerce funnel event 합산 detection
- eventName별 diagnosis

실행:

1. `Ecommerce - Build Detection Properties`가 실행되는지 확인
2. `Loop Ecommerce Detection` 실행 확인
3. `GA4 Ecommerce Detection Report` 실행 확인
4. `POST Ecommerce Generic Detection` 실행 확인
5. anomaly가 있으면 `Loop Ecommerce Diagnosis` 이후 실행
6. Next.js `/dashboard/themes/ecommerce` 확인

주의:

- detection 결과가 anomaly가 아니면 diagnosis node는 `Node was not executed`로 보일 수 있다.
- 이 경우는 정상 path일 수 있다.

### Unassigned Traffic

역할:

- GA4 attribution quality 감시
- Unassigned session share detection
- sessionSourceMedium별 diagnosis

실행:

1. `[Unassigned] Build Properties` 실행 확인
2. `Loop Unassigned Detection` 실행 확인
3. `[Unassigned] GA4 Detection Report` 실행 확인
4. `[Unassigned] POST Detection` 실행 확인
5. response의 `should_run_diagnosis`가 true면 diagnosis branch 실행
6. Next.js `/dashboard/themes/unassigned-traffic` 확인

주의:

- Unassigned detection의 derived ratio 계산은 n8n이 아니라 FastAPI가 한다.
- lower breach는 point anomaly일 수 있지만 business alert가 아닐 수 있다.

## 10. 자주 발생한 오류와 해결법

### Port Conflict

증상:

```text
port is already allocated
```

확인:

```bash
docker ps
lsof -i :8000
lsof -i :3000
lsof -i :5678
lsof -i :8501
```

해결:

```bash
docker compose down
```

다른 프로세스가 포트를 쓰고 있으면 종료하거나 `docker-compose.yml`의 host port를 변경한다.

### `/properties/:batchRunReports` 404

증상:

```text
The requested URL /v1beta/properties/:batchRunReports was not found
```

원인:

- GA4 Data API URL expression에서 `property_id`가 비어 있다.
- 정상 URL은 다음 형태다.

```text
https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:batchRunReports
```

확인:

- GA4 HTTP Request 직전 item에 `property_id` 또는 `propertyId`가 있는지 확인
- URL expression이 다음 형태인지 확인

```text
=https://analyticsdata.googleapis.com/v1beta/properties/{{ $json.property_id || $json.propertyId }}:batchRunReports
```

해결:

- Build Properties / Prepare Payload node에서 `property_id`를 보존한다.
- Loop node를 거치면서 `property_id`가 사라지지 않게 한다.
- workflow import 후 실제 n8n UI DB에도 수정이 반영됐는지 export로 확인한다.

### Credential 미연결

증상:

```text
Credential with ID "..." does not exist for type "googleAnalyticsOAuth2"
```

원인:

- repository JSON에 남은 credential ID가 현재 PC의 n8n DB에 없다.
- 다른 PC로 clone/import하면 credential secret은 자동으로 오지 않는다.

해결:

1. n8n UI에서 Google Analytics OAuth2 credential 생성
2. 모든 GA4 HTTP Request node에서 credential 재선택
3. workflow 저장
4. 다시 실행

확인:

```bash
docker exec ga4-n8n n8n export:workflow --all --output=/tmp/check.json
docker cp ga4-n8n:/tmp/check.json /tmp/check.json
```

그 뒤 export JSON에서 GA4 node의 `credentials.googleAnalyticsOAuth2`가 비어 있지 않은지 확인한다.

### Workflow Import 불일치

증상:

- repository JSON은 수정되어 있는데 n8n UI 실행 결과는 예전 구조처럼 동작
- `a.ok(from)`
- stale node connection
- `Node was not executed`가 의도치 않은 위치에서 발생

원인:

- workflow JSON 파일과 n8n 내부 DB draft가 자동 동기화되지 않는다.
- `/files/workflows` mount는 파일을 보여줄 뿐, UI workflow를 자동 갱신하지 않는다.

해결:

1. n8n UI에서 workflow를 다시 import
2. credential 재연결
3. 저장
4. export로 실제 DB workflow 확인

export:

```bash
docker exec ga4-n8n n8n export:workflow --all --output=/tmp/current-workflows.json
docker cp ga4-n8n:/tmp/current-workflows.json /tmp/current-workflows.json
```

### `Node was not executed`

정상인 경우:

- detection에서 anomaly가 없어서 diagnosis branch가 실행되지 않음
- 조건 node나 loop done/output path가 다른 쪽으로 감

비정상인 경우:

- branch 시작점이 잘못 연결됨
- source/target node 이름이 불일치
- workflow UI DB가 repository JSON과 다름

확인:

- 해당 node의 이전 node가 실행됐는지 본다.
- detection response가 `is_anomaly` 또는 `should_run_diagnosis` true인지 확인한다.
- workflow export 후 connections source/target 누락을 검사한다.

## 11. 다른 PC에서 실행 가능 여부 판단

현재 코드 기준 판단:

```text
Docker Compose 기반 로컬 실행은 가능하다.
단, GA4 OAuth credential은 각 PC의 n8n UI에서 수동 생성/연결해야 한다.
```

가능한 이유:

- `.env.example` 존재
- Docker Compose가 API, Next.js, Streamlit, n8n을 모두 정의
- n8n local workflow JSON 존재
- API/Frontend test 통과
- n8n workflow JSON source/target 무결성 확인됨

다른 PC에서 막힐 수 있는 지점:

- Docker Desktop 미설치 또는 리소스 부족
- `8000`, `3000`, `5678`, `8501` 포트 충돌
- GA4 OAuth credential 미연결
- Google Cloud OAuth redirect URI 설정 누락
- n8n UI workflow import 후 저장하지 않음
- repository JSON과 n8n DB draft 불일치
- CmdStan/Prophet image build가 저사양 머신에서 오래 걸림

## 12. Blocker와 수정 제안

현재 blocker:

1. GA4 OAuth credential은 자동 복제되지 않는다.
2. n8n workflow JSON과 UI DB draft가 자동 동기화되지 않는다.
3. 실제 GA4 OAuth end-to-end 실행은 환경 의존적이다.
4. JSON storage는 운영 규모가 커지면 한계가 있다.

수정 제안:

1. `n8n/workflows/Monitoring.local-docker.json` import 절차를 고정하고, import 후 credential 재연결 체크리스트를 README에 연결한다.
2. workflow export 검증 스크립트를 별도 파일로 추가해 source/target/credential 누락을 자동 검사한다.
3. `.env.example`에 Next.js 로컬 개발용 `API_BASE_URL=http://localhost:8000` 주석을 추가하는 것을 검토한다.
4. n8n 실행 전 포트 확인 스크립트를 문서화하거나 Makefile로 묶는다.
5. 실제 운영 전 `docker compose up -d --build` 후 n8n에서 Sessions/Ecommerce/Unassigned를 각각 한 번씩 smoke test한다.
6. storage가 커지면 JSON에서 SQLite/PostgreSQL/Cloud SQL로 전환한다.

## 13. 빠른 체크리스트

새 PC에서 최소 실행:

```bash
git clone <REPOSITORY_URL>
cd ga4-anomaly-detector
cp .env.example .env
docker compose up -d --build
curl http://localhost:8000/api/v1/health
```

접속:

```text
Next.js:  http://localhost:3000/dashboard
n8n:      http://localhost:5678
API docs: http://localhost:8000/docs
Streamlit: http://localhost:8501
```

n8n에서 반드시 할 것:

```text
1. Monitoring.local-docker.json import
2. Google Analytics OAuth2 credential 생성
3. GA4 HTTP Request node credential 재연결
4. workflow 저장
5. Execute workflow
```

검증:

```bash
docker compose ps
docker logs --tail 80 ga4-api
docker logs --tail 80 ga4-n8n
```
