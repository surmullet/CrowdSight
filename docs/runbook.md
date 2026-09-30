# CrowdSight Operations & Deployment Runbook

## 1. Prerequisites & Environment Setup

### 1.1 Local Development Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: v20 or v22 LTS with `pnpm`
- **System Tools**: `ffmpeg` (required for video decoding and proxy transcoding)
- **C++ Build Tools**: Required for Shapely/NumPy wheel installations on some environments

### 1.2 Quickstart Commands
```bash
# 1. Setup Backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
pip install -r requirements/crowd-inference-cu121-windows.txt  # Or CPU equivalents

# 2. Setup Frontend
cd web
pnpm install
pnpm run build
cd ..

# 3. Start Application
uvicorn crowdsight.service.api.app:app --host 0.0.0.0 --port 8000
```

---

## 2. Docker Deployment

### 2.1 Single-Command Launch
```bash
docker compose up -d --build
```

### 2.2 Verifying Service Health
```bash
curl -f http://localhost:8000/health
# Response: {"status": "ok", "liveness": true, "readiness": true, "database": "connected"}
```

---

## 3. Management CLI Commands

CrowdSight includes a comprehensive operator CLI (`crowdsight`):

```bash
# 1. Scan and register incoming video footage into server catalog
crowdsight media scan /path/to/media/folder

# 2. Register a specific video file with checksum calculation
crowdsight media register /path/to/video.mp4 --name "Gate Entrance Cam 1"

# 3. Verify cryptographic integrity of model profile and checkpoint
crowdsight model verify configs/models/crowd_best_local.yaml

# 4. Trigger manual data retention purge of sessions older than N days
crowdsight session purge --older-than-days 30

# 5. Reprocess a session with modified frame stride or synthetic options
crowdsight session reprocess <session-id> --frame-stride 2
```

---

## 4. Operational Troubleshooting

### 4.1 Issue: `MODEL_CHECKPOINT_MISSING`
- **Symptom**: Session fails immediately before starting with code `MODEL_CHECKPOINT_MISSING`.
- **Diagnosis**: Checkpoint weights file does not exist at configured path.
- **Resolution**:
  - Verify `CROWDSIGHT_CROWD_CHECKPOINT` environment variable points to a valid file.
  - For testing/CI environments, enable `use_synthetic: true` to run deterministic inference without model weights.

### 4.2 Issue: `MODEL_CHECKPOINT_HASH_MISMATCH`
- **Symptom**: Job fails with `MODEL_CHECKPOINT_HASH_MISMATCH`.
- **Diagnosis**: Checkpoint SHA-256 does not match profile's expected hash (`12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc`).
- **Resolution**: Re-download the official model checkpoint or run `crowdsight model verify` to inspect the digest.

### 4.3 Issue: Video Not Playable in Browser
- **Symptom**: Video does not display in web review workspace (e.g. HEVC or non-standard container).
- **Diagnosis**: Video codec is not natively supported by browser `<video>`.
- **Resolution**: System automatically generates an H.264 web proxy using FFmpeg (`src/crowdsight/service/storage/proxy.py`). Ensure `ffmpeg` is installed and available on system PATH.

### 4.4 Issue: Orphaned Crashed Jobs
- **Symptom**: Server restarted while sessions were in `RUNNING` status.
- **Resolution**: Automated recovery occurs during FastAPI lifespan startup (`JobManager.recover_orphaned_jobs()`). Orphaned jobs are marked `FAILED` with code `WORKER_CRASHED` and preserved for inspection.
