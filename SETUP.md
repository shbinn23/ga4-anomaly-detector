# GA4 Anomaly Detector Setup

다른 PC에서 clone 후 로컬 Docker Compose 환경을 띄우기 위한 최소 설정 문서다. 상세 운영 절차와 장애 대응은 `RUNBOOK.md`를 본다.

## 1. 필요 도구

- Git
- Docker Desktop 또는 Docker Engine + Docker Compose
- 선택: Node.js, Python 3.9+ 또는 3.11

Node/Python은 로컬에서 테스트를 직접 실행할 때만 필요하다. Docker Compose 실행만 할 경우 Docker가 핵심이다.

## 2. Clone

```bash
git clone <REPOSITORY_URL>
cd ga4-anomaly-detector
```

## 3. 환경 파일

`.env.example`이 이미 있다. 최초 실행 시 복사한다.

```bash
cp .env.example .env
```

현재 주요 값:

```text
PROJECT_NAME=GA4 Anomaly Detector
DB_FILE_NAME=results_db.json
PROPHET_INTERVAL_WIDTH=0.80
PRIORITY_WATCH_IDS=prop_id1,prop_id2
```

주의:

- `.env`는 Git에 올리지 않는다.
- GA4 OAuth credential은 `.env`가 아니라 n8n UI에서 만든다.
- 다른 PC에서는 n8n credential이 자동 복사되지 않는다.

## 4. Docker Compose 실행

빌드 및 실행:

```bash
docker compose up -d --build
```

상태 확인:

```bash
docker compose ps
```

로그 확인:

```bash
docker logs --tail 80 ga4-api
docker logs --tail 80 ga4-frontend
docker logs --tail 80 ga4-dashboard
docker logs --tail 80 ga4-n8n
```

중지:

```bash
docker compose down
```

볼륨까지 초기화:

```bash
docker compose down -v
```

## 5. 서비스 URL

| Service | Container | URL |
| --- | --- | --- |
| FastAPI | `ga4-api` | `http://localhost:8000` |
| FastAPI Docs | `ga4-api` | `http://localhost:8000/docs` |
| Next.js Dashboard | `ga4-frontend` | `http://localhost:3000/dashboard` |
| Streamlit Legacy Dashboard | `ga4-dashboard` | `http://localhost:8501` |
| n8n | `ga4-n8n` | `http://localhost:5678` |

Health check:

```bash
curl http://localhost:8000/api/v1/health
```

## 6. n8n 최초 설정

1. `http://localhost:5678` 접속
2. 최초 owner account 생성
3. workflow import
   - 로컬 Docker용: `n8n/workflows/Monitoring.local-docker.json`
4. Google Analytics OAuth2 credential 생성
5. GA4 관련 HTTP Request node에 credential 재연결
6. workflow 저장

중요:

- `./n8n/workflows`는 컨테이너 안의 `/files/workflows`에 read-only mount된다.
- workflow JSON 파일과 n8n UI 내부 DB draft는 자동 동기화되지 않는다.
- JSON을 수정한 뒤에는 n8n UI에서 다시 import하거나 export로 실제 반영 여부를 확인한다.
- n8n SQLite 직접 write는 금지한다. 진단은 read-only로만 한다.

## 7. 로컬 테스트 명령

Backend:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-api.txt
venv/bin/pytest tests/unit
```

Frontend:

```bash
cd frontend
npm install
npm run lint
npm run test
npm run build
```

## 8. 포트 충돌 확인

사용 포트:

```text
8000 FastAPI
3000 Next.js
8501 Streamlit
5678 n8n
```

충돌 확인:

```bash
lsof -i :8000
lsof -i :3000
lsof -i :8501
lsof -i :5678
```

이미 실행 중인 compose stack을 내릴 때:

```bash
docker compose down
```

## 9. 다른 PC 실행 가능 여부

현재 구조는 다른 PC에서 clone 후 Docker Compose로 실행 가능하다.

단, 아래는 수동 설정이 필요하다.

- `.env.example`을 `.env`로 복사
- n8n owner account 생성
- `Monitoring.local-docker.json` import
- Google Analytics OAuth2 credential 생성 및 node 재연결

가장 흔한 blocker는 GA4 credential 미연결과 workflow JSON/n8n DB 불일치다.
