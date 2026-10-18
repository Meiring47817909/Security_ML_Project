# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Store Session Security Monitor: intrusion detection with an MLP
#
# **Scenario.** An online store's security admin monitors login sessions on the store, from customers and staff.
# Each session is scored by the model for intrusion risk (Low / Medium / High). The admin dashboard then suggests the likely
# threat pattern (brute force, known-bad source, automated bot) and preventive actions, using fixed rules on the session's values.
#
# **Dataset.** Kaggle `dnkumars/cybersecurity-intrusion-detection-dataset`: 9,537 sessions, 9 features, binary target `attack_detected`.
#
# **Part 1** loads the raw file untouched and prepares it step by step (every step is visible, with before/after output), then splits and encodes it.
# The raw file is never modified, so every run repeats the whole preparation from the raw rows.
# **Part 2** builds and trains one model, a PyTorch multi-layer perceptron (MLP), evaluates it once on the test set and exports it for the web services.

# %% [markdown]
# ## 1. Setup
# Fixed seed 42 everywhere so the run is reproducible. The notebook runs from `notebooks/`, so the project root is added to the path
# to import the shared `intrusion` package (the same code the services use).

# %%
import sys
import random
import warnings

sys.path.insert(0, "..")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

from intrusion.data import (
    raw_path, file_sha256, load_raw, quality_report,
    fill_missing_encryption, drop_identifier, clean, split, TARGET,
)
from intrusion.preprocess import build_preprocessor, feature_names, NUMERIC, ORIGINAL_FEATURES

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 30)
# %matplotlib inline
print("setup done, seed =", SEED)

# %% [markdown]
# ## 2. Raw data, untouched
# The raw CSV stays in the kagglehub cache and is only ever *read*. Its SHA-256 hash (a fingerprint of the file) is printed so any change
# to the source data would be visible. Everything below works on in-memory copies.

# %%
path = raw_path()
raw_hash = file_sha256(path)
raw = load_raw(path)
print("path   :", path)
print("sha256 :", raw_hash)
print("shape  :", raw.shape)
print()
print(raw.dtypes)
raw.head()

# %% [markdown]
# ## 3. Data-quality report
# Before changing anything we measure what is wrong with the data: missing values (a model cannot ingest NaN),
# duplicate rows (would leak between splits), numeric ranges (to spot impossible values) and logical inconsistencies.
# Rows where `failed_logins > login_attempts` are logically odd (you cannot fail more logins than you attempt).
# We *report* them but keep them, because the live API must accept the same kind of rows the data contains.

# %%
report = quality_report(raw)
print("rows       :", report["rows"])
print("duplicates :", report["duplicates"])
print("rows with failed_logins > login_attempts:", report["failed_gt_attempts"])
print("\nMissing values per column:")
display(pd.Series(report["missing"], name="missing").to_frame())
print("Numeric ranges:")
display(pd.DataFrame(report["ranges"], index=["min", "max"]).T)
print("Five of the rows where failed_logins > login_attempts:")
display(raw[raw["failed_logins"] > raw["login_attempts"]].head(5))

# %% [markdown]
# **Findings.** Only `encryption_used` has missing values; in this dataset a missing value means no encryption was used, so it is a real category
# rather than an unknown. There are no duplicates and the numeric ranges are plausible. The `failed_logins > login_attempts` rows are
# a data-quality quirk of this synthetic dataset, noted and kept.

# %% [markdown]
# ## 4. Cleaning, one step per cell
# ### 4.1 Missing `encryption_used` becomes the category `"None"`
# A missing value here means "no encryption". Encoding it as its own category keeps all 1,966 rows and lets the model use the information.

# %%
before = raw["encryption_used"].value_counts(dropna=False)
step1 = fill_missing_encryption(raw)
after = step1["encryption_used"].value_counts(dropna=False)
display(pd.concat([before.rename("before"), after.rename("after")], axis=1).fillna(0).astype(int))
print("NaN before:", raw["encryption_used"].isna().sum(), "| NaN after:", step1["encryption_used"].isna().sum())

# %% [markdown]
# ### 4.2 Drop the identifier `session_id`
# `session_id` is a unique label with no predictive meaning. Left in, a model could memorise it, and it would be one-hot-encoded into thousands of useless columns.

