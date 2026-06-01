import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
from news_module import render_news_module

_render_page_header("MN", "Market News & Analysis", "Real-time professional news aggregation from major financial sources", "News")
render_news_module()
