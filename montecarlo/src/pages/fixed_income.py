import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
from fixed_income_research import render_fixed_income_research_tab

_render_page_header("FI", "Fixed Income Research", "Curve, spread and bond analytics", "Rates")
render_fixed_income_research_tab()