# %%
step2 = drop_identifier(step1)
print("columns before:", list(step1.columns))
print("columns after :", list(step2.columns))
print("shape before -> after:", step1.shape, "->", step2.shape)

# %% [markdown]
# ### 4.3 The full pipeline, and proof that the raw frame is untouched
# `clean` chains both steps and returns a **new** DataFrame. The assertions show the original `raw` frame still has its NaNs and its `session_id`.

# %%
df = clean(raw)
assert raw["encryption_used"].isna().sum() > 0, "raw lost its NaNs"
assert "session_id" in raw.columns, "raw lost session_id"
assert df["encryption_used"].isna().sum() == 0 and "session_id" not in df.columns
print("raw :", raw.shape, "| NaNs in encryption_used:", raw["encryption_used"].isna().sum(), "| has session_id:", "session_id" in raw.columns)
print("df  :", df.shape, "| NaNs in encryption_used:", df["encryption_used"].isna().sum(), "| has session_id:", "session_id" in df.columns)
print("Assertions passed: cleaning created a new frame and left the raw one unchanged.")
df.head()

# %% [markdown]
# ## 5. Split (stratified 70 / 15 / 15)
# The split comes *before* any fitting, so the validation and test sets stay unseen.
# It is stratified on the target so every split keeps the same attack rate. Train is used to fit, validation to stop training, test only for the final evaluation.

# %%
train_df, val_df, test_df = split(df)
pd.DataFrame(
    {
        "rows": [len(train_df), len(val_df), len(test_df)],
        "share": [len(d) / len(df) for d in (train_df, val_df, test_df)],
        "attack_rate": [d[TARGET].mean() for d in (train_df, val_df, test_df)],
    },
    index=["train", "val", "test"],
).round(4)

# %% [markdown]
# ## 6. Class balance
# Checked on the training split only, so nothing about the validation or test data influences our choices.

# %%
counts = train_df[TARGET].value_counts().sort_index()
fig, ax = plt.subplots(figsize=(4.5, 3.5))
ax.bar(["normal (0)", "attack (1)"], counts.values, color=["#4c72b0", "#c44e52"])
for i, v in enumerate(counts.values):
    ax.text(i, v, f"{v}\n({v / counts.sum():.1%})", ha="center", va="bottom")
ax.set_ylabel("sessions")
ax.set_title("Class balance (train)")
ax.set_ylim(0, counts.max() * 1.2)
plt.show()

# %% [markdown]
# The classes are close to balanced (about 45% attacks), so accuracy is a fair headline metric and no resampling is needed. We still report precision, recall, F1 and AUC.

# %% [markdown]
# ## 7. Encode and scale
# A neural network needs numeric inputs on comparable scales. A `ColumnTransformer` standardises the 6 numeric columns (mean 0, std 1)
# and one-hot encodes the 3 categoricals (protocol, encryption, browser) with a fixed category order, giving 17 features.
# It is **fitted on the training split only** and then applied to validation and test, so no test statistics leak into training.

# %%
pre = build_preprocessor()
X_train = pre.fit_transform(train_df[ORIGINAL_FEATURES]).astype(np.float32)
X_val = pre.transform(val_df[ORIGINAL_FEATURES]).astype(np.float32)
X_test = pre.transform(test_df[ORIGINAL_FEATURES]).astype(np.float32)
y_train = train_df[TARGET].to_numpy(dtype=np.float32)
y_val = val_df[TARGET].to_numpy(dtype=np.float32)
y_test = test_df[TARGET].to_numpy(dtype=np.float32)
FEATS = feature_names(pre)

print(f"{len(FEATS)} features:", FEATS)
print("X_train", X_train.shape, "X_val", X_val.shape, "X_test", X_test.shape)
print("y_train", y_train.shape, "y_val", y_val.shape, "y_test", y_test.shape)
print("\nScaled numeric columns in train (mean should be ~0, std ~1):")
display(pd.DataFrame(X_train[:, :len(NUMERIC)], columns=FEATS[:len(NUMERIC)]).agg(["mean", "std"]).round(4))
print("First 3 encoded training rows:")
display(pd.DataFrame(X_train[:3], columns=FEATS).round(3))

