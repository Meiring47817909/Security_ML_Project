# Store Session Security Monitor

A university ML-in-security project. An online store's security admin monitors login sessions; each session is scored by a PyTorch MLP for intrusion risk (Low / Medium / High). Clicking a session shows its values, the model's attack probability, and a likely threat pattern with preventive actions taken from fixed rules on the session's values (not from the model).

- Dataset: Kaggle `dnkumars/cybersecurity-intrusion-detection-dataset` (9,537 synthetic sessions, 11 columns).
- Model: one PyTorch MLP (17 -> 64 -> 32 -> 1) with BatchNorm, dropout, Adam and early stopping.
- Apps: a model service (FastAPI, port 8001) and an admin web app (FastAPI + HTMX, port 8000).
- Theory report draft: `reports/theory.md`. Assignment brief: `docs/project_brief.md`.

All commands below are for Windows PowerShell, run from the project root.

## 1. Setup

```powershell
python -m venv .venv --system-site-packages
.venv\Scripts\python -m pip install -r requirements.txt
```

`--system-site-packages` reuses an already installed CUDA build of PyTorch. The tests and the apps run on CPU.

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

For interactive use (Jupyter or VS Code), register the venv as a kernel once and select "ML Project New (.venv)":

```powershell
.venv\Scripts\python -m ipykernel install --user --name ml-project-new --display-name "ML Project New (.venv)"
```

If you edit `notebooks/intrusion_model.py` (the source of truth), regenerate the notebook and run it again:

```powershell
.venv\Scripts\python -m jupytext --to ipynb notebooks/intrusion_model.py
```

Check that the committed notebook has saved outputs and figures:

```powershell
.venv\Scripts\python scripts\check_notebook.py notebooks\intrusion_model.ipynb --min-images 6
```

Files written to `artifacts/` (gitignored): `mlp.pt`, `preprocess.joblib`, `model_meta.json`, `metrics.csv` (per-epoch log), `test_sessions.csv`.

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

## 3. Start the two services

Open two PowerShell windows.

Window 1, the model service (`GET /health`, `POST /predict`; interactive API docs at http://127.0.0.1:8001/docs):

```powershell
.venv\Scripts\python -m uvicorn model_service.app:app --port 8001
```

Window 2, the admin web app, pointed at the model service:

```powershell
$env:MODEL_API_URL = "http://127.0.0.1:8001"
.venv\Scripts\python -m uvicorn webapp.app:app --port 8000
```

Open http://127.0.0.1:8000. The header badge shows "Hosted model" when the model service answers and "Local fallback" otherwise.

`POST /predict` returns `probability`, `risk`, `prediction`, and the rule-based `pattern` and `actions`.

| Variable | Used by | Meaning |
|---|---|---|
| `MODEL_API_URL` | web app | Base URL of the model service. If unset, or if a request fails or times out (10 s), the web app loads the model locally and keeps working (automatic local fallback). |
| `ARTIFACTS_DIR` | both | Folder with the exported model files. Default `artifacts`. |

Current deployment status: both services run locally. Deploying the model service to Hugging Face Spaces is planned but not done yet.

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
| 2.5 Desktop application | 15 | `model_service/app.py` (FastAPI API) and `webapp/` (admin dashboard on localhost). A localhost web UI is used in place of Tkinter, which the brief allows ("other technologies can be used"). **To do: confirm this choice with the lecturer.** |
| 2.6 Patience / early stopping | 5 | Notebook §11–12: patience 10 on validation loss, best weights restored |
| 2.7 Additional features | 10 (bonus) | Separate model API with automatic local fallback; hosting on Hugging Face Spaces planned, not yet deployed |
| 3.1–3.4 Theory | 30 | `reports/theory.md` (references marked `[verify]`) |
| Missing notebook outputs | -10 if missing | `notebooks/intrusion_model.ipynb` is committed after a full execution with every output and figure saved; `scripts/check_notebook.py ... --min-images 6` checks it |
| Version control | -10 if missing | Git history in this repository |

## 6. Layout

```
intrusion/        shared package: data, preprocessing, MLP, inference, rule-based playbook
notebooks/        intrusion_model.py (source) and intrusion_model.ipynb (executed)
model_service/    FastAPI model API (port 8001)
webapp/           FastAPI + HTMX admin dashboard (port 8000)
scripts/          download_data.py, check_notebook.py
tests/            pytest suite
reports/          theory.md
docs/             project brief
```
