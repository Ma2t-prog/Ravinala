# backward-compat shim — imports from market.macro_data
from market.macro_data import *  # noqa: F401,F403
from market.macro_data import (  # noqa: F401
    _build_calendar_html,
    _build_commodities_html,
    _build_crypto_html,
    _build_fx_html,
    _build_indices_html,
    _build_news_html,
    _build_vol_html,
    _fmt,
    _pct_span,
    _spark,
)
