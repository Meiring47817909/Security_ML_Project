# Store Session Security Monitor: Complete Project Handover

> **What this is.** The full state of the ML project as of **18 October 2026**, written so the work can continue in a new Claude account with no memory of earlier conversations. Everything needed is here: what was built, why, where the files are, how to run them, the decisions made, the known pitfalls, and what is left to do.
>
> **Starting a new Claude session?** Open Claude Code in `C:\Users\meiri\Desktop\Claude_Code_Projects` and paste the prompt from **section 18**.

---

## Contents
1. Status at a glance
2. Folders and files on this machine
3. Environment
4. Quick-start commands
5. The assignment (rubric)
6. Scenario
7. Dataset
8. Data preparation (notebook §2–§5)
9. Encode and scale (§7)
10. The model (§8)
11. Training (§9–§12)
12. Results (§14)
13. Code architecture, file by file
14. Notebook workflow and section map
15. Decision log: what we tried, chose and rejected
16. Known issues and pitfalls
17. Remaining work, including the Hugging Face hosting plan
18. Prompt for the next Claude session
19. Demo script
20. Likely questions, short answers

---

## 1. Status at a glance

| Area | Status |
|---|---|
| Model notebook (single PyTorch MLP) | ✅ Done, executed, outputs saved |
| Data cleaning (incl. the login-count fix) | ✅ Done |
| Model API (FastAPI) | ✅ Done, works locally on port 8001 |
| Admin dashboard (FastAPI + HTMX) | ✅ Done, works locally on port 8000, with automatic local fallback |
| Tests | ✅ 79 passing |
| Theory report draft `reports/theory.md` | ✅ Draft. **You must verify the references and rewrite it in your own words** |
| Git | ✅ Local repo, 2 commits. ❌ **Not pushed to GitHub yet** |
| Hosting on Hugging Face Spaces (bonus) | ⏳ Planned, not started (plan in section 17) |
| "Analysis" text in notebook §14 | ⏳ Placeholder for you to write |
| Lecturer OK for a web UI instead of Tkinter | ⏳ To ask |

**The current project is `Security_ML_Project`** (renamed from `ML_Project_New` on 2026-10-19). `ML_Project` is an older, larger version, kept for reference only.

## 2. Folders and files on this machine

