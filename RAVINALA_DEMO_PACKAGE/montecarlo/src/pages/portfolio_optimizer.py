import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
from portfolio import render_portfolio_optimizer_tab

_render_page_header("PO", "Portfolio Optimizer", "Mean-variance optimization, efficient frontier and risk budgeting", "Portfolio")
render_portfolio_optimizer_tab()
