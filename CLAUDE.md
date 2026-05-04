# Claude Code 작업 지침

## 1. 설계 원칙 (Core Principles)

### SoC (관심사의 분리)
- 모듈 간 결합도(Coupling) 최소화, 응집도(Cohesion) 극대화
- 기능별 철저한 모듈화
- 계층 간 의존성 방향 단방향 유지 (상위 → 하위)

### Data Integrity (데이터 무결성)
- 편의를 위한 설계 타협 금지
- 데이터 정규화 3NF 이상 준수
- 제약 조건(Constraints) 설정 최우선

### Robust Pipeline
- 모든 파이프라인에 멱등성(Idempotency) 보장 필수
- 중복 적재 방지 로직 항상 포함
- 확장성(Scalability) 설계 단계부터 고려

---

## 2. 코드 품질 기준

### DRY & 추상화
- 중복 코드 발견 시 공통 모듈/함수로 분리
- 과도한 추상화 vs 부족한 추상화 교차 검증
- 추상화가 가독성을 해치면 DRY보다 가독성 우선

### SRP (단일 책임 원칙)
- God Class/Function 형태 금지
- 한 클래스/함수는 한 가지 책임만
- 클래스 내 Public 메소드 최소화
- 책임 최소 단위로 분할

### 코드 리뷰 기준
- 논리적/기술적 오류 발견 시 즉시 지적
- 과도한 칭찬 없이 팩트 기반 피드백
- 문제점 발견 시 수정 방향까지 반드시 제시
- 동일한 실수 반복 시 구조적 원인까지 분석

---

## 3. 배포 환경

### 로컬
- OS: macOS (Apple Silicon M4, arm64)
- IDE: IntelliJ
- Python: venv 기반

### 서버
- Provider: GCP e2-micro Always Free
- OS: Ubuntu 22.04 LTS (amd64)
- RAM: 1GB (메모리 제한 항상 고려)
- IP: 설정 후 .env로 관리 (하드코딩 금지)
- Docker: 29.4.1 / Compose: v5.1.3

### 빌드 규칙
- 반드시 --platform linux/amd64 명시
- 무거운 빌드(prophet 등)는 로컬에서만
- 이미지 압축 후 scp로 전송

---

## 4. 프로젝트 구조 규칙

### 디렉토리
- 기능 단위로 폴더 분리
- 공통 유틸리티는 core/ 또는 utils/ 하위
- 설정값은 core/config.py 단일 진입점으로 관리

### 환경변수
- 모든 환경변수는 .env로 관리
- 하드코딩 금지
- 민감 정보는 절대 GitHub push 금지

### Git
- 커밋 메시지 규칙 준수
  feat / fix / refactor / chore / docs
- 기능 단위로 커밋 (너무 크거나 작지 않게)
- .env, venv/, *.tar.gz는 .gitignore 필수

---

## 5. 불확실할 때 원칙

- 모르면 아는 척하지 말고 즉시 질문
- 다중 해석 가능한 요구사항은 임의 추측 금지
- 설계 방향이 불명확하면 구현 전 먼저 확인
- 빠른 구현보다 올바른 구조 우선
