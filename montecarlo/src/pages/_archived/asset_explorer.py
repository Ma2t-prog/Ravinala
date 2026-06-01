import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
from unified_asset_explorer import render_unified_asset_explorer

_render_page_header("AX", "Universal Asset Explorer", "Unified multi-asset discovery, analytics and comparison", "Valuations")
render_unified_asset_explorer()