Root: `C:\Users\meiri\Desktop\Claude_Code_Projects\`

| Path | What it is |
|---|---|
| `ML_Project.md` | The original assignment brief from the lecturer (rubric) |
| `handout.md` | This file |
| `mlp-diagram.html` | Interactive diagram of the MLP, tracing two real sessions layer by layer. Open it in any browser; works offline |
| **`Security_ML_Project\`** | **The current project. Work here.** Its own git repo (branch `main`) |
| `ML_Project\` | Older version (git, branch `main`, 20 commits). It has 3 baseline models, a long EDA, SHAP/XAI explanations and an integrity check. Superseded by `Security_ML_Project`; keep for reference |
| `ML_Project\docs\superpowers\specs\2026-10-04-store-session-monitor-design.md` | The original full design spec (describes the older version, including XAI and baselines) |
| `ML_Project\docs\superpowers\plans\2026-10-04-store-session-monitor.md` | The original implementation plan. **Task 11 there is the Hugging Face hosting task**, never done |

**Online pages from the old account will not open from a new account.** They are private to the account that made them:
- "Inside the Session MLP" diagram. Use the local copy `mlp-diagram.html` instead.
- "Cyber Threat Text Explorer", for the text dataset we rejected. Not needed.

### Inside `Security_ML_Project\`

```
Security_ML_Project/
├── README.md                     setup, commands, notebook section table, rubric map
├── requirements.txt              pip dependencies (torch comes from the system install)
├── pytest.ini                    testpaths = tests, pythonpath = .
├── .gitignore                    data/, artifacts/, .venv/, __pycache__/, *.pyc, .ipynb_checkpoints/, .env, .playwright-mcp/
├── docs/project_brief.md         copy of the assignment brief
├── notebooks/
│   ├── intrusion_model.py        SOURCE OF TRUTH (Jupytext "percent" format)
│   └── intrusion_model.ipynb     generated from the .py, executed, outputs saved (committed)
├── intrusion/                    shared Python package (notebook, API and dashboard all use it)
│   ├── data.py                   load raw CSV, quality report, cleaning steps, split
│   ├── preprocess.py             feature lists, ColumnTransformer, Session input schema
│   ├── model.py                  the MLP class
│   ├── inference.py              risk levels, save/load artifacts, Predictor
│   └── playbook.py               rule-based threat pattern + preventive actions
├── model_service/app.py          FastAPI model API (port 8001)
├── webapp/                       FastAPI + Jinja2 + HTMX dashboard (port 8000)
│   ├── app.py  client.py  feed.py
│   ├── templates/  (base, index, _rows, _row, _counters, _pause, new, detail)
│   └── static/app.css
├── scripts/
│   ├── download_data.py          downloads the dataset via kagglehub, prints path + hash
│   └── check_notebook.py         fails if the notebook has errors or too few figures
├── tests/                        79 pytest tests
├── reports/theory.md             theory report draft (rubric section 3)
└── artifacts/                    (gitignored) created by running the notebook
```

## 3. Environment

| Item | Value |
|---|---|
| OS | Windows 11 Pro |
| GPU | NVIDIA GeForce RTX 4070 Laptop (8 GB), CUDA available |
| Python | 3.13.6 (system install) |
| PyTorch | 2.11.0+cu128, installed **system-wide**, not in requirements.txt |
| Virtual env | `Security_ML_Project\.venv`, created with `--system-site-packages` so it reuses the system CUDA PyTorch |
| Key packages | scikit-learn 1.8.0, pandas 2.3.1, numpy 2.3.2, fastapi 0.135.2, pydantic 2.11.10, httpx 0.28.1, jinja2 3.1.6, uvicorn 0.41.0, joblib 1.5.3, matplotlib 3.10.8, kagglehub 1.0.2, jupytext 1.19.6, nbconvert 7.17.0 |
| Dataset location | kagglehub cache: `C:\Users\meiri\.cache\kagglehub\datasets\dnkumars\cybersecurity-intrusion-detection-dataset\versions\2\cybersecurity_intrusion_data.csv` |
| Raw file SHA-256 | `ef92832692c7ad45225d38f637a6a5c2d26d39a10157654b6c56c61a7850d0f7` (must never change) |
| Shells | PowerShell (primary) and Git Bash |

## 4. Quick-start commands

Run everything from `C:\Users\meiri\Desktop\Claude_Code_Projects\Security_ML_Project` in PowerShell.

**Fresh setup** (only if `.venv` is missing):
```powershell
python -m venv .venv --system-site-packages
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts\download_data.py      # prints the path, rows 9537, and the hash
```

**Run the tests:**
```powershell
.venv\Scripts\python -m pytest -q                   # expect: 79 passed
```

**Re-run the notebook end to end.** This also re-creates `artifacts/`, which the apps need:
```powershell
.venv\Scripts\python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 notebooks/intrusion_model.ipynb
.venv\Scripts\python scripts\check_notebook.py notebooks\intrusion_model.ipynb --min-images 6
```

**After editing the notebook source (`.py`):**
```powershell
.venv\Scripts\python -m jupytext --to ipynb notebooks/intrusion_model.py
# then run the nbconvert command above
```

**Use the notebook interactively** (VS Code or Jupyter). Register the kernel once, then pick "ML Project New (.venv)":
```powershell
.venv\Scripts\python -m ipykernel install --user --name ml-project-new --display-name "ML Project New (.venv)"
```

**Start the apps** (two terminals):
```powershell
# Terminal 1: model API  → http://127.0.0.1:8001/docs
.venv\Scripts\python -m uvicorn model_service.app:app --port 8001
# Terminal 2: dashboard  → http://127.0.0.1:8000
$env:MODEL_API_URL = "http://127.0.0.1:8001"; .venv\Scripts\python -m uvicorn webapp.app:app --port 8000
```

**Commit:**
```powershell
git add -A; git commit -m "your message"
```

## 5. The assignment (rubric)

From `ML_Project.md` (the lecturer's brief):
- All model code must be in a Jupyter notebook, and every figure and metric must be visible in it.
- Git must be used throughout.

| Item | Marks |
|---|---|
| 2.1 Model development | 20 |
| 2.2 Train / validation / test split | 5 |
| 2.3 Metric logging every iteration (accuracy, precision, recall, F1, AUC, loss) | 15 |
| 2.4 Metric graphs with Matplotlib (ROC, PR, confusion matrix, loss curve) | 15 |
| 2.5 API (Flask/FastAPI) plus a desktop app (Tkinter suggested; "other technologies can be used") | 15 |
| 2.6 Patience / early stopping | 5 |
| 2.7 Bonus: XAI, hosting the model, other extras | 10 |
| 3.1 Scenario / 3.2 Architecture / 3.3 Results analysis / 3.4 Real-world use (with academic references) | 3 / 10 / 10 / 7 |
| Deductions: missing notebook outputs / poor version control | −10 / −10 |

**Where each item is met in `Security_ML_Project`:**

| Item | Where |
|---|---|
| 2.1 | Notebook §8 (architecture printed in full), §10–§12 (metric function, early stopping, hand-written training loop). The `MLP` class is imported from `intrusion/model.py` so the notebook and the services run identical code |
| 2.2 | Notebook §5 |
| 2.3 | Notebook §12 per-epoch log; `artifacts/metrics.csv` |
| 2.4 | Notebook §13 (loss, metrics per epoch), §14 (ROC, PR, confusion matrix) |
| 2.5 | `model_service/` + `webapp/`. **Web UI in place of Tkinter: confirm with the lecturer** |
| 2.6 | Notebook §11–§12 |
| 2.7 | Separate model API with automatic local fallback. Hugging Face hosting planned. XAI was deliberately removed (section 15) |
| 3.x | `reports/theory.md` |

## 6. Scenario

An online store's security admin monitors customer and staff **login sessions**. The MLP gives each session a probability of being an intrusion, which maps to a risk level:

| Probability | Risk |
|---|---|
| below 0.4 | **Low** |
| 0.4 to below 0.7 | **Medium** |
| 0.7 and above | **High** |

The dashboard shows a live feed of scored sessions. Clicking a session shows its values, the probability, and a **likely threat pattern with preventive actions**. These come from **fixed rules on the session's values, not from the model** (`intrusion/playbook.py`):

| Rule (checked in this order) | Pattern | Actions |
|---|---|---|
| Risk is Low | "None" | "No action" |
| failed_logins ≥ 3 **or** login_attempts ≥ 7 | Brute force / credential stuffing | Temporary account lockout; Enforce MFA; CAPTCHA after repeated failures; Alert account owner |
| ip_reputation_score > 0.6 | Known-bad source | Block or rate-limit the IP; Add a WAF rule; Check other sessions from that IP |
| browser_type = Unknown | Automated bot / scripted client | Bot detection / challenge; Require JavaScript-capable client; Rate-limit |
| otherwise | Anomalous session | Manual review; Step-up authentication |

## 7. Dataset

- Kaggle **`dnkumars/cybersecurity-intrusion-detection-dataset`** v2, file `cybersecurity_intrusion_data.csv`.
- **9,537 rows × 11 columns**, target `attack_detected` (0/1), **44.7% attacks**, no duplicate rows.
- Columns:
  - `session_id`: an ID, dropped.
  - 6 numeric: `network_packet_size`, `login_attempts`, `session_duration`, `ip_reputation_score`, `failed_logins`, `unusual_time_access` (0/1).
  - 3 categorical, with values in this fixed order:
    - `protocol_type`: ICMP, TCP, UDP
    - `encryption_used`: AES, DES, missing → "None"
    - `browser_type`: Chrome, Edge, Firefox, Safari, Unknown
- **Synthetic data.** Found in the earlier analysis (`ML_Project`, notebook §6.6–6.7):
  - `failed_logins ≥ 3`, `login_attempts ≥ 7` and `ip_reputation_score > 0.6` each mean attack in 100% of cases.
  - An Unknown browser raises the attack rate.
  - The remaining sessions are about 18% attacks with almost no learnable signal.
  - So **every model tops out at about 88% accuracy**. Random forest and gradient boosting scored 0.882 and 0.885 in `ML_Project`.

## 8. Data preparation (notebook §2–§5)

**Rule: the raw CSV is never modified.** The notebook only reads it and prints its SHA-256. Every cleaning function returns a **new** DataFrame.

| § | Step | Detail |
|---|---|---|
| 2 | Load raw | Prints path, hash, shape, dtypes, `head()` |
| 3 | Quality report | Missing: only `encryption_used` (1,966). Duplicates: 0. Ranges: plausible. **730 rows have failed_logins > login_attempts** |
| 4.1 | `fill_missing_encryption` | NaN → "None" (it means no encryption, a real category) |
| 4.2 | `drop_identifier` | Drops `session_id` |
| 4.3 | `fix_login_counts` | In the 730 inconsistent rows, sets `login_attempts = failed_logins`. Increases: +1 in 526 rows, +2 in 166, +3 in 33, +4 in 5. No row reaches 7+ attempts. These rows are 70.7% attacks |
| 4.4 | `clean()` + assertions | `clean = fix_login_counts(drop_identifier(fill_missing_encryption(df)))`. Asserts that the raw frame still has its NaNs, ID and 730 odd rows |
| 5 | `split(df, seed=42)` | Stratified **70/15/15 → 6,675 / 1,431 / 1,431**, each ~44.7% attacks |
| 6 | Class balance | Bar chart (train) |

**Seed 42 everywhere** (`random`, NumPy, `torch.manual_seed`, `torch.cuda.manual_seed_all`, cuDNN deterministic, the DataLoader generator, sklearn `random_state`) gives identical runs.

**Effect of the login fix**, measured on the same test set:

| | Accuracy | Precision | Recall | F1 | AUC | TN/FP/FN/TP |
|---|---|---|---|---|---|---|
| Before (commit `66dd9c6`) | 0.8812 | 0.9896 | 0.7422 | 0.8482 | 0.8794 | 786/5/165/475 |
| After (current) | 0.8798 | 0.9776 | 0.7484 | 0.8478 | 0.8804 | 780/11/161/479 |

The difference is 2 test sessions, within noise. The data became consistent without changing performance.

## 9. Encode and scale (notebook §7)

- `build_preprocessor()` creates a `ColumnTransformer`:
  - **StandardScaler** on the 6 numeric columns: `(x − mean) ÷ std`.
  - **OneHotEncoder** on the 3 categoricals, with a fixed category order and `handle_unknown="ignore"`.
- The result is **17 features**: 6 scaled, then ICMP/TCP/UDP, AES/DES/None, Chrome/Edge/Firefox/Safari/Unknown.
- **Fitted on train only**, then applied to validation and test, to avoid data leakage.
- Train means and standard deviations:

  | Column | Mean | Std |
  |---|---|---|
  | packet size | 500.5 | 198.1 |
  | login attempts | 4.15 | 1.89 |
  | duration | 789.4 | 785.4 |
  | IP reputation | 0.330 | 0.178 |
  | failed logins | 1.52 | 1.03 |
  | unusual time | 0.152 | 0.359 |

  These were from before the login fix; login attempts shifts slightly after it.
- Saved as `artifacts/preprocess.joblib`. The API applies exactly the same transformation to live sessions.

## 10. The model (notebook §8)

```
 9 session values
        │  encode & scale (§7)
        ▼
 17 inputs
        ▼
 Linear(17 → 64) → BatchNorm1d(64) → ReLU → Dropout(0.2)     Hidden layer 1
        ▼  64 numbers
 Linear(64 → 32) → BatchNorm1d(32) → ReLU → Dropout(0.2)     Hidden layer 2
        ▼  32 numbers
 Linear(32 → 1)                                              Output layer
        ▼  1 number = logit
 sigmoid → probability (0–1) → Low / Medium / High