# %% [markdown]
# # Part 2: the PyTorch MLP
#
# Part 2 trains the model, a multi-layer perceptron, with a hand-written training loop. Every epoch logs train and validation
# metrics, early stopping watches the validation loss, and the best weights are restored. The model is then evaluated once on the test set
# and exported for the web services.
#
# ## 8. Model architecture
# The architecture is printed in full below; the metric function (section 10), early stopping (section 11) and the hand-written training loop (section 12) are
# written out in this notebook. The `MLP` class is imported from `intrusion/model.py` so the notebook and both services run identical code.
# Two hidden layers (64 and 32 units) are plenty for 17 inputs; BatchNorm stabilises training and Dropout(0.2) limits overfitting.
# The last layer outputs one **logit**; the sigmoid is applied only at inference, because `BCEWithLogitsLoss` is numerically more stable on logits.

# %%
import copy
import inspect
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import roc_curve, precision_recall_curve, average_precision_score, confusion_matrix, ConfusionMatrixDisplay

from intrusion.model import MLP
from intrusion.inference import save_artifacts, Predictor
from intrusion.preprocess import Session

torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
ARTIFACTS = Path("../artifacts")
ARTIFACTS.mkdir(parents=True, exist_ok=True)
print("device:", device)
print(inspect.getsource(MLP))

# %% [markdown]
# ## 9. DataLoaders
# The encoded arrays become tensors. The training loader feeds the model shuffled mini-batches of 64 sessions every epoch, using its own generator
# seeded 42 so the batch order is reproducible. Validation and test are evaluated in one pass each, so they need no loader.

# %%
train_ds = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
train_loader = DataLoader(train_ds, batch_size=64, shuffle=True, generator=torch.Generator().manual_seed(SEED))
xb, yb = next(iter(train_loader))
print("train batches per epoch:", len(train_loader))
print("one batch: X", tuple(xb.shape), xb.dtype, "| y", tuple(yb.shape), yb.dtype)

# %% [markdown]
# ## 10. Metric function
# One function computes every metric we log (accuracy, precision, recall, F1, AUC), so train, validation and test are measured identically.
# Probabilities are thresholded at 0.5 for the class metrics; AUC uses the raw probabilities. `zero_division=0` avoids warnings in the first epochs when
# the model may predict only one class.

# %%
def compute_metrics(y_true, prob, threshold=0.5) -> dict:
    pred = (np.asarray(prob) >= threshold).astype(int)
    return {
        "accuracy": accuracy_score(y_true, pred),
        "precision": precision_score(y_true, pred, zero_division=0),
        "recall": recall_score(y_true, pred, zero_division=0),
        "f1": f1_score(y_true, pred, zero_division=0),
        "auc": roc_auc_score(y_true, prob),
    }

print(compute_metrics([0, 1, 1, 0], [0.2, 0.9, 0.4, 0.1]))

# %% [markdown]
# ## 11. Early stopping
# Training for a fixed number of epochs risks overfitting. `EarlyStopping` watches the validation loss: an epoch counts as an improvement only if the loss drops by more
# than `min_delta`. It keeps a deep copy of the best weights, and after `patience` epochs without improvement it signals the loop to stop.

# %%
class EarlyStopping:
    def __init__(self, patience=10, min_delta=1e-4):
        self.patience = patience
        self.min_delta = min_delta
        self.best_loss = float("inf")
        self.best_epoch = 0
        self.best_state = None
        self.counter = 0
        self.epoch = 0

    def step(self, val_loss, model) -> bool:
        self.epoch += 1
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.best_epoch = self.epoch
            self.best_state = copy.deepcopy(model.state_dict())
            self.counter = 0
        else:
            self.counter += 1
        return self.counter >= self.patience

# %% [markdown]
# ## 12. Training loop
# Each epoch: one training pass over shuffled mini-batches (dropout and batch-norm in training mode), then the model is switched to eval mode
# and the loss and all metrics are computed on the full train and validation sets. Each epoch prints one row and is stored in `history`.
# Loss `BCEWithLogitsLoss`, Adam (lr 1e-3, weight decay 1e-4), at most 200 epochs, early stopping with patience 10 on validation loss.

