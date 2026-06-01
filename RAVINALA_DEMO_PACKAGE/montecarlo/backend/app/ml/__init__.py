"""
ml — Machine Learning module.

Étape 8 — ML Minimum Sérieux
─────────────────────────────
Credible ML core: RF, XGB, LGB.
LSTM and GARCH explicitly disabled until proper pipeline exists.

Design principles (construction22032026.docx):
  - Every model saved, every run tracked, every prediction logged
  - Baselines mandatory (naive + linear)
  - Temporal validation only — no random split ever
  - Walk-forward when applicable
  - accuracy alone is forbidden — must include directional acc, MAE, IC
"""