```

| Component | Role |
|---|---|
| Linear | Each neuron computes w₁x₁ + … + wₙxₙ + b. These are the learned weights |
| BatchNorm | Keeps values well-scaled: batch statistics while training, saved running averages when predicting |
| ReLU | `max(0, z)`. The non-linearity, which lets the network learn threshold-like rules |
| Dropout 0.2 | During training only, switches off 20% of neurons at random, against overfitting |
| Sigmoid | Logit → probability. Inside `BCEWithLogitsLoss` during training; applied explicitly at prediction |

- **Parameters: 3,457** = 1,152 + 128 (BN) + 2,080 + 64 (BN) + 33.
- `forward` returns `self.net(x).squeeze(-1)`, so the output shape is `[batch]`, and a batch of 1 stays `[1]`.
- `model.train()` versus `model.eval()` switches Dropout and BatchNorm behaviour.

**Real sessions** traced through the current model (from `mlp-diagram.html`):

| Session | Key values | Neurons on (layer 1 / layer 2) | Logit | Probability | Risk |
|---|---|---|---|---|---|
| SID_04290, truly normal | 2 failed logins, IP reputation 0.12 | 28/64, 14/32 | −1.55 | 0.175 | Low |
| SID_05357, truly attack | 4 failed logins, IP reputation 0.20 | 27/64, 15/32 | +20.2 | 1.000 | High |

## 11. Training (notebook §9–§12)

| Setting | Value |
|---|---|
| DataLoader (§9) | Batch 64, shuffled, generator seeded 42 (105 batches per epoch) |
| Metric function (§10) | `compute_metrics(y, prob, 0.5)` → accuracy, precision, recall, F1 (all `zero_division=0`), AUC |
| Early stopping (§11) | `EarlyStopping(patience=10, min_delta=1e-4)` on **validation loss**; deep-copies the best `state_dict` |
| Loop (§12) | Up to 200 epochs, `BCEWithLogitsLoss`, Adam (lr 1e-3, weight decay 1e-4). After each epoch: `evaluate()` in eval mode on all of train and validation, one printed line, and a row appended to `history` → `artifacts/metrics.csv` |
| Device | CUDA if available, otherwise CPU |

**Current result:**
- Prints `Early stopping at epoch 36 (best epoch 26)`, and the weights from epoch 26 are restored (val loss 0.3328).
- At epoch 26, validation accuracy 0.8791, precision 0.9814, recall 0.7438, F1 0.8462, AUC 0.8705; train accuracy 0.8944.
- At epoch 1, val loss 0.4926 and val accuracy 0.7722.

## 12. Results (notebook §14, test set used once)

| Accuracy | Precision | Recall | F1 | AUC-ROC |
|---|---|---|---|---|
| **0.8798** | **0.9776** | **0.7484** | **0.8478** | **0.8804** |

| | Predicted normal | Predicted attack |
|---|---|---|
| **Actually normal (791)** | 780 | 11 false alarms |
| **Actually attack (640)** | 161 missed | 479 |

- **High precision:** 479 of 490 alerts are real attacks.
- **Lower recall:** 161 of 640 attacks are missed. They look like normal sessions on these features.
- **Threshold trade-off:** a lower threshold catches more attacks but raises more false alarms. The PR curve (§14.2) shows it.
- **Caveat:** the data is synthetic, so this is not proven on real traffic. In real traffic attacks are rare (the base-rate problem), so precision would drop.

**Notebook figures (6):** class balance, loss curve, 2×3 metric-per-epoch grid, ROC, PR, confusion matrix.

## 13. Code architecture, file by file

### `intrusion/data.py`
- Constants: `DATASET`, `RAW_FILENAME`, `TARGET = "attack_detected"`, `ID_COLUMN = "session_id"`.
- `raw_path()` returns the kagglehub path (it imports kagglehub only when called).
- `file_sha256(path)`
- `load_raw(path=None)`, which only reads.
- `quality_report(df)` returns a dict with `rows`, `missing`, `duplicates`, `failed_gt_attempts` and `ranges`.
- Cleaning functions (each returns a new DataFrame): `fill_missing_encryption(df)`, `drop_identifier(df)`, `fix_login_counts(df)`, and `clean(df)`, which chains all three.
- `split(df, seed=42)` → train, validation, test. Two stratified `train_test_split` calls (30% held out, then split 50/50).

### `intrusion/preprocess.py`
- `NUMERIC` (6), `CATEGORICAL` (3), `CATEGORIES` (the fixed orders), `ORIGINAL_FEATURES = NUMERIC + CATEGORICAL`.
- `build_preprocessor()`, `feature_names(pre)` (17 names, e.g. `num__failed_logins`, `cat__browser_type_Unknown`) and `original_feature(name)`.
- **`Session`** (pydantic v2) is the input schema used by the API and the dashboard form:

  | Field | Rule |
  |---|---|
  | `network_packet_size` | int 1–65,535 |
  | `login_attempts` | int 0–100 |
  | `failed_logins` | int 0–100 |
  | `session_duration` | float ≥ 0, no inf/NaN |
  | `ip_reputation_score` | float 0–1, no inf/NaN |
  | `unusual_time_access` | int 0 or 1, so HTML form strings coerce |
  | categoricals | `Literal` of the allowed values |

  `failed_logins ≤ login_attempts` is **not** enforced: inconsistent input is accepted and corrected at prediction time.
- `to_frame(sessions)` returns a DataFrame with columns in `ORIGINAL_FEATURES` order.

### `intrusion/model.py`
`MLP(in_features=17)` with `self.net = nn.Sequential(...)` as in section 10.

### `intrusion/inference.py`
- `THRESHOLD = 0.5`.
- `risk_level(p)` returns "Low", "Medium" or "High".
- `save_artifacts(out_dir, model, preprocessor, version)` writes `mlp.pt` (the state_dict), `preprocess.joblib` and `model_meta.json` (`{"version", "in_features": 17, "threshold": 0.5}`).
- `Predictor.load(dir)` loads to CPU in eval mode.
- `predict(session)` applies `fix_login_counts` to the session, transforms it, takes the sigmoid, and returns `{"probability", "risk", "prediction"}` as plain Python types.

### `intrusion/playbook.py`
- `PLAYBOOK` holds the copy text.
- `assess(session, risk)` returns `{"pattern", "actions"}` using the rules in section 6.
- Thresholds are constants: `FAILED_LOGINS_MIN = 3`, `LOGIN_ATTEMPTS_MIN = 7`, `BAD_REPUTATION_ABOVE = 0.6`.

### `model_service/app.py`, the API
- `create_app(load_predictor)` lazily loads the predictor under a `threading.Lock`. A failed load isn't cached, so the next request retries.
- Routes:

  | Route | Returns |
  |---|---|
  | `GET /health` | `{"status": "ok", "model_version": "1.0.0"}` |
  | `POST /predict` (body = a `Session` as JSON) | `{probability, risk, prediction, pattern, actions}` |

- Invalid input → **422**. Model missing → **503** `{"detail": "Model not available: …"}`.
- Module-level `app` uses the `ARTIFACTS_DIR` env var (default `artifacts`).
- Example request body:
  ```json
  {"network_packet_size":500,"protocol_type":"TCP","login_attempts":4,"session_duration":300,
   "encryption_used":"None","ip_reputation_score":0.3,"failed_logins":4,"browser_type":"Chrome","unusual_time_access":0}
  ```
  The response has risk "High" and pattern "Brute force / credential stuffing".

### `webapp/client.py`
- `ModelClient(remote_url, local_loader, timeout=10.0, http=None)`.
- `predict(session)` POSTs to `{remote_url}/predict`. On any HTTP error, timeout, non-2xx response or non-JSON reply it logs a warning and falls back to the local `Predictor`, adding `assess(...)`.
- It adds `"source": "remote"` or `"local"` and sets `last_source`.
- The local load and predict run under a lock. If both remote and local fail, it raises `ModelUnavailable`.

### `webapp/feed.py`
- `ScoredSession`, a dataclass with `id`, `session`, `true_label`, `probability`, `risk`, `source`, `created`, `pattern` and `actions`.
- `SessionFeed(df)` / `.from_csv(path)` replays `artifacts/test_sessions.csv` in order and wraps around at the end. It uses `keep_default_na=False` so "None" stays a string. `.next()` returns `(session_id, Session, label)`.
- `FeedStore` is the in-memory store, with `add`, `get`, `list(risk)` (newest first), `agreement()` (matches against the true label) and `next_manual_id()` → `MAN_00001` and so on.

### `webapp/app.py`, the dashboard
- `create_app(client, feed)`. The module-level `app` reads `MODEL_API_URL` (optional) and `ARTIFACTS_DIR`.
- Routes:

  | Route | Behaviour |
  |---|---|
  | `GET /?risk=` | Full page. The feed table polls `/feed/next` every 3 s with HTMX |
  | `GET /feed/next` | Scores and stores the next session, returns one table row. 204 when paused, when there is no feed, or when the model is unavailable |
  | `POST /feed/pause`, `POST /feed/resume` | Pause and resume the feed |
  | `GET /counters` | Header badge ("Hosted model", "Local fallback" or "Model offline") and the agreement count |
  | `GET /sessions/new`, `POST /sessions` | Manual form. 422 with field errors; 503 when the model is unavailable; 303 redirect to the new session's detail page |
  | `GET /sessions/{id}` | Detail page from the **stored** result: values, probability, risk, pattern, actions, and the footnote "not from the model". 404 for an unknown ID |

- A banner "No trained model found…" appears if `test_sessions.csv` is missing or the model is unavailable.
- Pico.css 2.0.6 and HTMX 2.0.4 load from CDNs (jsdelivr and unpkg), so the page needs internet for styling and polling.

### `tests/` (79 tests)
| File | Covers |
|---|---|
| `conftest.py` | `raw_df` (200 synthetic rows), `raw_csv`, `VALID_SESSION`, `artifacts_dir` (an untrained MLP saved to a temp folder) |
| `test_data.py` | No input mutation, quality report, split, login fix, raw file hash unchanged |
| `test_preprocess.py` | 17 features, schema bounds |
| `test_model.py` | Layer structure |
| `test_inference.py` | Risk levels, load and predict, extreme values, no SHAP files, login fix applied at prediction |
| `test_playbook.py` | Every rule, the exact thresholds (3, 7, 0.6 vs 0.61), priority order |
| `test_model_service.py` | `/health`, `/predict` including the playbook, `/explain` returns 404, 422, 503 then retry |
| `test_client.py` | Remote, fallback cases, logging, loader called only once (also with threads) |
| `test_feed.py` | Feed wrap-around, store, agreement count, thread safety |
| `test_webapp.py` | All routes, pause, risk filter, form 422/303/503, detail page, banner |

## 14. Notebook workflow and section map

- **The source of truth is `notebooks/intrusion_model.py`.** Edit it, then regenerate the `.ipynb` with jupytext and execute it with nbconvert (section 4).
- If you edit the `.ipynb` directly in VS Code, the `.py` goes out of date. Either copy the changes back into the `.py`, or from then on treat the `.ipynb` as the source and stop using jupytext.
- Always **commit the `.ipynb` after a full top-to-bottom run**, so the saved outputs are complete and in order.
- **Currently uncommitted:** `notebooks/intrusion_model.ipynb` has modified execution counters only (cells were run interactively, partly out of order). Re-run it with nbconvert before committing, or discard with `git checkout notebooks/intrusion_model.ipynb`.
- The notebook runs with `notebooks/` as its working folder. It uses `sys.path.insert(0, "..")` and writes artifacts to `../artifacts`.

| § | Content |
|---|---|
| 1 | Setup: imports, seed 42, display options |
| 2 | Raw data, untouched (SHA-256) |
| 3 | Data-quality report |
| 4.1–4.4 | Cleaning steps and the no-mutation proof |
| 5 | Stratified 70/15/15 split |
| 6 | Class balance |
| 7 | Encode and scale |
| 8 | Model architecture (prints the device and the MLP source) |
| 9 | DataLoaders |
| 10 | Metric function |
| 11 | EarlyStopping class |
| 12 | Training loop (per-epoch log, early stop, restore best, save metrics.csv) |
| 13.1–13.2 | Loss curve; metrics per epoch |
| 14 | Test metrics; 14.1 ROC; 14.2 PR; 14.3 confusion matrix; **Analysis heading for you to fill in** |
| 15 | Export: `save_artifacts(...)`, `test_sessions.csv`, and a Predictor sanity check |

## 15. Decision log: what we tried, chose and rejected

1. **The text dataset was rejected first.** The "Text-based Cyber Threat Detection" Kaggle set (`ramoliyafenil/...`) turned out to be threat-intelligence report sentences, not network traffic. Its provided split leaked: 21% of test rows also appear in train. Its labels were noisy. It didn't fit the store scenario.
2. **The intrusion detection dataset was chosen** because its per-session login features fit the "store admin monitors sessions" scenario.
3. **Synthetic ceiling.** The label follows hard rules plus noise, so about 88% accuracy is the most any model can reach. The theory report explains this honestly.
4. **`ML_Project`, the first full build,** had an MLP plus three baselines (LogReg 0.7365, RF 0.8819, HGB 0.8847 accuracy), a long EDA, SHAP explanations (the top features were failed logins, login attempts, IP reputation and browser, about 92% together), Docker-free local services and 70 tests.
5. **`Security_ML_Project`** came from your request for **one model only**. It removed the baselines, the extra EDA (old §6.2–6.7), the comparison chart and the end-of-run integrity check. The setup/raw-data/quality/cleaning/split, encoding, architecture, DataLoaders, metric function, early stopping, training loop, curves, test evaluation and export were all kept.
6. **XAI (SHAP) was removed entirely.** That covers the notebook, the package, the `/explain` endpoint, the SHAP bars in the dashboard and the `shap` dependency. Consequence: the rubric 2.7 bonus now relies on the separate API plus hosting.
7. **The playbook became rule-based.** Patterns and actions are decided from session values, not from SHAP, and the dashboard says so.
8. **Login counts were fixed** (section 8). The fix is applied the same way at training time (`clean`) and at prediction time (`Predictor.predict`).
9. **A web UI is used instead of Tkinter.** The brief allows other technologies, but this must be confirmed with the lecturer.
10. **The raw data is never modified.** This was your explicit requirement: the notebook must show the cleaning on every run.
11. **Hosting was deferred** until local testing was satisfactory.

## 16. Known issues and pitfalls

- **Use the venv's Python.** `python -m jupyter nbconvert` can pick up the system kernel. Use `.venv\Scripts\python -m nbconvert` as in section 4. The venv has no `jupyter.exe`.
- **pandas reads the string "None" as missing.** Any CSV with `encryption_used = "None"` must be read with `keep_default_na=False`, as `SessionFeed.from_csv` does. Otherwise "None" becomes NaN and validation fails.
- **sklearn versions must match.** `preprocess.joblib` is pickled with scikit-learn **1.8.0**. Loading it with a different version, for example in a Docker image for Hugging Face, can warn or break. Pin `scikit-learn==1.8.0`.
- **The dashboard needs `artifacts/`.** Run the notebook first in a new checkout; `artifacts/` is gitignored.
- **CDNs are needed.** The dashboard loads Pico and HTMX from CDNs, so it needs internet. For an offline demo, download `htmx.min.js` into `webapp/static/` and point `base.html` at it.
- **Remote-down delay.** On Windows, a refused connection takes about 2 s before the fallback kicks in. The 3 s feed poll still keeps up.
- **The feed replays the 1,431 test sessions in order.** After about 71 minutes it wraps, and IDs repeat (the detail page then opens the first copy).
- **Re-running changes numbers slightly.** Any change to data or code shifts the early-stopping epoch and the metrics. Update README, `reports/theory.md` and this handout after re-running.
- **Line endings.** Git prints "LF will be replaced by CRLF" warnings. These are harmless.

## 17. Remaining work

### For you (submission)
- [ ] Write the **Analysis** text under notebook §14: what the curves and confusion matrix show, and whether the model is effective. Then re-run the notebook and commit.
- [ ] `reports/theory.md`: **verify every `[verify]` reference** (authors, year, venue, DOI) and rewrite the draft in your own words. Add the figures where it says *(Add the … figures …)*.
- [ ] Ask the lecturer to approve the web UI instead of Tkinter.
- [ ] Create a GitHub repo and push:
  ```powershell
  git remote add origin https://github.com/<you>/<repo>.git
  git push -u origin main
  ```
  Then keep committing regularly (the −10 is for *poor* version control).
- [ ] Check your university's policy on disclosing AI assistance.

### Hugging Face Spaces hosting (bonus 2.7), plan not yet started
Goal: the model API runs publicly on a free Hugging Face **Docker Space**, and the local dashboard calls it through `MODEL_API_URL`. If the Space is asleep or down, the local fallback takes over.

1. **Accounts:** a Hugging Face account and a **write token**. Log in yourself: `.venv\Scripts\python -m pip install huggingface_hub`, then `.venv\Scripts\huggingface-cli login`. Never paste the token into a chat.
2. **Model repo:** add `scripts/publish_artifacts.py`. It takes `--repo <user>/store-session-mlp` and uploads `artifacts/mlp.pt`, `preprocess.joblib` and `model_meta.json` with `huggingface_hub.upload_folder(repo_type="model", allow_patterns=[...])`, leaving out `metrics.csv` and `test_sessions.csv`.
3. **Space files:**
   - `model_service/Dockerfile`:
     - based on `python:3.13-slim`
     - installs CPU torch from `https://download.pytorch.org/whl/cpu`
     - installs `fastapi uvicorn pydantic scikit-learn==1.8.0 numpy pandas joblib huggingface_hub`
     - copies `intrusion/` and `model_service/`
     - at startup, if `ARTIFACTS_DIR` is empty, runs `huggingface_hub.snapshot_download(repo_id=os.environ["HF_MODEL_REPO"], local_dir=ARTIFACTS_DIR)`
     - `CMD uvicorn model_service.app:app --host 0.0.0.0 --port 7860`
   - A Space `README.md` header:
     ```yaml
     ---
     title: Store Session MLP
     sdk: docker
     app_port: 7860
     ---
     ```
