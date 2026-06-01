"""
pdf_engine.py — Core PDF generation engine for Ravinala reporting.

Provides color constants, typography styles, reusable UI components,
and the main document builder for all PDF reports.
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, cm, inch
from reportlab.lib.colors import HexColor, Color, white, black
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime
from pathlib import Path
import math


# ═══════════════════════════════════════════════════════════════
# COLOR PALETTE
# ═══════════════════════════════════════════════════════════════

class RavinalaColors:
    """Ravinala brand color constants as ReportLab HexColor objects."""

    # Brand greens
    EMERALD       = HexColor('#059669')
    EMERALD_LIGHT = HexColor('#34D399')
    EMERALD_DARK  = HexColor('#047857')

    # Neutrals
    NAVY   = HexColor('#0F172A')
    DARK   = HexColor('#1E293B')
    MEDIUM = HexColor('#475569')
    LIGHT  = HexColor('#94A3B8')
    PALE   = HexColor('#F1F5F9')
    WHITE  = HexColor('#FFFFFF')

    # Accents
    GOLD   = HexColor('#D97706')
    BLUE   = HexColor('#2563EB')
    RED    = HexColor('#DC2626')
    GREEN  = HexColor('#16A34A')
    ORANGE = HexColor('#EA580C')

    # Backgrounds
    BG_HEADER       = HexColor('#0F172A')
    BG_TABLE_HEADER = HexColor('#1E293B')
    BG_TABLE_ALT    = HexColor('#F8FAFC')
    BG_HIGHLIGHT    = HexColor('#ECFDF5')
    BG_WARNING      = HexColor('#FEF3C7')


# ═══════════════════════════════════════════════════════════════
# FONT CONSTANTS
# ═══════════════════════════════════════════════════════════════

class RavinalaFonts:
    """ReportLab built-in font name constants."""

    TITLE     = 'Helvetica-Bold'
    HEADING   = 'Helvetica-Bold'
    BODY      = 'Helvetica'
    BODY_BOLD = 'Helvetica-Bold'
    MONO      = 'Courier'
    MONO_BOLD = 'Courier-Bold'


# ═══════════════════════════════════════════════════════════════
# PARAGRAPH STYLES
# ═══════════════════════════════════════════════════════════════

class RavinalaStyles:
    """Factory for all Ravinala paragraph styles."""

    @staticmethod
    def get_styles() -> dict:
        """Return a dict of ParagraphStyle objects keyed by style name."""
        C = RavinalaColors

        styles = {
            'doc_title': ParagraphStyle(
                'doc_title',
                fontName='Helvetica-Bold',
                fontSize=24,
                textColor=C.NAVY,
                alignment=TA_CENTER,
                spaceAfter=6,
            ),
            'doc_subtitle': ParagraphStyle(
                'doc_subtitle',
                fontName='Helvetica',
                fontSize=14,
                textColor=C.EMERALD,
                alignment=TA_CENTER,
                spaceAfter=4,
            ),
            'section_title': ParagraphStyle(
                'section_title',
                fontName='Helvetica-Bold',
                fontSize=14,
                textColor=C.NAVY,
                alignment=TA_LEFT,
                spaceAfter=4,
                spaceBefore=2,
            ),
            'subsection': ParagraphStyle(
                'subsection',
                fontName='Helvetica-Bold',
                fontSize=12,
                textColor=C.DARK,
                alignment=TA_LEFT,
                spaceAfter=4,
                spaceBefore=2,
            ),
            'body': ParagraphStyle(
                'body',
                fontName='Helvetica',
                fontSize=10,
                textColor=C.DARK,
                alignment=TA_JUSTIFY,
                leading=14,
                spaceAfter=4,
            ),
            'body_small': ParagraphStyle(
                'body_small',
                fontName='Helvetica',
                fontSize=9,
                textColor=C.MEDIUM,
                alignment=TA_LEFT,
                spaceAfter=2,
            ),
            'body_bold': ParagraphStyle(
                'body_bold',
                fontName='Helvetica-Bold',
                fontSize=10,
                textColor=C.DARK,
                alignment=TA_LEFT,
                spaceAfter=2,
            ),
            'caption': ParagraphStyle(
                'caption',
                fontName='Helvetica-Oblique',
                fontSize=9,
                textColor=C.LIGHT,
                alignment=TA_CENTER,
                spaceAfter=4,
            ),
            'table_header': ParagraphStyle(
                'table_header',
                fontName='Helvetica-Bold',
                fontSize=9,
                textColor=C.WHITE,
                alignment=TA_CENTER,
            ),
            'table_cell': ParagraphStyle(
                'table_cell',
                fontName='Helvetica',
                fontSize=9,
                textColor=C.DARK,
                alignment=TA_LEFT,
            ),
            'table_cell_bold': ParagraphStyle(
                'table_cell_bold',
                fontName='Helvetica-Bold',
                fontSize=9,
                textColor=C.DARK,
                alignment=TA_LEFT,
            ),
            'table_cell_right': ParagraphStyle(
                'table_cell_right',
                fontName='Helvetica',
                fontSize=9,
                textColor=C.DARK,
                alignment=TA_RIGHT,
            ),
            'table_cell_center': ParagraphStyle(
                'table_cell_center',
                fontName='Helvetica',
                fontSize=9,
                textColor=C.DARK,
                alignment=TA_CENTER,
            ),
            'kpi_value': ParagraphStyle(
                'kpi_value',
                fontName='Helvetica-Bold',
                fontSize=22,
                textColor=C.EMERALD,
                alignment=TA_CENTER,
                spaceAfter=2,
            ),
            'kpi_label': ParagraphStyle(
                'kpi_label',
                fontName='Helvetica',
                fontSize=9,
                textColor=C.MEDIUM,
                alignment=TA_CENTER,
            ),
            'disclaimer': ParagraphStyle(
                'disclaimer',
                fontName='Helvetica-Oblique',
                fontSize=8,
                textColor=C.LIGHT,
                alignment=TA_JUSTIFY,
                leading=11,
                spaceAfter=2,
            ),
            'footer_text': ParagraphStyle(
                'footer_text',
                fontName='Helvetica',
                fontSize=8,
                textColor=C.LIGHT,
                alignment=TA_CENTER,
            ),
            'confidential': ParagraphStyle(
                'confidential',
                fontName='Helvetica-Bold',
                fontSize=9,
                textColor=C.RED,
                alignment=TA_CENTER,
            ),
        }
        return styles


# ═══════════════════════════════════════════════════════════════
# UI COMPONENTS
# ═══════════════════════════════════════════════════════════════

class RavinalaComponents:
    """Reusable Platypus building blocks for all report sections."""

    # ------------------------------------------------------------------
    # Header banner
    # ------------------------------------------------------------------

    @staticmethod
    def header_banner(
        title: str,
        subtitle: str = '',
        date=None,
        ref: str = None,
        confidential: bool = True,
    ) -> list:
        """
        Returns a list of Platypus elements forming a full-width dark navy header banner.

        Layout (top to bottom inside the table):
          Row 0 : "🌴 RAVINALA"  (left, white bold) | "CONFIDENTIAL" (right, gold) if flag set
          Row 1 : emerald HRFlowable separator
          Row 2 : title (large, white bold, centered)
          Row 3 : subtitle (emerald, centered) — only when provided
          Row 4 : "Date: …" (left, small white) | "Ref: …" (right, small white)
        """
        C = RavinalaColors

        # Styles used inside the banner (white text on dark bg)
        brand_style = ParagraphStyle(
            'banner_brand', fontName='Helvetica-Bold', fontSize=12,
            textColor=C.WHITE, alignment=TA_LEFT,
        )
        conf_style = ParagraphStyle(
            'banner_conf', fontName='Helvetica-Bold', fontSize=9,
            textColor=C.GOLD, alignment=TA_RIGHT,
        )
        title_style = ParagraphStyle(
            'banner_title', fontName='Helvetica-Bold', fontSize=20,
            textColor=C.WHITE, alignment=TA_CENTER, spaceAfter=2,
        )
        subtitle_style = ParagraphStyle(
            'banner_subtitle', fontName='Helvetica', fontSize=12,
            textColor=C.EMERALD_LIGHT, alignment=TA_CENTER,
        )
        meta_left_style = ParagraphStyle(
            'banner_meta_left', fontName='Helvetica', fontSize=8,
            textColor=C.LIGHT, alignment=TA_LEFT,
        )
        meta_right_style = ParagraphStyle(
            'banner_meta_right', fontName='Helvetica', fontSize=8,
            textColor=C.LIGHT, alignment=TA_RIGHT,
        )

        date_str = date if date else datetime.now().strftime('%d %B %Y')
        ref_str  = ref  if ref  else '—'

        conf_text = 'CONFIDENTIAL' if confidential else ''

        # Separator element (rendered inside a nested single-cell table for layout)
        sep = HRFlowable(
            width='100%', thickness=1.5,
            color=C.EMERALD, spaceAfter=4, spaceBefore=4,
        )

        # Build inner table rows
        inner_rows = []
        inner_styles = []

        # Row 0: brand + confidential badge
        inner_rows.append([
            Paragraph('🌴 RAVINALA', brand_style),
            Paragraph(conf_text, conf_style),
        ])
        inner_styles += [
            ('BACKGROUND', (0, 0), (-1, 0), C.NAVY),
            ('TOPPADDING',    (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('LEFTPADDING',   (0, 0), (-1, 0), 10),
            ('RIGHTPADDING',  (0, 0), (-1, 0), 10),
        ]

        # Row 1: separator (span full width)
        inner_rows.append([sep, ''])
        inner_styles += [
            ('BACKGROUND', (0, 1), (-1, 1), C.NAVY),
            ('SPAN',        (0, 1), (-1, 1)),
            ('TOPPADDING',    (0, 1), (-1, 1), 0),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 0),
            ('LEFTPADDING',   (0, 1), (-1, 1), 10),
            ('RIGHTPADDING',  (0, 1), (-1, 1), 10),
        ]

        # Row 2: title (span full width)
        inner_rows.append([Paragraph(title, title_style), ''])
        inner_styles += [
            ('BACKGROUND', (0, 2), (-1, 2), C.NAVY),
            ('SPAN',        (0, 2), (-1, 2)),
            ('TOPPADDING',    (0, 2), (-1, 2), 6),
            ('BOTTOMPADDING', (0, 2), (-1, 2), 4),
            ('LEFTPADDING',   (0, 2), (-1, 2), 10),
            ('RIGHTPADDING',  (0, 2), (-1, 2), 10),
        ]

        row_offset = 3

        # Row 3 (optional): subtitle
        if subtitle:
            inner_rows.append([Paragraph(subtitle, subtitle_style), ''])
            inner_styles += [
                ('BACKGROUND', (0, row_offset), (-1, row_offset), C.NAVY),
                ('SPAN',        (0, row_offset), (-1, row_offset)),
                ('TOPPADDING',    (0, row_offset), (-1, row_offset), 2),
                ('BOTTOMPADDING', (0, row_offset), (-1, row_offset), 4),
                ('LEFTPADDING',   (0, row_offset), (-1, row_offset), 10),
                ('RIGHTPADDING',  (0, row_offset), (-1, row_offset), 10),
            ]
            row_offset += 1

        # Last row: date + ref
        inner_rows.append([
            Paragraph(f'Date: {date_str}', meta_left_style),
            Paragraph(f'Ref: {ref_str}',   meta_right_style),
        ])
        inner_styles += [
            ('BACKGROUND', (0, row_offset), (-1, row_offset), C.BG_HEADER),
            ('TOPPADDING',    (0, row_offset), (-1, row_offset), 6),
            ('BOTTOMPADDING', (0, row_offset), (-1, row_offset), 10),
            ('LEFTPADDING',   (0, row_offset), (-1, row_offset), 10),
            ('RIGHTPADDING',  (0, row_offset), (-1, row_offset), 10),
        ]

        banner_table = Table(inner_rows, colWidths=['60%', '40%'])
        banner_table.setStyle(TableStyle(inner_styles))

        return [banner_table, Spacer(0, 10)]

    # ------------------------------------------------------------------
    # Section header
    # ------------------------------------------------------------------

    @staticmethod
    def section_header(title: str, number: str = None) -> list:
        """
        Returns a list of elements forming a section header with:
          - A thin emerald HRFlowable top rule
          - A Table cell with a 4px left border in emerald containing the title
          - A small spacer
        """
        C  = RavinalaColors
        St = RavinalaStyles.get_styles()

        display_title = f'{number}. {title}' if number else title

        top_rule = HRFlowable(
            width='100%', thickness=1,
            color=C.EMERALD, spaceAfter=0, spaceBefore=8,
        )

        # Left-border trick: use a thin left-padding column with emerald background
        border_cell = ''   # purely cosmetic colored column
        title_cell  = Paragraph(display_title, St['section_title'])

        tbl = Table(
            [[border_cell, title_cell]],
            colWidths=[4, None],
        )
        tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (0, 0), C.EMERALD),
            ('BACKGROUND',    (1, 0), (1, 0), C.WHITE),
            ('LEFTPADDING',   (0, 0), (0, 0), 0),
            ('RIGHTPADDING',  (0, 0), (0, 0), 0),
            ('TOPPADDING',    (0, 0), (-1, 0), 4),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('LEFTPADDING',   (1, 0), (1, 0), 8),
            ('RIGHTPADDING',  (1, 0), (1, 0), 4),
            ('VALIGN',        (0, 0), (-1, 0), 'MIDDLE'),
        ]))

        return [Spacer(0, 4), top_rule, tbl, Spacer(0, 4)]

    # ------------------------------------------------------------------
    # Key-value table
    # ------------------------------------------------------------------

    @staticmethod
    def key_value_table(
        data: dict,
        columns: int = 2,
        title: str = None,
    ):
        """
        Arrange key-value pairs in a multi-column styled table.

        columns=2 → each row contains [label1, value1, label2, value2]
        columns=1 → each row contains [label, value]
        """
        C  = RavinalaColors
        St = RavinalaStyles.get_styles()

        label_style = ParagraphStyle(
            'kv_label', fontName='Helvetica', fontSize=9,
            textColor=C.MEDIUM, alignment=TA_LEFT,
        )
        value_style = ParagraphStyle(
            'kv_value', fontName='Helvetica-Bold', fontSize=9,
            textColor=C.DARK, alignment=TA_LEFT,
        )

        pairs = list(data.items())
        rows  = []

        if columns == 2:
            col_widths = [4*cm, 6*cm, 4*cm, 6*cm]
            for i in range(0, len(pairs), 2):
                k1, v1 = pairs[i]
                if i + 1 < len(pairs):
                    k2, v2 = pairs[i + 1]
                else:
                    k2, v2 = '', ''
                rows.append([
                    Paragraph(str(k1), label_style),
                    Paragraph(str(v1), value_style),
                    Paragraph(str(k2), label_style),
                    Paragraph(str(v2), value_style),
                ])
        else:
            col_widths = [4*cm, 6*cm]
            for k, v in pairs:
                rows.append([
                    Paragraph(str(k), label_style),
                    Paragraph(str(v), value_style),
                ])

        if not rows:
            rows = [['', '']] if columns == 1 else [['', '', '', '']]

        # Alternating row backgrounds
        table_styles = [
            ('GRID',          (0, 0), (-1, -1), 0.3, C.PALE),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]
        for idx in range(len(rows)):
            bg = C.WHITE if idx % 2 == 0 else C.BG_TABLE_ALT
            table_styles.append(('BACKGROUND', (0, idx), (-1, idx), bg))

        tbl = Table(rows, colWidths=col_widths)
        tbl.setStyle(TableStyle(table_styles))

        elements = []
        if title:
            elements.append(Paragraph(title, St['subsection']))
            elements.append(Spacer(0, 4))
        elements.append(tbl)
        return elements

    # ------------------------------------------------------------------
    # Data table
    # ------------------------------------------------------------------

    @staticmethod
    def data_table(
        headers: list,
        rows: list,
        col_widths=None,
        col_alignments=None,
        highlight_row: int = None,
        total_row: bool = False,
        title: str = None,
        pnl_column: int = None,
    ):
        """
        Build a fully formatted data table with header, alternating rows,
        optional highlighted row, optional totals row, and optional P&L coloring.
        """
        C  = RavinalaColors
        St = RavinalaStyles.get_styles()

        n_cols = len(headers)

        if col_alignments is None:
            col_alignments = ['L'] * n_cols

        align_map = {'L': TA_LEFT, 'C': TA_CENTER, 'R': TA_RIGHT}

        # Header row
        header_cells = [Paragraph(str(h), St['table_header']) for h in headers]
        table_data = [header_cells]

        # Data rows
        for row_idx, row in enumerate(rows):
            cells = []
            for col_idx, val in enumerate(row):
                align = align_map.get(col_alignments[col_idx], TA_LEFT)

                # P&L coloring
                if pnl_column is not None and col_idx == pnl_column:
                    try:
                        numeric = float(str(val).replace(',', '').replace('%', '').replace(' ', ''))
                        color   = C.GREEN if numeric >= 0 else C.RED
                    except (ValueError, AttributeError):
                        color = C.DARK
                    cell_style = ParagraphStyle(
                        f'pnl_cell_{row_idx}_{col_idx}',
                        fontName='Helvetica-Bold', fontSize=9,
                        textColor=color, alignment=align,
                    )
                    cells.append(Paragraph(str(val), cell_style))
                else:
                    # Total row: bold last row
                    is_last = (total_row and row_idx == len(rows) - 1)
                    fn = 'Helvetica-Bold' if is_last else 'Helvetica'
                    cell_style = ParagraphStyle(
                        f'cell_{row_idx}_{col_idx}',
                        fontName=fn, fontSize=9,
                        textColor=C.DARK, alignment=align,
                    )
                    cells.append(Paragraph(str(val), cell_style))
            table_data.append(cells)

        # Build style commands
        table_styles = [
            # Header
            ('BACKGROUND',    (0, 0), (-1, 0), C.BG_TABLE_HEADER),
            ('TEXTCOLOR',     (0, 0), (-1, 0), C.WHITE),
            ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, 0), 9),
            ('ALIGN',         (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID',          (0, 0), (-1, -1), 0.3, C.PALE),
            ('LINEBELOW',     (0, 0), (-1, 0), 1.0, C.EMERALD),
        ]

        # Alternating row backgrounds
        for row_idx in range(len(rows)):
            bg = C.WHITE if row_idx % 2 == 0 else C.BG_TABLE_ALT
            table_styles.append(('BACKGROUND', (0, row_idx + 1), (-1, row_idx + 1), bg))

        # Highlight row
        if highlight_row is not None:
            tbl_row = highlight_row + 1  # +1 for header
            table_styles.append(('BACKGROUND', (0, tbl_row), (-1, tbl_row), C.BG_HIGHLIGHT))

        # Total row: top border + bold background
        if total_row and rows:
            last = len(rows)
            table_styles += [
                ('LINEABOVE',  (0, last), (-1, last), 1.0, C.NAVY),
                ('BACKGROUND', (0, last), (-1, last), C.PALE),
            ]

        tbl = Table(table_data, colWidths=col_widths)
        tbl.setStyle(TableStyle(table_styles))

        elements = []
        if title:
            St2 = RavinalaStyles.get_styles()
            elements.append(Paragraph(title, St2['subsection']))
            elements.append(Spacer(0, 4))
        elements.append(tbl)
        return elements

    # ------------------------------------------------------------------
    # KPI row
    # ------------------------------------------------------------------

    @staticmethod
    def kpi_row(kpis: list, columns: int = 4):
        """
        Build a row of KPI boxes.

        Each kpi dict: {'label': str, 'value': str, 'color': None|'green'|'red'|'gold'}
        """
        C  = RavinalaColors
        St = RavinalaStyles.get_styles()

        color_map = {
            'green': C.GREEN,
            'red':   C.RED,
            'gold':  C.GOLD,
            None:    C.EMERALD,
        }

        cells = []
        for kpi in kpis:
            color     = color_map.get(kpi.get('color'), C.EMERALD)
            val_style = ParagraphStyle(
                f'kpi_v_{kpi.get("label", "")}',
                fontName='Helvetica-Bold', fontSize=22,
                textColor=color, alignment=TA_CENTER, spaceAfter=2,
            )
            inner = [
                [Paragraph(str(kpi.get('value', '—')), val_style)],
                [Paragraph(str(kpi.get('label', '')), St['kpi_label'])],
            ]
            inner_tbl = Table(inner, colWidths=['100%'])
            inner_tbl.setStyle(TableStyle([
                ('TOPPADDING',    (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING',   (0, 0), (-1, -1), 4),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
                ('BACKGROUND',    (0, 0), (-1, -1), C.WHITE),
                ('BOX',           (0, 0), (-1, -1), 1, C.EMERALD_LIGHT),
                ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            cells.append(inner_tbl)

        # Pad to fill `columns` width
        while len(cells) % columns != 0:
            cells.append('')

        # Split into rows of `columns`
        row_data = [cells[i:i+columns] for i in range(0, len(cells), columns)]
        outer = Table(row_data)
        outer.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ]))
        return outer

    # ------------------------------------------------------------------
    # Chart image
    # ------------------------------------------------------------------

    @staticmethod
    def chart_image(fig_or_bytes, width=16*cm, height=8*cm, caption: str = None) -> list:
        """
        Embed a chart (plotly Figure or raw PNG bytes) into the PDF.

        Falls back to a placeholder Paragraph if kaleido is not available.
        """
        St = RavinalaStyles.get_styles()

        img_bytes = None

        if isinstance(fig_or_bytes, (bytes, bytearray)):
            img_bytes = bytes(fig_or_bytes)
        else:
            # Assume plotly Figure — try kaleido export
            try:
                img_bytes = fig_or_bytes.to_image(format='png')
            except Exception:
                elements = [
                    Paragraph(
                        '[Chart unavailable — install kaleido]',
                        St['body_small'],
                    )
                ]
                if caption:
                    elements.append(Paragraph(caption, St['caption']))
                return elements

        # Build centred Image from bytes
        buf = BytesIO(img_bytes)
        img = Image(buf, width=width, height=height)
        img.hAlign = 'CENTER'

        elements = [img]
        if caption:
            elements.append(Spacer(0, 2))
            elements.append(Paragraph(caption, St['caption']))
        return elements

    # ------------------------------------------------------------------
    # Greeks table
    # ------------------------------------------------------------------

    @staticmethod
    def greeks_table(greeks: dict):
        """
        Compact 2-column table showing present Greeks.

        Expects keys: delta, gamma, vega, theta, rho, vanna, volga (all optional/None).
        """
        C = RavinalaColors

        label_style = ParagraphStyle(
            'gr_label', fontName='Helvetica-Bold', fontSize=9,
            textColor=C.MEDIUM, alignment=TA_LEFT,
        )
        value_style = ParagraphStyle(
            'gr_value', fontName='Courier', fontSize=9,
            textColor=C.DARK, alignment=TA_RIGHT,
        )

        greek_defs = [
            ('Delta',  'delta',  4),
            ('Gamma',  'gamma',  4),
            ('Vega',   'vega',   2),
            ('Theta',  'theta',  2),
            ('Rho',    'rho',    2),
            ('Vanna',  'vanna',  4),
            ('Volga',  'volga',  4),
        ]

        rows = []
        for display_name, key, decimals in greek_defs:
            val = greeks.get(key)
            if val is None:
                continue
            try:
                formatted = f'{float(val):.{decimals}f}'
            except (TypeError, ValueError):
                formatted = str(val)
            rows.append([
                Paragraph(display_name, label_style),
                Paragraph(formatted, value_style),
            ])

        if not rows:
            rows = [[Paragraph('No Greeks available', label_style), Paragraph('—', value_style)]]

        table_styles = [
            ('GRID',          (0, 0), (-1, -1), 0.3, C.PALE),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 8),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]
        for i in range(len(rows)):
            bg = C.WHITE if i % 2 == 0 else C.BG_TABLE_ALT
            table_styles.append(('BACKGROUND', (0, i), (-1, i), bg))

        tbl = Table(rows, colWidths=[5*cm, 4*cm])
        tbl.setStyle(TableStyle(table_styles))
        return tbl

    # ------------------------------------------------------------------
    # Schedule table
    # ------------------------------------------------------------------

    @staticmethod
    def schedule_table(
        barriers: list,
        coupons,
        inception_date,
        maturity_date,
        tenor_years: float,
    ):
        """
        Generate an observation-date schedule table.

        Columns: Date | Event | Barrier Level | Status
        """
        from datetime import date, timedelta

        C  = RavinalaColors
        St = RavinalaStyles.get_styles()

        header_style = St['table_header']
        cell_style   = St['table_cell']
        center_style = St['table_cell_center']

        # Determine frequency
        frequency = 'annual'
        coupon_dict = coupons if isinstance(coupons, dict) else {}
        if coupon_dict:
            freq_str = str(coupon_dict.get('frequency', 'annual')).lower()
            if 'quarter' in freq_str or freq_str == 'q':
                frequency = 'quarterly'
            elif 'semi' in freq_str or freq_str == 'semi-annual':
                frequency = 'semi-annual'
            elif 'month' in freq_str:
                frequency = 'monthly'

        # Parse dates
        def _parse_date(d):
            if d is None:
                return None
            if isinstance(d, (date,)):
                return d
            if hasattr(d, 'date'):
                return d.date()
            try:
                from datetime import datetime as _dt
                return _dt.strptime(str(d)[:10], '%Y-%m-%d').date()
            except Exception:
                return None

        t_inception = _parse_date(inception_date)
        t_maturity  = _parse_date(maturity_date)

        if t_inception is None or t_maturity is None:
            # Fallback: use tenor_years
            from datetime import date as _date
            t_inception = _date.today()
            import datetime as _dt_mod
            t_maturity  = t_inception + _dt_mod.timedelta(days=int((tenor_years or 1) * 365))

        # Generate observation dates
        obs_dates = []
        if frequency == 'quarterly':
            months_step = 3
        elif frequency == 'semi-annual':
            months_step = 6
        elif frequency == 'monthly':
            months_step = 1
        else:
            months_step = 12

        current = t_inception
        while current < t_maturity:
            # Advance by months_step months
            month = current.month + months_step
            year  = current.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            from datetime import date as _date
            try:
                import calendar
                max_day = calendar.monthrange(year, month)[1]
                day     = min(current.day, max_day)
                current = _date(year, month, day)
            except Exception:
                break
            if current <= t_maturity:
                obs_dates.append(current)

        # Always include maturity if not already in list
        if obs_dates and obs_dates[-1] != t_maturity:
            obs_dates.append(t_maturity)
        elif not obs_dates:
            obs_dates.append(t_maturity)

        # Build barrier lookup {date_str: barrier}
        ki_barrier_pct  = None
        au_barrier_pct  = None
        cp_barrier_pct  = coupon_dict.get('condition_barrier_pct')
        paid_coupons    = coupon_dict.get('paid_coupons', []) or []

        for b in (barriers or []):
            bt = str(b.get('barrier_type', '')).lower()
            if 'knock' in bt or 'ki' in bt or 'down' in bt:
                ki_barrier_pct = b.get('level_pct')
            elif 'autocall' in bt or 'call' in bt or 'up' in bt:
                au_barrier_pct = b.get('level_pct')

        # Triggered barrier dates
        triggered_dates = set()
        for b in (barriers or []):
            if b.get('is_triggered') and b.get('triggered_date'):
                td = _parse_date(b.get('triggered_date'))
                if td:
                    triggered_dates.add(td)

        today = __import__('datetime').date.today()

        # Build rows
        header_row = [
            Paragraph('Date',          header_style),
            Paragraph('Event',         header_style),
            Paragraph('Barrier Level', header_style),
            Paragraph('Status',        header_style),
        ]
        table_rows = [header_row]

        for obs_dt in obs_dates:
            is_maturity = (obs_dt == t_maturity)
            event       = 'Maturity' if is_maturity else 'Observation'

            # Barrier level string
            barriers_str_parts = []
            if au_barrier_pct is not None:
                barriers_str_parts.append(f'Autocall: {au_barrier_pct:.0f}%')
            if cp_barrier_pct is not None:
                barriers_str_parts.append(f'Coupon: {cp_barrier_pct:.0f}%')
            if ki_barrier_pct is not None:
                barriers_str_parts.append(f'KI: {ki_barrier_pct:.0f}%')
            barrier_str = ' | '.join(barriers_str_parts) if barriers_str_parts else '—'

            # Status
            date_str_key = obs_dt.strftime('%Y-%m-%d')
            if obs_dt in triggered_dates:
                status = 'Triggered'
                status_color = C.ORANGE
            elif obs_dt < today:
                # Past date — check if coupon was paid
                if date_str_key in [str(p)[:10] for p in paid_coupons]:
                    status = '✓ Paid'
                    status_color = C.GREEN
                else:
                    status = '✗ Missed'
                    status_color = C.RED
            else:
                status = 'Pending'
                status_color = C.MEDIUM

            status_style = ParagraphStyle(
                f'sched_status_{date_str_key}',
                fontName='Helvetica-Bold', fontSize=9,
                textColor=status_color, alignment=TA_CENTER,
            )

            table_rows.append([
                Paragraph(obs_dt.strftime('%d %b %Y'), cell_style),
                Paragraph(event, center_style),
                Paragraph(barrier_str, center_style),
                Paragraph(status, status_style),
            ])

        # Style commands
        table_styles = [
            ('BACKGROUND',    (0, 0), (-1, 0), C.BG_TABLE_HEADER),
            ('LINEBELOW',     (0, 0), (-1, 0), 1.0, C.EMERALD),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID',          (0, 0), (-1, -1), 0.3, C.PALE),
        ]
        for i in range(1, len(table_rows)):
            bg = C.WHITE if i % 2 == 0 else C.BG_TABLE_ALT
            table_styles.append(('BACKGROUND', (0, i), (-1, i), bg))

        # Highlight maturity row
        if len(table_rows) > 1:
            table_styles.append(('BACKGROUND', (0, len(table_rows) - 1), (-1, len(table_rows) - 1), C.BG_HIGHLIGHT))

        tbl = Table(table_rows, colWidths=[3.5*cm, 4*cm, 6*cm, 3*cm])
        tbl.setStyle(TableStyle(table_styles))
        return tbl

    # ------------------------------------------------------------------
    # Disclaimer block
    # ------------------------------------------------------------------

    @staticmethod
    def disclaimer_block(custom_text: str = None) -> list:
        """
        Returns a list of elements: thin rule, spacer, disclaimer paragraph,
        optional custom text paragraph.
        """
        C  = RavinalaColors
        St = RavinalaStyles.get_styles()

        standard_text = (
            'This document is produced by Ravinala for informational purposes only. '
            'It does not constitute an offer, solicitation, or recommendation to buy or sell '
            'any financial instrument. All pricing is indicative and based on mathematical models. '
            'Past performance is not indicative of future results. '
            'Confidential — for authorized recipients only. '
            'Generated by Ravinala v2.0 \u00a9 2026 TSIVAHINY Matthias.'
        )

        rule = HRFlowable(
            width='100%', thickness=0.5,
            color=C.LIGHT, spaceAfter=4, spaceBefore=8,
        )

        elements = [
            rule,
            Spacer(0, 4),
            Paragraph(standard_text, St['disclaimer']),
        ]

        if custom_text:
            elements.append(Spacer(0, 2))
            elements.append(Paragraph(custom_text, St['disclaimer']))

        return elements


# ═══════════════════════════════════════════════════════════════
# DOCUMENT BUILDER
# ═══════════════════════════════════════════════════════════════

class RavinalaDocument:
    """
    High-level PDF document builder.

    Usage:
        doc = RavinalaDocument('/path/to/output.pdf', title='My Report')
        doc.build(elements)
    """

    def __init__(
        self,
        output_path: str,
        title: str = '',
        author: str = 'Ravinala',
        landscape_mode: bool = False,
        watermark_text: str = None,
    ):
        self.output_path    = output_path
        self.title          = title
        self.author         = author
        self.landscape_mode = landscape_mode
        self.watermark_text = watermark_text
        self._page_count    = [0]   # mutable list so it's modifiable in closure

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _draw_page_decorations(self, canv, doc):
        """Draw header rule, footer, and optional watermark on every page."""
        from reportlab.lib.pagesizes import A4, landscape as rl_landscape
        C = RavinalaColors

        page_w, page_h = canv._pagesize

        self._page_count[0] += 1
        page_num = self._page_count[0]

        canv.saveState()

        # ── Watermark ───────────────────────────────────────────────
        if self.watermark_text:
            canv.saveState()
            canv.setFont('Helvetica-Bold', 60)
            canv.setFillColor(HexColor('#E2E8F0'))
            canv.setFillAlpha(0.18)
            canv.translate(page_w / 2, page_h / 2)
            canv.rotate(45)
            canv.drawCentredString(0, 0, self.watermark_text)
            canv.restoreState()

        # ── Top emerald rule ────────────────────────────────────────
        rule_y = page_h - 1.5 * cm
        canv.setStrokeColor(C.EMERALD)
        canv.setLineWidth(1.5)
        canv.line(2 * cm, rule_y, page_w - 2 * cm, rule_y)

        # ── Footer ──────────────────────────────────────────────────
        footer_y    = 1.3 * cm
        footer_rule = 0.8 * cm

        # Thin rule above footer
        canv.setStrokeColor(C.LIGHT)
        canv.setLineWidth(0.5)
        canv.line(2 * cm, footer_rule, page_w - 2 * cm, footer_rule)

        canv.setFont('Helvetica', 8)
        canv.setFillColor(C.LIGHT)

        # Left text
        canv.drawString(2 * cm, footer_y, '\U0001f334 Ravinala v2.0 \u2014 Confidential')

        # Centre text: generation timestamp
        gen_str = f'Generated: {datetime.now().strftime("%d %b %Y %H:%M")}'
        canv.drawCentredString(page_w / 2, footer_y, gen_str)

        # Right text: page number
        canv.drawRightString(page_w - 2 * cm, footer_y, f'Page {page_num}')

        canv.restoreState()

    def _on_first_page(self, canv, doc):
        self._draw_page_decorations(canv, doc)

    def _on_later_pages(self, canv, doc):
        self._draw_page_decorations(canv, doc)

    # ------------------------------------------------------------------
    # Public build method
    # ------------------------------------------------------------------

    def build(self, elements: list) -> str:
        """
        Compile the Platypus element list into a PDF file.

        Returns the output_path string.
        """
        from reportlab.lib.pagesizes import landscape as rl_landscape

        # Ensure output directory exists
        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)

        page_size = rl_landscape(A4) if self.landscape_mode else A4

        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=page_size,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            title=self.title,
            author=self.author,
            subject='Ravinala Report',
            creator='Ravinala v2.0',
        )

        # Reset page counter before each build
        self._page_count[0] = 0

        doc.build(
            elements,
            onFirstPage=self._on_first_page,
            onLaterPages=self._on_later_pages,
        )

        return self.output_path
