---
title: Store Session MLP API
emoji: 🛡️
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# Store Session MLP API

A university ML-in-security project. A PyTorch multi-layer perceptron scores an online store's login session for intrusion risk.

- `GET /health`: status, model version, and whether API-key protection is on.
- `POST /predict`: send one session as JSON; returns the attack probability, risk level (Low / Medium / High), prediction, and a rule-based threat pattern with preventive actions.
- `GET /docs`: interactive documentation. Click **Authorize** and enter the API key to try `/predict`.

`/predict` requires the header `X-API-Key`. The key is stored as a Space secret named `MODEL_API_KEY`.

Example request body:

```json
{"network_packet_size": 500, "protocol_type": "TCP", "login_attempts": 4, "session_duration": 300,
 "encryption_used": "None", "ip_reputation_score": 0.3, "failed_logins": 4, "browser_type": "Chrome",
 "unusual_time_access": 0}
```

Trained on the synthetic Kaggle dataset `dnkumars/cybersecurity-intrusion-detection-dataset`; not a production intrusion detection system.
