# Theory Report: Store Session Security Monitor

> Draft written from the project's real outputs. Sections 3.1 and 3.2 are complete; 3.3 quotes the real results from the notebook; 3.4 is a draft whose every reference is marked `[verify]` and must be checked against the original source (authors, year, title, venue, pages/DOI) before submission. Edit everything into your own words, and check your university's policy on disclosing AI assistance.

## 3.1 Model scenario

An online store has customers and staff who log in to its website all day. Some of these login sessions are intrusion attempts: credential-stuffing and brute-force attacks that try many passwords, connections from IP addresses with a bad reputation, and scripted bots that pretend to be browsers. A security administrator cannot inspect every session by hand, so the store needs an automatic first filter.

The model in this project is that filter. For each session it receives nine pieces of information: packet size, protocol, number of login attempts, number of failed logins, session duration, whether encryption was used, the reputation score of the source IP address, the browser type, and whether the access happened at an unusual time. It outputs the probability that the session is an intrusion, and the probability is mapped to a risk level: Low (below 0.4), Medium (0.4 to below 0.7) or High (0.7 and above).

This is useful in cybersecurity because it prioritises the administrator's attention: a ranked live feed of scored sessions replaces a raw log, and the High-risk sessions can be handled first. For each flagged session the dashboard also shows a likely threat pattern (brute force, known-bad source, automated bot) and suggested preventive actions such as temporary lockout, multi-factor authentication, IP blocking or bot challenges. These suggestions come from a small set of fixed, hand-written rules on the session's values, not from the model, and the application says so.

The system is a decision-support tool for a human, not an automatic blocker. This matters because of false positives, discussed in 3.3 and 3.4.

## 3.2 Model architecture

### Input

Each session has 6 numeric features and 3 categorical features. A `ColumnTransformer` standardises the numeric features (mean 0, standard deviation 1) and one-hot encodes the categorical ones (protocol: 3 values, encryption: 3 values including "None" for missing, browser: 5 values). This gives 6 + 3 + 3 + 5 = **17 input features**. The preprocessor is fitted on the training split only, so no information from the validation or test data leaks into training.

### Network

The model is a multi-layer perceptron (MLP) implemented in PyTorch:

| Layer | Output size | Purpose |
|---|---|---|
| Linear(17, 64) | 64 | First learned combination of the inputs |
| BatchNorm1d(64) | 64 | Normalises the layer's activations per mini-batch |
| ReLU | 64 | Non-linearity |
| Dropout(0.2) | 64 | Regularisation |
| Linear(64, 32) | 32 | Second hidden layer (compression) |
| BatchNorm1d(32) | 32 | Normalisation |
| ReLU | 32 | Non-linearity |
| Dropout(0.2) | 32 | Regularisation |
| Linear(32, 1) | 1 | One logit for the attack class |

At inference a **sigmoid** converts the logit to a probability between 0 and 1. The model has about 3,300 trainable weights in the linear layers (17x64+64, 64x32+32, 32x1+1 = 1,152 + 2,080 + 33 = 3,265), plus the batch-norm parameters.

### Components and why they are used

- **Linear layers** compute weighted sums of their inputs. Stacking them with non-linearities lets the network learn combinations of features, for example "many failed logins and a poor IP reputation".
- **ReLU** (`max(0, x)`) is the non-linearity. Without it, stacked linear layers would collapse into one linear model. ReLU is cheap, avoids the vanishing gradients of sigmoid/tanh in hidden layers, and can represent threshold-like behaviour (Nair & Hinton, 2010 [verify]).
- **Batch normalisation** standardises each hidden layer's activations over the mini-batch and then rescales them with learned parameters. It stabilises and speeds up training and has a mild regularising effect (Ioffe & Szegedy, 2015 [verify]).
- **Dropout (p = 0.2)** randomly sets 20% of the activations to zero during training only. This stops the units from co-adapting and reduces overfitting (Srivastava et al., 2014 [verify]). At evaluation time dropout is off.
- **Sigmoid output with binary cross-entropy (BCE).** The task is binary (normal vs attack), so the sigmoid gives a probability and BCE is the matching loss: it penalises confident wrong predictions heavily. In code `BCEWithLogitsLoss` combines the sigmoid and the loss in one numerically stable operation.
- **Adam optimiser** (learning rate 1e-3, weight decay 1e-4) adapts the step size per weight using running averages of the gradient and its square (Kingma & Ba, 2015 [verify]). The weight decay is an L2 penalty that keeps the weights small. Mini-batches of 64 sessions are used for up to 200 epochs.
- **Early stopping.** After every epoch the validation loss is computed. If it has not improved by at least 1e-4 for 10 consecutive epochs, training stops and the weights of the best epoch are restored. This is the main protection against overfitting.
- **Decision threshold 0.5** turns the probability into the class label for the metrics.

Seeds are fixed to 42 and the split is a stratified 70 / 15 / 15 (6,675 / 1,431 / 1,431 sessions), so a run can be reproduced.

### Why an MLP is reasonable here

