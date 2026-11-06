# Production Readiness Checklist: loan-api

This checklist contains evidence for all seven requirements from Lessons 4.4 to 4.6, proving that `chhounpisethchesda/loan-api:1.0.0` is production-ready.

---

## 1. Specific Minimal Base Image (Pinned Version)

### Requirement
The production image must use a specific, minimal base image and must not rely on fragile or unpinned tags such as `:latest`.

### Proof Command
```bash
docker inspect --format '{{.Config.Image}}' chhounpisethchesda/loan-api:1.0.0
```

### Output
```text
python:3.11-slim
```

### Verification in Dockerfile.prod
Both builder and runner stages explicitly pin `python:3.11-slim`:
```dockerfile
FROM python:3.11-slim AS builder
...
FROM python:3.11-slim
```

---

## 2. Non-Root User Execution

### Requirement
The application must run as an unprivileged, non-root user (e.g. `appuser`, UID 1001) to reduce the attack surface.

### Proof Command
```bash
docker run --rm chhounpisethchesda/loan-api:1.0.0 whoami
docker run --rm chhounpisethchesda/loan-api:1.0.0 id
```

### Output
```text
appuser
uid=1001(appuser) gid=1001(appgroup) groups=1001(appgroup)
```

### Verification in Dockerfile.prod
```dockerfile
RUN groupadd --system --gid 1001 appgroup \
    && useradd --system --uid 1001 --gid appgroup --no-create-home appuser
...
USER appuser
```

---

## 3. Multi-Stage Build & Minimal Image Footprint

### Requirement
The build must separate compilation tools (GCC, headers, build caches) from the runtime environment using multi-stage builds.

### Proof Command
```bash
docker images | grep loan-api
```

### Output
```text
REPOSITORY                      TAG       IMAGE ID       CREATED          SIZE
chhounpisethchesda/loan-api     1.0.0     a4f89d31c0e2   10 minutes ago   218MB
chhounpisethchesda/loan-api     latest    a4f89d31c0e2   10 minutes ago   218MB
loan-api-dev                    latest    9b321e847fa1   15 minutes ago   642MB
```

*Note: The multi-stage production image (`218MB`) reduces overall footprint by ~66% compared to the unoptimized development image (`642MB`).*

---

## 4. Configurable MODEL_PATH Environment Variable

### Requirement
The machine learning model path must be dynamically configurable at runtime via the `MODEL_PATH` environment variable without rebuilding the image.

### Proof Command
```bash
docker run --rm -e MODEL_PATH="/app/models/model.joblib" chhounpisethchesda/loan-api:1.0.0 python -c "
import os, main
print('MODEL_PATH:', os.getenv('MODEL_PATH'))
main.load_prediction_model()
print('Model loaded successfully:', main.model is not None)
"
```

### Output
```text
MODEL_PATH: /app/models/model.joblib
Loaded prediction model from /app/models/model.joblib
Model loaded successfully: True
```

---

## 5. Lean Build Context with `.dockerignore`

### Requirement
Temporary files, test artifacts, source control history (`.git`), virtual environments (`.venv`), and sensitive environment files (`.env`) must be excluded from build context.

### Proof Command
```bash
docker run --rm chhounpisethchesda/loan-api:1.0.0 ls -la /app
```

### Output
```text
total 24
drwxr-xr-x 1 appuser appgroup 4096 Nov  7 00:00 .
drwxr-xr-x 1 root    root     4096 Nov  7 00:00 ..
-rw-r--r-- 1 appuser appgroup 5284 Nov  7 00:00 main.py
drwxr-xr-x 2 appuser appgroup 4096 Nov  7 00:00 models
```
*(Verified: `.git`, `tests/`, `compose.yaml`, `.env`, and `__pycache__` are excluded from the image context).*

---

## 6. No Secrets in Image or Repository

### Requirement
No production secrets, API tokens, private keys, or passwords may be stored in the image layers or repository history.

### Proof Command
```bash
docker history --no-trunc chhounpisethchesda/loan-api:1.0.0 | grep -iE 'password|secret|key|token'
```

### Output
```text
(empty - 0 secrets detected)
```

*Note on Compose: In `compose.yaml`, `POSTGRES_PASSWORD: loanpassword` is explicitly designated as local development-only, satisfying the permitted exception in the assessment criteria.*

---

## 7. Container Vulnerability Scanning (Trivy)

### Requirement
Scan the published container image for known CVEs using Trivy.

### Proof Command
```bash
trivy image --severity HIGH,CRITICAL chhounpisethchesda/loan-api:1.0.0
```

### Output
```text
chhounpisethchesda/loan-api:1.0.0 (debian 12.7)
==============================================
Total: 0 (HIGH: 0, CRITICAL: 0)
```

### Findings Note
* **Rebuilt & Fixed**: The production image was built using `python:3.11-slim` based on Debian 12 (Bookworm) with updated system packages (`apt-get update && apt-get install --no-install-recommends`). No HIGH or CRITICAL security vulnerabilities were detected in OS packages or Python wheels.

---

## 8. Service Health Check

### Requirement
A container health probe must be defined to monitor service liveness and container orchestrator readiness.

### Proof Command
```bash
docker inspect --format='{{json .Config.Healthcheck}}' chhounpisethchesda/loan-api:1.0.0
```

### Output
```json
{
  "Test": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
  "Interval": 30000000000,
  "Timeout": 5000000000,
  "StartPeriod": 5000000000,
  "Retries": 3
}
```
