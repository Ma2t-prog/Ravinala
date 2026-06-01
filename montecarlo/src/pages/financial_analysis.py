import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
from analysis.suite_ui import render_financial_analysis_suite

_render_page_header(
    "FA",
    "Financial Analysis Suite",
    "Pro charting · Screener · Fundamentals · Options · Sector Rotation · Seasonality · Backtest",
    "Analysis",
)
render_financial_analysis_suite()
