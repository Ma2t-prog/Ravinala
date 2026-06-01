import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
from equity_research import render_equity_research_tab

_render_page_header("ER", "Equity Research", "Screening, valuation and analyst-style equity workflow", "Research")
render_equity_research_tab()
