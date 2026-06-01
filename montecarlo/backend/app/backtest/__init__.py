"""
backtest — Traceable backtesting module.

Étape 9 — Backtesting traçable
────────────────────────────────
Every run persisted with params, trades, metrics, cost assumptions,
and explicit limitations matrix.

Design principles (construction22032026.docx):
  - Persistence of runs AND trades
  - Serialised parameters + seed
  - Explicit benchmark
  - Cost hypotheses logged
  - Anti-lookahead validation visible
  - Clear labelling of limitations
  - "exploration only" policy until biases corrected
  - MANDATORY baselines: buy & hold + 1/N equal-weight
"""
