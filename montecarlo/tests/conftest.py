from __future__ import annotations

import os
import tempfile
from pathlib import Path
import importlib.util
import importlib.machinery
import sys
import types
import numpy as np


_TMPDIR = Path(__file__).resolve().parents[1] / "tmp" / "pytest-temp"
_TMPDIR.mkdir(parents=True, exist_ok=True)

_OriginalTemporaryDirectory = tempfile.TemporaryDirectory


class _SafeTemporaryDirectory(_OriginalTemporaryDirectory):
    def cleanup(self):
        try:
            super().cleanup()
        except PermissionError:
            pass

os.environ.setdefault("TMP", str(_TMPDIR))
os.environ.setdefault("TEMP", str(_TMPDIR))
tempfile.tempdir = str(_TMPDIR)
tempfile.TemporaryDirectory = _SafeTemporaryDirectory


if not hasattr(np, "trapezoid"):
    np.trapezoid = np.trapz


if importlib.util.find_spec("plotly") is None and "plotly" not in sys.modules:
    class _DummyFigure:
        def __init__(self, *args, **kwargs):
            self.data = list(args)
            self.layout = kwargs.get("layout", {})

        def update_layout(self, *args, **kwargs):
            self.layout = {**getattr(self, "layout", {}), **kwargs}
            return self

        def update_traces(self, *args, **kwargs):
            return self

        def update_xaxes(self, *args, **kwargs):
            return self

        def update_yaxes(self, *args, **kwargs):
            return self

        def add_trace(self, *args, **kwargs):
            return self

        def add_shape(self, *args, **kwargs):
            return self

        def add_annotation(self, *args, **kwargs):
            return self

        def add_hline(self, *args, **kwargs):
            return self

        def add_vline(self, *args, **kwargs):
            return self

        def to_dict(self):
            return {"data": self.data, "layout": self.layout}

    class _DummyTrace:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class _DummyTemplate:
        def __init__(self, layout=None, **kwargs):
            self.layout = layout or {}
            self.kwargs = kwargs

    plotly_stub = types.ModuleType("plotly")
    plotly_stub.__spec__ = importlib.machinery.ModuleSpec("plotly", loader=None, is_package=True)
    plotly_stub.__path__ = []
    plotly_stub.__RAVINALA_PLOTLY_STUB__ = True

    graph_objects_stub = types.ModuleType("plotly.graph_objects")
    graph_objects_stub.__spec__ = importlib.machinery.ModuleSpec("plotly.graph_objects", loader=None)
    graph_objects_stub.Figure = _DummyFigure
    graph_objects_stub.Layout = dict
    graph_objects_stub.Scatter = _DummyTrace
    graph_objects_stub.Bar = _DummyTrace
    graph_objects_stub.Heatmap = _DummyTrace
    graph_objects_stub.Histogram = _DummyTrace
    graph_objects_stub.Waterfall = _DummyTrace
    graph_objects_stub.Sankey = _DummyTrace
    graph_objects_stub.Indicator = _DummyTrace
    graph_objects_stub.Pie = _DummyTrace
    graph_objects_stub.layout = types.SimpleNamespace(Template=_DummyTemplate)

    express_stub = types.ModuleType("plotly.express")
    express_stub.__spec__ = importlib.machinery.ModuleSpec("plotly.express", loader=None)

    def _express_factory(*args, **kwargs):
        return _DummyFigure(*args, **kwargs)

    express_stub.line = _express_factory
    express_stub.scatter = _express_factory
    express_stub.bar = _express_factory
    express_stub.area = _express_factory
    express_stub.imshow = _express_factory
    express_stub.pie = _express_factory
    express_stub.histogram = _express_factory

    subplots_stub = types.ModuleType("plotly.subplots")
    subplots_stub.__spec__ = importlib.machinery.ModuleSpec("plotly.subplots", loader=None)
    subplots_stub.make_subplots = lambda *args, **kwargs: _DummyFigure()

    class _Templates(dict):
        def __init__(self):
            super().__init__()
            self.default = None

    io_stub = types.ModuleType("plotly.io")
    io_stub.__spec__ = importlib.machinery.ModuleSpec("plotly.io", loader=None)
    io_stub.templates = _Templates()

    plotly_stub.graph_objects = graph_objects_stub
    plotly_stub.express = express_stub
    plotly_stub.subplots = subplots_stub
    plotly_stub.io = io_stub

    sys.modules["plotly"] = plotly_stub
    sys.modules["plotly.graph_objects"] = graph_objects_stub
    sys.modules["plotly.express"] = express_stub
    sys.modules["plotly.subplots"] = subplots_stub
    sys.modules["plotly.io"] = io_stub