The dataset is small and tabular, with 17 inputs after encoding. An MLP is a natural neural model for such data: it handles mixed numeric and one-hot inputs, is small enough to train in seconds, and outputs a probability that is easy to map to risk levels. The standardisation and batch normalisation matter because the raw features have very different scales (packet size in the hundreds, reputation between 0 and 1). It is worth noting that on typical tabular data, tree-based ensembles often match or beat neural networks (Grinsztajn et al., 2022 [verify]; Shwartz-Ziv & Armon, 2022 [verify]); this project uses an MLP because the assignment focuses on building, training and logging a deep-learning model.

## 3.3 Model result analysis

### Training behaviour

Metrics were logged every epoch for train and validation (loss, accuracy, precision, recall, F1, AUC-ROC) and saved to `artifacts/metrics.csv` (notebook section 12). Early stopping triggered at epoch 64, and the weights of epoch 54 (the lowest validation loss, 0.3274) were restored. The curves behave as expected: in epoch 1 the validation loss is 0.4951 and the validation accuracy 0.7722; by epoch 54 the validation loss is 0.3274 and the validation accuracy 0.8805 (validation precision 0.9835, recall 0.7453, F1 0.8480, AUC 0.8732). After epoch 54 both losses plateau and fluctuate; validation loss does not improve by more than 1e-4 for 10 epochs, which triggers early stopping. The gap between training and validation accuracy at the best epoch is small (0.8965 vs 0.8805), so the model is not badly overfitted. *(Add the loss-curve and metric-curve figures from notebook section 13 here.)*

### Test results

The test set (1,431 sessions) was used once, after training (notebook section 14):

| Metric | MLP (test) |
|---|---|
| Accuracy | 0.8812 |
| Precision | 0.9896 |
| Recall | 0.7422 |
| F1 | 0.8482 |
| AUC-ROC | 0.8794 |

The confusion matrix at threshold 0.5 is: TN = 786, FP = 5, FN = 165, TP = 475. Of the 791 normal sessions, 786 are correctly passed; of the 640 attacks, 475 are caught. *(Add the ROC curve, precision-recall curve and confusion matrix from notebook sections 14.1–14.3.)*

### High precision, lower recall

The model's precision is 0.9896: only 5 of 480 sessions flagged as attacks were normal. When it raises an alert, it is almost always right. The recall is 0.7422: 165 of 640 attacks are missed. The missed attacks are sessions whose values look like ordinary sessions, so the features available give the model little to separate them on. For a security setting the trade-off is important. A missed attack (false negative) is usually costlier than a false alarm, so the threshold could be lowered to gain recall, at the price of more false positives; the precision-recall curve in section 14.2 shows how much precision would be lost for each gain in recall. The three-level risk output (Low / Medium / High) partly addresses this by giving the administrator a graded signal rather than a single yes/no.

### A data-quality finding

In 730 of the 9,537 rows, `failed_logins` is greater than `login_attempts`, which is logically impossible for real sessions (you cannot fail more logins than you attempted; notebook section 3). This is a sign that the data is generated, not captured. The rows were kept and the schema of the API does not enforce the rule, because they are part of the dataset; the issue is reported here as a data-quality limitation.

### Is the model effective?

Within the limits of this dataset, largely yes. It reaches 0.8812 accuracy and 0.8794 AUC with very few false alarms (5 in 791 normal sessions), and training is stable, with early stopping preventing overfitting. Its main weakness is recall: about a quarter of attacks are missed. It is not a proven real-world detector: the data is synthetic, and the accuracy would very likely differ on real traffic. The honest conclusion is that the project demonstrates a complete ML pipeline, from raw data to a served model in a working dashboard, not a production-ready intrusion detection system.

## 3.4 Real-world use of models in cybersecurity

*(Draft. Every citation is marked [verify]: confirm each one exists and says what is attributed to it, and add the missing details (pages, DOI) yourself.)*

### Applications

Machine learning is applied in security for **intrusion detection** (classifying network flows or sessions as benign or malicious), **threat classification** (assigning an alert to a type or family, for example malware families or attack categories), **anomaly detection** (flagging behaviour that deviates from a learned baseline, which can find unseen attacks) and **risk assessment** (turning model scores into priorities for analysts, as the risk levels in this project do). Overviews of these uses are given by Apruzzese et al. (2018) [verify] and Apruzzese et al. (2023) [verify]. Anomaly detection in general is surveyed by Chandola et al. (2009) [verify].

### Strengths

Models can process volumes of events that humans cannot, learn combinations of weak signals, and be retrained as new data arrives. Supervised models perform very well on known attack types in benchmark datasets such as CICIDS2017 (Sharafaldin et al., 2018 [verify]) and UNSW-NB15 (Moustafa & Slay, 2015 [verify]). Anomaly detectors can, in principle, flag novel attacks.

### Limitations and common challenges

