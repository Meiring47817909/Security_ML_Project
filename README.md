# Store Session Security Monitor

A university ML-in-security project. An online store's security admin monitors login sessions; each session is scored by a PyTorch MLP for intrusion risk (Low / Medium / High). Clicking a session shows its values, the model's attack probability, and a likely threat pattern with preventive actions taken from fixed rules on the session's values (not from the model).

- Dataset: Kaggle `dnkumars/cybersecurity-intrusion-detection-dataset` (9,537 synthetic sessions, 11 columns).
- Model: one PyTorch MLP (17 -> 64 -> 32 -> 1) with BatchNorm, dropout, Adam and early stopping.
- Apps: a model API (FastAPI) **hosted on Render at https://store-session-mlp.onrender.com**, and an admin web app (FastAPI + HTMX, port 8000) that calls it.

All commands below are for Windows PowerShell, run from the project root.

## 1. Setup

Requires Python 3.13.

```powershell
git clone https://github.com/Meiring47817909/Security_ML_Project.git
cd Security_ML_Project
python -m venv .venv --system-site-packages
.venv\Scripts\python -m pip install -r requirements.txt
```

PyTorch is not in `requirements.txt`, because the right build depends on the machine. `--system-site-packages` reuses a PyTorch that is already installed system-wide (the notebook was trained with the CUDA build of 2.11.0). If PyTorch is not installed yet, add it to the venv:

```powershell
# CPU only (enough for the tests, the apps and the notebook)
.venv\Scripts\python -m pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu
```

The tests and the apps run on CPU.

Download the dataset (kept in the kagglehub cache, never committed, never modified):

```powershell
.venv\Scripts\python scripts\download_data.py
```

## 2. Run the notebook

The notebook `notebooks/intrusion_model.ipynb` contains all model code and every figure and metric. It is generated from the plain-text source `notebooks/intrusion_model.py` with Jupytext.

Execute it end to end (this also writes the model files to `artifacts/`, which the apps need):

```powershell
.venv\Scripts\python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 notebooks/intrusion_model.ipynb
```

For interactive use (Jupyter or VS Code), register the venv as a kernel once and select "Security ML Project (.venv)":

```powershell
.venv\Scripts\python -m ipykernel install --user --name security-ml-project --display-name "Security ML Project (.venv)"
```

If you edit `notebooks/intrusion_model.py` (the source of truth), regenerate the notebook and run it again:

```powershell
.venv\Scripts\python -m jupytext --to ipynb notebooks/intrusion_model.py
```

Check that the committed notebook has saved outputs and figures:

```powershell
.venv\Scripts\python scripts\check_notebook.py notebooks\intrusion_model.ipynb --min-images 6
```

Files written to `artifacts/`: `mlp.pt`, `preprocess.joblib`, `model_meta.json` (committed, needed by the hosted API), `test_sessions.csv` (committed, the cleaned test split the dashboard replays as its feed) and `metrics.csv` (per-epoch log, gitignored). The committed files mean the apps run straight after cloning, without re-running the notebook. After retraining, commit the model files and push so Render redeploys the new model.

### Notebook sections

| § | Content |
|---|---|
| 1 | Setup (seed 42) |
| 2 | Raw data, untouched (SHA-256 fingerprint) |
| 3 | Data-quality report |
| 4 | Cleaning, one step per cell (encryption, identifier, login counts) |
| 5 | Stratified 70 / 15 / 15 split |
| 6 | Class balance |
| 7 | Encode and scale (17 features) |
| 8 | Model architecture |
| 9 | DataLoaders |
| 10 | Metric function |
| 11 | Early stopping |
| 12 | Training loop (per-epoch log) |
| 13 | Training curves: loss, metrics per epoch |
| 14 | Final test evaluation: metrics, ROC, precision-recall, confusion matrix |
| 15 | Export for the services |

## 3. Run the app

The model API is **hosted on Render** at **https://store-session-mlp.onrender.com** (interactive docs: https://store-session-mlp.onrender.com/docs). The admin dashboard runs on your PC and calls it.

### 3.1 Settings in `.env`

Create `.env` in the project root (it is gitignored; never commit it). See `.env.example`:

```
MODEL_API_URL=https://store-session-mlp.onrender.com
MODEL_API_KEY=<your API key>
```

### 3.2 Start the dashboard (uses the hosted model)

```powershell
.venv\Scripts\python -m uvicorn webapp.app:app --port 8000 --env-file .env
```

Open http://127.0.0.1:8000. The header badge shows **"Hosted model"** when Render answers and **"Local fallback"** otherwise (the dashboard then scores with its own copy of the model and keeps working).

The hosted API only accepts requests that carry the project's API key, which is not published. Without it (or without a `.env`), the dashboard still works fully: every request falls back to the local model, and the badge shows "Local fallback". To use your own hosted copy, deploy it as in 3.5 with your own key.

Render's free service sleeps after about 15 minutes without requests; the first request can then take up to a minute. Before a demo, wake it by opening https://store-session-mlp.onrender.com/health (or `curl.exe https://store-session-mlp.onrender.com/health`) and wait for `{"status":"ok","model_version":"1.0.0","auth":"on"}`.

### 3.3 Run everything locally instead (no internet API)

Two PowerShell windows:

```powershell
# Window 1: local model API (interactive docs at http://127.0.0.1:8001/docs)
.venv\Scripts\python -m uvicorn model_service.app:app --port 8001
```

```powershell
# Window 2: dashboard pointed at the local API
$env:MODEL_API_URL = "http://127.0.0.1:8001"
$env:MODEL_API_KEY = ""
.venv\Scripts\python -m uvicorn webapp.app:app --port 8000
```

### 3.4 The model API

