import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st

from etf_explorer import render_etf_explorer
render_etf_explorer()