# %%
model = MLP(in_features=X_train.shape[1]).to(device)
print(model)
criterion = nn.BCEWithLogitsLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
es = EarlyStopping(patience=10, min_delta=1e-4)
MAX_EPOCHS = 200


def evaluate(model, X, y):
    model.eval()
    with torch.no_grad():
        logits = model(torch.from_numpy(X).to(device))
        loss = criterion(logits, torch.from_numpy(y).to(device)).item()
        prob = torch.sigmoid(logits).cpu().numpy()
    return loss, compute_metrics(y, prob)


history = []
for epoch in range(1, MAX_EPOCHS + 1):
    model.train()
    for xb, yb in train_loader:
        xb, yb = xb.to(device), yb.to(device)
        optimizer.zero_grad()
        loss = criterion(model(xb), yb)
        loss.backward()
        optimizer.step()

    tr_loss, tr = evaluate(model, X_train, y_train)
    va_loss, va = evaluate(model, X_val, y_val)
    row = {"epoch": epoch, "train_loss": tr_loss, "val_loss": va_loss}
    row.update({f"train_{k}": v for k, v in tr.items()})
    row.update({f"val_{k}": v for k, v in va.items()})
    history.append(row)
    print(f"epoch {epoch:3d} | loss {tr_loss:.4f}/{va_loss:.4f} | acc {tr['accuracy']:.4f}/{va['accuracy']:.4f} | "
          f"prec {tr['precision']:.4f}/{va['precision']:.4f} | rec {tr['recall']:.4f}/{va['recall']:.4f} | "
          f"f1 {tr['f1']:.4f}/{va['f1']:.4f} | auc {tr['auc']:.4f}/{va['auc']:.4f}  (train/val)")

    if es.step(va_loss, model):
        print(f"Early stopping at epoch {epoch} (best epoch {es.best_epoch})")
        break

model.load_state_dict(es.best_state)
model.eval()
hist = pd.DataFrame(history)
hist.to_csv(ARTIFACTS / "metrics.csv", index=False)
print(f"Restored best weights from epoch {es.best_epoch} (val loss {es.best_loss:.4f}); {len(hist)} epochs saved to {ARTIFACTS / 'metrics.csv'}")

# %% [markdown]
# ## 13. Training curves
# ### 13.1 Loss
# The dashed line marks the best epoch, whose weights were restored. After it, the validation loss stops improving while training continues for `patience` epochs.

# %%
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(hist["epoch"], hist["train_loss"], label="train")
ax.plot(hist["epoch"], hist["val_loss"], label="validation")
ax.axvline(es.best_epoch, color="k", ls="--", lw=1, label=f"best epoch ({es.best_epoch})")
ax.set_xlabel("epoch")
ax.set_ylabel("BCE loss")
ax.set_title("MLP loss per epoch")
ax.legend()
fig.tight_layout()
plt.show()

# %% [markdown]
# ### 13.2 Metrics per epoch
# Accuracy, precision, recall, F1 and AUC for train and validation, with the same best-epoch marker. The sixth panel shows the generalisation gap
# (validation minus train accuracy).

# %%
fig, axes = plt.subplots(2, 3, figsize=(15, 8))
for ax, m in zip(axes.ravel(), ["accuracy", "precision", "recall", "f1", "auc"]):
    ax.plot(hist["epoch"], hist[f"train_{m}"], label="train")
    ax.plot(hist["epoch"], hist[f"val_{m}"], label="validation")
    ax.axvline(es.best_epoch, color="k", ls="--", lw=1)
    ax.set_title(m)
    ax.set_xlabel("epoch")
    ax.legend()
ax = axes.ravel()[5]
ax.plot(hist["epoch"], hist["val_accuracy"] - hist["train_accuracy"], color="#8172b2")
ax.axhline(0, color="grey", lw=0.8)
ax.axvline(es.best_epoch, color="k", ls="--", lw=1, label=f"best epoch ({es.best_epoch})")
ax.set_title("val - train accuracy")
ax.set_xlabel("epoch")
ax.legend()
fig.suptitle("MLP metrics per epoch (dashed line = best epoch)")
fig.tight_layout()
plt.show()

