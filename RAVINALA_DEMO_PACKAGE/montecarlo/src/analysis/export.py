"""
export.py — Export charts as PNG/PDF and generate analysis reports.
"""
from __future__ import annotations

import io
import tempfile
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


class ReportExporter:
    """Export Plotly charts and DataFrames to various formats."""

    @staticmethod
    def fig_to_bytes(fig: go.Figure, fmt: str = "png",
                      width: int = 1400, height: int = 700) -> bytes:
        """Convert a Plotly figure to image bytes.

        Args:
            fig: Plotly Figure.
            fmt: 'png' | 'svg' | 'pdf' | 'jpeg'.
            width: Image width in pixels.
            height: Image height in pixels.

        Returns:
            Image bytes.
        """
        return fig.to_image(format=fmt, width=width, height=height)

    @staticmethod
    def download_button_chart(fig: go.Figure, filename: str = "chart.png",
                               label: str = "Download Chart (PNG)") -> None:
        """Render a Streamlit download button for a chart.

        Args:
            fig: Plotly Figure.
            filename: Downloaded file name.
            label: Button label.
        """
        try:
            img_bytes = ReportExporter.fig_to_bytes(fig, "png")
            st.download_button(
                label=label,
                data=img_bytes,
                file_name=filename,
                mime="image/png",
            )
        except Exception as e:
            st.warning(f"PNG export requires `kaleido`. Error: {e}")

    @staticmethod
    def download_button_csv(df: pd.DataFrame, filename: str = "data.csv",
                             label: str = "Download CSV") -> None:
        """Render a Streamlit download button for a DataFrame as CSV."""
        csv = df.to_csv(index=True).encode("utf-8")
        st.download_button(
            label=label,
            data=csv,
            file_name=filename,
            mime="text/csv",
        )

    @staticmethod
    def download_button_excel(df: pd.DataFrame, filename: str = "data.xlsx",
                               label: str = "Download Excel") -> None:
        """Render a Streamlit download button for a DataFrame as Excel."""
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=True, sheet_name="Data")
        buffer.seek(0)
        st.download_button(
            label=label,
            data=buffer,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @staticmethod
    def generate_pdf_report(
        symbol: str,
        snapshot: dict,
        technicals: dict,
        fundamentals: dict,
        charts: Optional[list[go.Figure]] = None,
    ) -> Optional[bytes]:
        """Generate a simple PDF analysis report.

        Args:
            symbol: Ticker symbol.
            snapshot: Price snapshot dict.
            technicals: Dict of technical indicator values.
            fundamentals: Dict of fundamental data.
            charts: Optional list of Plotly Figures to embed.

        Returns:
            PDF bytes or None if reportlab is unavailable.
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
            )

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4,
                                     rightMargin=2*cm, leftMargin=2*cm,
                                     topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            story = []

            # Title
            story.append(Paragraph(
                f"<b>Financial Analysis Report — {symbol}</b>",
                styles["Title"]
            ))
            story.append(Spacer(1, 0.5*cm))

            # Price summary
            price = snapshot.get("price", "N/A")
            chg = snapshot.get("change_pct", 0)
            story.append(Paragraph(
                f"Price: <b>${price:.2f}</b>  |  Change: <b>{chg:+.2f}%</b>  |  "
                f"Name: {snapshot.get('name', symbol)}",
                styles["Normal"]
            ))
            story.append(Spacer(1, 0.3*cm))

            # Fundamentals table
            if fundamentals:
                fund_data = [["Metric", "Value"]]
                for k, v in fundamentals.items():
                    if v is not None:
                        fund_data.append([str(k).replace("_", " ").title(), str(v)])

                t = Table(fund_data, colWidths=[7*cm, 7*cm])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                    ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                    ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                    ("FONTSIZE",   (0, 0), (-1, -1), 9),
                ]))
                story.append(t)
                story.append(Spacer(1, 0.5*cm))

            # Charts as images
            if charts:
                for chart_fig in charts:
                    try:
                        img_bytes = ReportExporter.fig_to_bytes(chart_fig, "png", 900, 450)
                        from reportlab.platypus import Image as RLImage
                        img = RLImage(io.BytesIO(img_bytes), width=17*cm, height=8.5*cm)
                        story.append(img)
                        story.append(Spacer(1, 0.5*cm))
                    except Exception:
                        pass

            doc.build(story)
            buffer.seek(0)
            return buffer.read()

        except ImportError:
            return None
        except Exception:
            return None