- **False positives and the base-rate problem.** Real traffic is overwhelmingly benign, so even a small false-positive rate produces many false alarms per real attack, which can swamp analysts and make the system useless in practice (Axelsson, 2000 [verify]). In this project the precision of 0.99 depends on the data's 45% attack rate; on a real network where attacks are rare it would be much lower.
- **The closed-world and semantic-gap problem.** Sommer and Paxson (2010) [verify] argue that intrusion detection differs from typical ML tasks: the cost of errors is high, the traffic is highly variable, outliers are not necessarily attacks, and evaluation is hard, so results from benchmark data rarely carry over to deployments.
- **Data quality and synthetic data.** Public intrusion datasets are often synthetic or generated in laboratories, and they can contain labelling errors and artefacts. Engelen et al. (2021) [verify] documented errors in the CICIDS2017 dataset, and Arp et al. (2022) [verify] list sampling bias, label inaccuracy and data snooping among the common pitfalls of ML in security. The dataset used here is synthetic and has 730 logically inconsistent rows, so a high score says little about real performance.
- **Concept drift.** Attacker behaviour, software and normal user behaviour change over time, so a model's performance decays and it must be monitored and retrained (Gama et al., 2014 [verify]; Arp et al., 2022 [verify]).
- **Adversarial evasion.** Attackers can deliberately craft inputs to evade a model or poison its training data (Biggio & Roli, 2018 [verify]). A model that depends heavily on a few features such as failed logins or IP reputation is easy to evade: an attacker can spread attempts over many IP addresses and sessions.
- **Evaluation practice.** Arp et al. (2022) [verify] recommend realistic evaluation (time-aware splits, realistic base rates, comparison to simple baselines).

### Relation to this project

The project follows several good practices (stratified split, a held-out test set used once, early stopping, honest error analysis) but also shows the limitations above: synthetic data, missed attacks that look like normal sessions, and a fixed model with no drift monitoring. In a real deployment the model would be one component alongside rules, threat intelligence and human review, trained on real, time-ordered data, evaluated at realistic base rates, and retrained regularly.

## References

All entries are marked `[verify]`: check each against the original source and complete the details before submission.

- Apruzzese, G., Colajanni, M., Ferretti, L., Guido, A., & Marchetti, M. (2018). On the effectiveness of machine and deep learning for cyber security. *10th International Conference on Cyber Conflict (CyCon)*. [verify]
- Apruzzese, G., Laskov, P., Montes de Oca, E., Mallouli, W., Brdalo Rapa, L., Grammatopoulos, A. V., & Di Franco, F. (2023). The role of machine learning in cybersecurity. *Digital Threats: Research and Practice*. [verify]
- Arp, D., Quiring, E., Pendlebury, F., Warnecke, A., Pierazzi, F., Wressnegger, C., Cavallaro, L., & Rieck, K. (2022). Dos and don'ts of machine learning in computer security. *31st USENIX Security Symposium*. [verify]
- Axelsson, S. (2000). The base-rate fallacy and the difficulty of intrusion detection. *ACM Transactions on Information and System Security*. [verify]
- Biggio, B., & Roli, F. (2018). Wild patterns: Ten years after the rise of adversarial machine learning. *Pattern Recognition*. [verify]
- Chandola, V., Banerjee, A., & Kumar, V. (2009). Anomaly detection: A survey. *ACM Computing Surveys*. [verify]
- Engelen, G., Rimmer, V., & Joosen, W. (2021). Troubleshooting an intrusion detection dataset: the CICIDS2017 case study. *IEEE Security and Privacy Workshops*. [verify]
- Gama, J., Zliobaite, I., Bifet, A., Pechenizkiy, M., & Bouchachia, A. (2014). A survey on concept drift adaptation. *ACM Computing Surveys*. [verify]
- Grinsztajn, L., Oyallon, E., & Varoquaux, G. (2022). Why do tree-based models still outperform deep learning on typical tabular data? *NeurIPS Datasets and Benchmarks Track*. [verify]
- Ioffe, S., & Szegedy, C. (2015). Batch normalization: Accelerating deep network training by reducing internal covariate shift. *Proceedings of the 32nd International Conference on Machine Learning (ICML)*. [verify]
- Kingma, D. P., & Ba, J. (2015). Adam: A method for stochastic optimization. *International Conference on Learning Representations (ICLR)*. [verify]
- Moustafa, N., & Slay, J. (2015). UNSW-NB15: a comprehensive data set for network intrusion detection systems. *Military Communications and Information Systems Conference (MilCIS)*. [verify]
- Nair, V., & Hinton, G. E. (2010). Rectified linear units improve restricted Boltzmann machines. *Proceedings of the 27th International Conference on Machine Learning (ICML)*. [verify]
- Sharafaldin, I., Lashkari, A. H., & Ghorbani, A. A. (2018). Toward generating a new intrusion detection dataset and intrusion traffic characterization. *4th International Conference on Information Systems Security and Privacy (ICISSP)*. [verify]
- Shwartz-Ziv, R., & Armon, A. (2022). Tabular data: Deep learning is not all you need. *Information Fusion*. [verify]
- Sommer, R., & Paxson, V. (2010). Outside the closed world: On using machine learning for network intrusion detection. *IEEE Symposium on Security and Privacy*. [verify]
- Srivastava, N., Hinton, G., Krizhevsky, A., Sutskever, I., & Salakhutdinov, R. (2014). Dropout: A simple way to prevent neural networks from overfitting. *Journal of Machine Learning Research*. [verify]