# %% [markdown]
# ## 14. Final test evaluation (run once)
# The test set has not been touched until now. The MLP (best weights) is scored once.

# %%
with torch.no_grad():
    mlp_prob = torch.sigmoid(model(torch.from_numpy(X_test).to(device))).cpu().numpy()
mlp_pred = (mlp_prob >= 0.5).astype(int)
pd.DataFrame({"MLP (test)": compute_metrics(y_test, mlp_prob)}).T.round(4)

# %% [markdown]
# ### 14.1 ROC curve
# The ROC curve shows the true-positive rate against the false-positive rate across all thresholds; the area under it (AUC) is threshold-free.

# %%
fpr, tpr, _ = roc_curve(y_test, mlp_prob)
fig, ax = plt.subplots(figsize=(6.5, 6))
ax.plot(fpr, tpr, lw=2, label=f"MLP (AUC = {roc_auc_score(y_test, mlp_prob):.3f})")
ax.plot([0, 1], [0, 1], color="grey", ls=":", lw=1, label="random guess")
ax.set_xlabel("false-positive rate")
ax.set_ylabel("true-positive rate")
ax.set_title("ROC curve (test)")
ax.legend(loc="lower right")
fig.tight_layout()
plt.show()

# %% [markdown]
# ### 14.2 Precision-recall curve
# The PR curve focuses on the attack class: how much precision we keep as we try to catch more attacks. AP is the average precision (area under the curve).

# %%
prec, rec, _ = precision_recall_curve(y_test, mlp_prob)
fig, ax = plt.subplots(figsize=(6.5, 6))
ax.plot(rec, prec, lw=2, label=f"MLP (AP = {average_precision_score(y_test, mlp_prob):.3f})")
ax.axhline(y_test.mean(), color="grey", ls=":", lw=1, label=f"attack rate ({y_test.mean():.2f})")
ax.set_xlabel("recall")
ax.set_ylabel("precision")
ax.set_title("Precision-recall curve (test)")
ax.legend(loc="lower left")
fig.tight_layout()
plt.show()

# %% [markdown]
# ### 14.3 Confusion matrix (threshold 0.5)

# %%
cm = confusion_matrix(y_test, mlp_pred)
fig, ax = plt.subplots(figsize=(5, 4.5))
ConfusionMatrixDisplay(cm, display_labels=["normal", "attack"]).plot(ax=ax, cmap="Blues", values_format="d", colorbar=False)
ax.set_title("MLP confusion matrix (test)")
fig.tight_layout()
plt.show()
tn, fp, fn, tp = cm.ravel()
print(f"TN={tn}  FP={fp}  FN={fn}  TP={tp}")

# %% [markdown]
# ### Analysis
#
# _(student analysis: what the curves and the confusion matrix show, and whether the model is effective)_

# %% [markdown]
# ## 15. Export for the services
# `save_artifacts` writes the trained weights (CPU copy), the fitted preprocessor and a small metadata file (version 1.0.0).
# The test sessions are also saved in raw form (cleaned values, with `session_id` and the true label) so the web app can replay them as a live feed.
# Finally the artifacts are loaded back with `Predictor`, exactly as the service does, and one session is scored as a sanity check.

# %%
model_cpu = copy.deepcopy(model).to("cpu").eval()  # a copy, so `model` stays on its device and section 14 can be re-run
save_artifacts(ARTIFACTS, model_cpu, pre, "1.0.0")
test_sessions = fill_missing_encryption(raw.loc[test_df.index])
test_sessions.to_csv(ARTIFACTS / "test_sessions.csv", index=False)
print("test_sessions.csv:", test_sessions.shape)
for f in sorted(ARTIFACTS.iterdir()):
    print(f"  {f.name:24s} {f.stat().st_size:>10,d} bytes")

predictor = Predictor.load(ARTIFACTS)
first = test_sessions[ORIGINAL_FEATURES].to_dict(orient="records")[0]
result = predictor.predict(Session(**first))
print("\nfirst test session:", first)
print("Predictor.predict  :", result)
print("notebook MLP prob  :", round(float(mlp_prob[0]), 6), "| true label:", int(test_sessions[TARGET].iloc[0]))
assert abs(result["probability"] - float(mlp_prob[0])) < 1e-5