4. **Test locally first:** `docker build -f model_service/Dockerfile -t session-mlp .`, then `docker run -p 7860:7860 -e HF_MODEL_REPO=<user>/store-session-mlp session-mlp`. `curl http://localhost:7860/health` should return `{"status":"ok","model_version":"1.0.0"}`.
5. **Deploy:** create a Docker Space, set the variable `HF_MODEL_REPO`, and push the Dockerfile, `intrusion/` and `model_service/` to the Space repo.
6. **Use it:** `$env:MODEL_API_URL = "https://<user>-<space>.hf.space"`, then start the dashboard. The badge shows "Hosted model". A free Space sleeps when idle, and the first call after waking can exceed the 10 s timeout. The dashboard then shows "Local fallback" until the Space is up, which is expected.
7. **Update the docs:** the README rubric row 2.7 and the theory report (hosting).

## 18. Prompt for the next Claude session

Open Claude Code in `C:\Users\meiri\Desktop\Claude_Code_Projects` and paste:

> I'm continuing a university ML project. Please read `handout.md` in this folder first: it is the complete handover (status, environment, file-by-file architecture, decisions, pitfalls and remaining work). The current project is `Security_ML_Project` (single PyTorch MLP for intrusion detection, FastAPI model API, FastAPI+HTMX dashboard, 79 tests). `ML_Project` is an older reference version. The assignment brief is `ML_Project.md`. Rules: never modify the raw dataset; keep seed 42; edit the notebook via `notebooks/intrusion_model.py` and run it with `.venv\Scripts\python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 notebooks/intrusion_model.ipynb`; run `.venv\Scripts\python -m pytest -q` after code changes; commit to git. Next I want to: <your next task, e.g. "deploy the model API to Hugging Face Spaces following section 17">.

