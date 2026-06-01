import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
from structuring_suite import render_structuring_suite

_render_page_header("SS", "Rates Structuring Suite", "Bulge-bracket style design, pricing, risk, hedging and compliance", "Structuring")
render_structuring_suite()
