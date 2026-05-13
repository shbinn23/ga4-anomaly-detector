# n8n Workflows

## Files

- `Monitoring.json`
  - Original exported workflow.
  - Current sessions detection and channel diagnosis flow.

- `Monitoring.generic-ecommerce.json`
  - Copy of `Monitoring.json` with an added ecommerce generic flow.
  - Existing sessions workflow is preserved.

- `Monitoring.local-docker.json`
  - Local Docker test version.
  - FastAPI endpoints point to `http://api:8000`.
  - Import this into the local n8n container started by this repository's `docker-compose.yml`.

## Added Ecommerce Flow

```text
Existing property list
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

## Detection

GA4 request:

```text
dimensions: date
metrics: eventCount
dimensionFilter: eventName in [view_item, add_to_cart, begin_checkout, purchase]
```

FastAPI request:

```text
POST /api/v1/analyze/generic
mode: detection
domain: ecommerce
metric_name: eventCount
dimensions: {}
```

## Diagnosis

Triggered only when detection returns `is_anomaly: true`.

GA4 request:

```text
dimensions: date, eventName
metrics: eventCount
dimensionFilter: eventName in [view_item, add_to_cart, begin_checkout, purchase]
```

FastAPI request:

```text
POST /api/v1/analyze/generic
mode: diagnosis
domain: ecommerce
metric_name: eventCount
dimensions: { eventName }
```

## Local Test URL

The exported workflow currently points to the deployed API:

```text
http://34.172.65.42:8000
```

For local Docker testing, import:

```text
n8n/workflows/Monitoring.local-docker.json
```

It already points all FastAPI calls to:

```text
http://api:8000
```

Local URLs:

```text
n8n:       http://localhost:5678
API:       http://localhost:8000
Dashboard: http://localhost:8501
```

Start local stack:

```bash
docker compose up -d
```

Notes:

- The first local n8n login requires creating an owner account.
- Credentials from n8n Cloud are not available automatically in local Docker.
- Recreate or reconnect the Google Analytics OAuth credential before executing the imported workflow.
- The mounted workflow files are available inside n8n at `/files/workflows`.
```