## 19. Demo script (about 10 minutes)

1. **Scenario** (30 s): a store admin monitoring login sessions.
2. **Notebook §2–§5** (2 min): untouched raw data and its hash, the quality report (1,966 missing, 730 impossible), the three cleaning steps with before/after, the split table.
3. **§7–§8** (1 min): 17 features; the architecture. Optionally open `mlp-diagram.html`.
4. **§10–§12** (2 min): the metric function, the `EarlyStopping` class, and the per-epoch log ending "Early stopping at epoch 36 (best epoch 26)".
5. **§13–§14** (2 min): loss and metric curves, test metrics, ROC, PR, confusion matrix.
6. **Live app** (3 min), with the commands in section 4:
   - Show the API docs at http://127.0.0.1:8001/docs and run `/predict`.
   - Open the dashboard and watch the feed. Click a High-risk row to show the pattern and actions.
   - Click "Score a session": enter IP reputation 5 first (rejected), then a valid session with 4 failed logins (High, "Brute force").
   - Stop the API. The badge changes to "Local fallback" and scoring continues.

## 20. Likely questions, short answers

- **Why fix the seed?** Reproducibility: the same split, training and numbers on every run.
- **Why scale and one-hot?** Networks need numbers on comparable scales; categories have no natural order.
- **Why fit the preprocessor on train only?** To keep test information out of training (no leakage).
- **What prevents overfitting?** Dropout, weight decay, and early stopping with the best weights restored. The train and validation accuracy gap is small (0.894 vs 0.879).
- **Why one sigmoid output and not softmax?** It's a two-class problem: P(attack), and P(normal) = 1 − P(attack).
- **Why not just accuracy?** Precision and recall show the security trade-off between false alarms and missed attacks.
- **Why ~88% and not higher?** The dataset is synthetic: its label follows a few hard rules plus noise, and the noisy attacks look like normal sessions.
- **What about the 730 impossible rows?** Every failed login is also an attempt, so login attempts was raised to match. This is the smallest consistent fix, applied identically at prediction time. Measured effect: 2 test sessions, within noise.
- **Are the playbook actions from the model?** No. They come from fixed rules on the session's values, and the dashboard says so.
- **Is it production-ready?** No. The data is synthetic, real attacks are rare (the base-rate problem) and behaviour drifts over time. It is a complete, honest pipeline demonstration.