| Route | Access | Returns |
|---|---|---|
| `GET /` | open | redirects to `/docs` |
| `GET /docs` | open | interactive documentation (click **Authorize** and paste the API key to try `/predict`) |
| `GET /health` | open | `{"status": "ok", "model_version": "1.0.0", "auth": "on" \| "off"}` |
| `POST /predict` | needs `X-API-Key` when a key is configured | `probability`, `risk`, `prediction`, rule-based `pattern` and `actions`; 401 for a missing/wrong key, 422 for invalid input |

Example request body:

```json
{"network_packet_size": 500, "protocol_type": "TCP", "login_attempts": 4, "session_duration": 300,
 "encryption_used": "None", "ip_reputation_score": 0.3, "failed_logins": 4, "browser_type": "Chrome",
 "unusual_time_access": 0}
```

| Variable | Used by | Meaning |
|---|---|---|
| `MODEL_API_URL` | web app | Base URL of the model API. If unset, or if a request fails or times out (10 s), the web app loads the model locally (automatic local fallback). |
| `MODEL_API_KEY` | both | Shared secret. On the API, `POST /predict` then requires `X-API-Key: <key>` (compared in constant time); on the web app, it is sent with every request. Never commit it. |
| `ARTIFACTS_DIR` | both | Folder with the exported model files. Default `artifacts`. |
| `PORT` | API container | Port to listen on; Render sets it, default 7860. |

Generate an API key once and keep it private:

```powershell
.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3.5 Hosting on Render

The API is deployed as a Docker web service on Render's free plan (region Oregon, US West):

- `Dockerfile` (repo root): Python 3.13 slim, CPU-only PyTorch 2.11.0, pinned requirements from `deploy/hf_space/requirements.txt` (scikit-learn 1.8.0 to match the saved preprocessor), copies only `intrusion/`, `model_service/` and the three model files; listens on `$PORT`.
- `.dockerignore`: keeps `.venv`, notebooks, tests, data and the dashboard out of the build.
- `render.yaml`: Render Blueprint (free Docker web service, health check `/health`, auto-deploy on push to `main`). `MODEL_API_KEY` is entered in the Render dashboard (`sync: false`), never stored in git.
- `artifacts/mlp.pt`, `artifacts/preprocess.joblib` and `artifacts/model_meta.json` (23 KB) are committed so Render can build from the repository; the rest of `artifacts/` stays ignored.

Deploy or update: push to `main` on GitHub; Render rebuilds automatically. First-time setup: Render dashboard → **New → Blueprint** → select this repository → enter `MODEL_API_KEY` → deploy.

Test the image locally (as Render runs it):

```powershell
docker build -t store-session-mlp-render .
docker run --rm -p 7860:7860 -e MODEL_API_KEY=<key> store-session-mlp-render      # http://127.0.0.1:7860/docs
```

Measured: about 0.4 s per request from South Africa once awake; about 243 MB memory in the container (free plan limit 512 MB).

**Hugging Face Spaces (not used).** `deploy/hf_space/` and `scripts/build_hf_space.py` build an equivalent Docker Space, but Hugging Face now requires a PRO subscription to run Docker Spaces, so Render was used instead.

## 4. Tests

```powershell
.venv\Scripts\python -m pytest -q
```

## 5. Rubric map

| Rubric item | Marks | Where it is met |
|---|---|---|
| 2.1 Development of model | 20 | Notebook §8 (architecture printed in full), §10–12 (metric function, early stopping, hand-written training loop). The `MLP` class is imported from `intrusion/model.py` so the notebook and both services run identical code |
| 2.2 Train / validation / test split | 5 | Notebook §5: stratified 70/15/15, seed 42, class balance per split |
| 2.3 Logging of metrics per iteration | 15 | Notebook §12: one row per epoch with loss, accuracy, precision, recall, F1, AUC for train and validation; also saved to `artifacts/metrics.csv` |
| 2.4 Metric graphs (Matplotlib) | 15 | Notebook §13–14: loss curve, metric-vs-epoch curves, ROC, precision-recall, confusion matrix |
| 2.5 Desktop application | 15 | `model_service/app.py` (FastAPI API, hosted on Render) and `webapp/` (admin dashboard on localhost). A localhost web UI is used in place of Tkinter, which the brief allows ("other technologies can be used") |
| 2.6 Patience / early stopping | 5 | Notebook §11–12: patience 10 on validation loss, best weights restored |
| 2.7 Additional features | 10 (bonus) | **Model hosted** as a Docker web service on Render (https://store-session-mlp.onrender.com/docs), protected by an API key (`X-API-Key`), with automatic local fallback in the dashboard |
| 3.1–3.4 Theory | 30 | Separate written report (not in this repository) |
| Missing notebook outputs | -10 if missing | `notebooks/intrusion_model.ipynb` is committed after a full execution with every output and figure saved; `scripts/check_notebook.py ... --min-images 6` checks it |
| Version control | -10 if missing | Git history in this repository |

## 6. Layout

```
intrusion/        shared package: data, preprocessing, MLP, inference, rule-based playbook
notebooks/        intrusion_model.py (source) and intrusion_model.ipynb (executed)
model_service/    FastAPI model API (port 8001)
webapp/           FastAPI + HTMX admin dashboard (port 8000)
scripts/          download_data.py, check_notebook.py, build_hf_space.py
Dockerfile        Docker image of the model API (used by Render)
render.yaml       Render Blueprint (free Docker web service)
.env.example      template for .env (MODEL_API_URL, MODEL_API_KEY)
deploy/hf_space/  Hugging Face Space variant (not used: Docker Spaces need PRO)
tests/            pytest suite
artifacts/        trained model files and the dashboard's feed data
mlp-diagram.html  diagram of the MLP architecture
```
