"""
PayReality Reporting Module - Phase 2 (Enhanced Formatting)
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable, HRFlowable, KeepTogether, PageBreak,
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from core import CONTROL_TAXONOMY

# ── Palette ──────────────────────────────────────────────────────────────────
NAVY      = colors.HexColor("#1A1752")
PURPLE    = colors.HexColor("#534AB7")
PURPLE_LT = colors.HexColor("#EEEDFE")
TEAL      = colors.HexColor("#0F6E56")
TEAL_LT   = colors.HexColor("#E1F5EE")
AMBER     = colors.HexColor("#854F0B")
AMBER_LT  = colors.HexColor("#FAEEDA")
CORAL     = colors.HexColor("#993C1D")
CORAL_LT  = colors.HexColor("#FAECE7")
GRAY      = colors.HexColor("#5F5E5A")
GRAY_LT   = colors.HexColor("#F1EFE8")
WHITE     = colors.white
INK       = colors.HexColor("#1A1A1A")

RISK_COLORS = {
    "High":   colors.HexColor("#993C1D"),
    "Medium": colors.HexColor("#854F0B"),
    "Low":    colors.HexColor("#0F6E56"),
}

STRATEGY_LABELS = {
    "exact":                          "Exact Match",
    "normalized":                     "Normalised",
    "token_sort":                     "Token Sort",
    "partial":                        "Partial",
    "levenshtein":                    "Edit Distance",
    "phonetic":                       "Phonetic",
    "obfuscation_dot_spacing":        "Obfsc / Dot Spacing",
    "obfuscation_leetspeak":          "Obfsc / Leetspeak",
    "obfuscation_char_repetition":    "Obfsc / Char Repeat",
    "obfuscation_homoglyph":          "Obfsc / Homoglyph",
    "none":                           "No Match",
}

_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def _safe_filename(name: str) -> str:
    return _INVALID_FILENAME_CHARS.sub("_", name)


class ColorBar(Flowable):
    def __init__(self, w, h, fill):
        super().__init__()
        self.width = w
        self.height = h
        self.fill = fill

    def draw(self):
        self.canv.setFillColor(self.fill)
        self.canv.rect(0, 0, self.width, self.height, stroke=0, fill=1)


class PayRealityReport:

    def __init__(self, client_name: str = "Client", config: Optional[Dict] = None):
        self.client_name = client_name
        self.config = config or {}
        self.logger = logging.getLogger("PayReality.Report")
        self.currency = self.config.get("currency_symbol", "R")
        self._report_date = datetime.now()
        
        page_size_key = self.config.get("page_size", "a4").lower()
        self._pagesize = LETTER if page_size_key == "letter" else A4
        self._W, self._H = self._pagesize
        
        self._build_styles()

    def _build_styles(self):
        """Build all paragraph styles once"""
        self.styles = {}
        
        # Title style
        self.styles['title'] = ParagraphStyle(
            'title',
            fontName='Helvetica-Bold',
            fontSize=24,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=12,
            spaceBefore=20,
        )
        
        # Subtitle style
        self.styles['subtitle'] = ParagraphStyle(
            'subtitle',
            fontName='Helvetica',
            fontSize=12,
            textColor=PURPLE,
            alignment=TA_CENTER,
            spaceAfter=20,
        )
        
        # Heading 1
        self.styles['h1'] = ParagraphStyle(
            'h1',
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=NAVY,
            spaceBefore=18,
            spaceAfter=8,
            keepWithNext=True,
        )
        
        # Heading 2
        self.styles['h2'] = ParagraphStyle(
            'h2',
            fontName='Helvetica-Bold',
            fontSize=13,
            textColor=PURPLE,
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True,
        )
        
        # Body text
        self.styles['body'] = ParagraphStyle(
            'body',
            fontName='Helvetica',
            fontSize=10,
            textColor=INK,
            leading=14,
            alignment=TA_LEFT,
            spaceAfter=6,
        )
        
        # Body bold
        self.styles['body_bold'] = ParagraphStyle(
            'body_bold',
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=INK,
            leading=14,
            spaceAfter=6,
        )
        
        # Small text
        self.styles['small'] = ParagraphStyle(
            'small',
            fontName='Helvetica',
            fontSize=8,
            textColor=GRAY,
            leading=10,
        )
        
        # Table header
        self.styles['table_header'] = ParagraphStyle(
            'table_header',
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=WHITE,
            alignment=TA_CENTER,
            leading=12,
        )
        
        # Table cell
        self.styles['table_cell'] = ParagraphStyle(
            'table_cell',
            fontName='Helvetica',
            fontSize=8,
            textColor=INK,
            leading=11,
        )
        
        # Table cell bold
        self.styles['table_cell_bold'] = ParagraphStyle(
            'table_cell_bold',
            fontName='Helvetica-Bold',
            fontSize=8,
            textColor=INK,
            leading=11,
        )

    def _fmt(self, amount: float) -> str:
        if amount >= 0:
            return f"{self.currency} {amount:,.0f}"
        return f"-{self.currency} {abs(amount):,.0f}"

    def _on_page(self, canvas, doc):
        W, H = self._W, self._H
        date_str = self._report_date.strftime("%d %B %Y")

        canvas.saveState()
        # Header bar
        canvas.setFillColor(NAVY)
        canvas.rect(0, H - 28 * mm, W, 28 * mm, stroke=0, fill=1)
        
        # Header text
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(20 * mm, H - 18 * mm, "PayReality")
        canvas.setFont("Helvetica", 9)
        canvas.drawString(20 * mm, H - 24 * mm, "Independent Control Verification Report")
        
        # Client and date
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(W - 20 * mm, H - 18 * mm, self.client_name)
        canvas.drawRightString(W - 20 * mm, H - 24 * mm, date_str)
        
        # Accent line
        canvas.setFillColor(TEAL)
        canvas.rect(0, H - 29.5 * mm, W, 1.5 * mm, stroke=0, fill=1)
        
        # Footer
        canvas.setStrokeColor(GRAY_LT)
        canvas.setLineWidth(0.4)
        canvas.line(20 * mm, 18 * mm, W - 20 * mm, 18 * mm)
        canvas.setFillColor(GRAY)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(20 * mm, 12 * mm, "AI Securewatch · sean@aisecurewatch.com · Confidential")
        canvas.drawRightString(W - 20 * mm, 12 * mm, f"Page {doc.page}")
        
        canvas.restoreState()

    def _kpi_table(self, results: Dict):
        """Create KPI summary table with proper spacing"""
        W = self._W
        ent = results["entropy_score"]
        ent_color = CORAL if ent >= 20 else AMBER if ent >= 10 else TEAL

        # Calculate column widths
        cw = (W - 40 * mm) / 5
        
        # Create cells with proper spacing
        cells = []
        
        # Total Payments
        cells.append([
            Paragraph(f"{results['total_payments']:,}", 
                     ParagraphStyle('v1', parent=self.styles['body'], fontSize=20, 
                                   textColor=PURPLE, alignment=TA_CENTER)),
            Paragraph("Total Payments", self.styles['small'])
        ])
        
        # Exceptions
        cells.append([
            Paragraph(f"{results['exception_count']:,}", 
                     ParagraphStyle('v2', parent=self.styles['body'], fontSize=20,
                                   textColor=CORAL, alignment=TA_CENTER)),
            Paragraph("Exceptions", self.styles['small'])
        ])
        
        # Exception Spend
        cells.append([
            Paragraph(self._fmt(results["exception_spend"]), 
                     ParagraphStyle('v3', parent=self.styles['body'], fontSize=16,
                                   textColor=AMBER, alignment=TA_CENTER)),
            Paragraph("Exception Spend", self.styles['small'])
        ])
        
        # Entropy
        cells.append([
            Paragraph(f"{ent:.1f}%", 
                     ParagraphStyle('v4', parent=self.styles['body'], fontSize=20,
                                   textColor=ent_color, alignment=TA_CENTER)),
            Paragraph("Control Entropy", self.styles['small'])
        ])
        
        # Master Health
        cells.append([
            Paragraph(f"{results['vendor_health']['health_score']}", 
                     ParagraphStyle('v5', parent=self.styles['body'], fontSize=20,
                                   textColor=TEAL, alignment=TA_CENTER)),
            Paragraph("Master Health", self.styles['small'])
        ])
        
        # Build table with values in first row, labels in second
        val_row = [c[0] for c in cells]
        lbl_row = [c[1] for c in cells]
        
        t = Table([val_row, lbl_row], colWidths=[cw] * 5)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GRAY_LT),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 1), (-1, 1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEAFTER', (0, 0), (3, -1), 0.5, colors.lightgrey),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.lightgrey),
        ]))
        return t

    def _match_table(self, match_stats: Dict, total: int):
        """Create match distribution table"""
        W = self._W
        cw_total = W - 40 * mm
        
        order = [
            "exact", "normalized", "token_sort", "partial", "levenshtein",
            "phonetic",
            "obfuscation_dot_spacing", "obfuscation_leetspeak",
            "obfuscation_char_repetition", "obfuscation_homoglyph",
            "none",
        ]
        
        pass_numbers = {
            "exact": "1", "normalized": "2", "token_sort": "3",
            "partial": "4", "levenshtein": "5", "phonetic": "6",
            "obfuscation_dot_spacing": "7", "obfuscation_leetspeak": "7",
            "obfuscation_char_repetition": "7", "obfuscation_homoglyph": "7",
            "none": "—",
        }
        
        colors_map = {
            "exact": TEAL, "normalized": TEAL,
            "token_sort": PURPLE, "partial": PURPLE,
            "levenshtein": AMBER, "phonetic": AMBER,
            "obfuscation_dot_spacing": CORAL, "obfuscation_leetspeak": CORAL,
            "obfuscation_char_repetition": CORAL, "obfuscation_homoglyph": CORAL,
            "none": CORAL,
        }
        
        headers = ["Pass", "Strategy", "Count", "% of Total"]
        data = [headers]
        
        for s in order:
            count = match_stats.get(s, 0)
            pct = (count / total * 100) if total > 0 else 0
            c = colors_map.get(s, GRAY)
            
            pass_text = f"<b>{pass_numbers.get(s, '?')}</b>"
            strategy_text = STRATEGY_LABELS.get(s, s)
            
            data.append([
                Paragraph(pass_text, self.styles['table_cell_bold']),
                Paragraph(strategy_text, self.styles['table_cell']),
                Paragraph(f"{count:,}", self.styles['table_cell']),
                Paragraph(f"{pct:.1f}%", self.styles['table_cell']),
            ])
        
        t = Table(data, colWidths=[cw_total * 0.12, cw_total * 0.48, cw_total * 0.2, cw_total * 0.2])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_LT]),
            ('GRID', (0, 0), (-1, -1), 0.3, GRAY_LT),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return t

    def _exception_block(self, ex: Dict, index: int):
        """Create an exception detail block with proper spacing"""
        W = self._W
        cw = W - 40 * mm
        
        risk = ex.get("risk_level", "Low")
        risk_c = RISK_COLORS.get(risk, GRAY)
        conf = ex.get("confidence_score", 0)
        amount = ex.get("amount", 0)
        controls = ex.get("control_ids", [])
        explanation = ex.get("explanation", "")
        strategy = STRATEGY_LABELS.get(ex.get("match_strategy", "none"), "—")
        
        # Header table
        header_data = [[
            Paragraph(f"#{index}", ParagraphStyle('idx', parent=self.styles['table_cell_bold'], textColor=WHITE)),
            Paragraph(ex.get("payee_name", "Unknown")[:60], ParagraphStyle('name', parent=self.styles['table_cell_bold'], textColor=WHITE)),
            Paragraph(self._fmt(amount), ParagraphStyle('amt', parent=self.styles['table_cell_bold'], textColor=WHITE, alignment=TA_RIGHT)),
        ]]
        
        header = Table(header_data, colWidths=[cw * 0.07, cw * 0.65, cw * 0.28])
        header.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), NAVY),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        # Meta info table
        conf_c = CORAL if conf >= 70 else AMBER if conf >= 40 else TEAL
        
        meta_data = [[
            Paragraph(f"Risk: <b>{risk}</b>", self.styles['table_cell']),
            Paragraph(f"Confidence: <b>{conf}/100</b>", self.styles['table_cell']),
            Paragraph(f"Match: <b>{strategy}</b>", self.styles['table_cell']),
            Paragraph(f"Controls: <b>{', '.join(controls)}</b>", self.styles['table_cell']),
        ]]
        
        meta = Table(meta_data, colWidths=[cw * 0.18, cw * 0.22, cw * 0.3, cw * 0.3])
        meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), PURPLE_LT),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        # Explanation table
        explanation_data = [[
            Paragraph("<b>Why flagged:</b>", self.styles['table_cell']),
            Paragraph(explanation, self.styles['body']),
        ]]
        
        expl = Table(explanation_data, colWidths=[cw * 0.13, cw * 0.87])
        expl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), WHITE),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        return KeepTogether([header, Spacer(1, 2), meta, Spacer(1, 2), expl, Spacer(1, 8)])

    def generate_report(self, results: Dict, output_dir: str) -> str:
        """Generate the PDF report with improved formatting"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        ts = self._report_date.strftime("%Y%m%d_%H%M%S")
        clean = _safe_filename(self.client_name.replace(" ", "_"))
        filepath = os.path.join(output_dir, f"PayReality_{clean}_{ts}.pdf")

        doc = SimpleDocTemplate(
            filepath,
            pagesize=self._pagesize,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=34 * mm,
            bottomMargin=24 * mm,
            title=f"PayReality Report - {self.client_name}",
            author="AI Securewatch",
        )

        story = []
        W, H = self._W, self._H
        cw = W - 40 * mm

        # ── COVER PAGE ──────────────────────────────────────────────────────────
        story.append(Spacer(1, 30 * mm))
        story.append(Paragraph("PAYREALITY", self.styles['title']))
        story.append(Paragraph("Independent Control Verification Report", self.styles['subtitle']))
        story.append(Spacer(1, 10 * mm))
        story.append(Paragraph(self.client_name, 
                              ParagraphStyle('client', parent=self.styles['h1'], alignment=TA_CENTER)))
        story.append(Paragraph(self._report_date.strftime("%d %B %Y"), 
                              ParagraphStyle('date', parent=self.styles['body'], alignment=TA_CENTER, textColor=GRAY)))
        story.append(Spacer(1, 20 * mm))
        story.append(HRFlowable(width="80%", thickness=1, color=PURPLE, spaceAfter=20))
        story.append(Spacer(1, 10 * mm))

        # KPI Summary
        story.append(self._kpi_table(results))
        story.append(Spacer(1, 15 * mm))

        # Metadata table
        meta_data = [
            ["Run ID", results.get("run_id", "—")],
            ["Analysis Date", self._report_date.strftime("%Y-%m-%d %H:%M")],
            ["Client", results.get("client_name", "—")],
            ["Match Threshold", f"{results.get('threshold', 80)}%"],
            ["Vendor Master Hash", results.get("master_file_hash", "—")[:16] + "..."],
            ["Payments Hash", results.get("payments_file_hash", "—")[:16] + "..."],
        ]
        
        mt = Table(meta_data, colWidths=[cw * 0.28, cw * 0.72])
        mt.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), PURPLE),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [GRAY_LT, WHITE]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.3, GRAY_LT),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(mt)
        story.append(PageBreak())

        # ── SECTION 1: Control Entropy ──────────────────────────────────────────
        story.append(Paragraph("1. Control Entropy Score", self.styles['h1']))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LT, spaceAfter=12))
        
        ent = results["entropy_score"]
        if ent >= 20:
            ent_interp = "CRITICAL — Over 20% of spend bypassed approved vendor controls. Immediate action required."
        elif ent >= 10:
            ent_interp = "WARNING — Between 10–20% of spend requires investigation."
        else:
            ent_interp = "ACCEPTABLE — Control failure rate is within normal bounds."
        
        story.append(Paragraph(
            "The Control Entropy Score measures the percentage of total spend "
            "that bypassed approved vendor controls after all seven matching passes.",
            self.styles['body']
        ))
        story.append(Spacer(1, 8))
        
        ent_c = CORAL if ent >= 20 else AMBER if ent >= 10 else TEAL
        ent_tbl = Table([[
            Paragraph(f"{ent:.2f}%", 
                     ParagraphStyle('ent', parent=self.styles['body'], fontSize=36, 
                                   textColor=ent_c, alignment=TA_CENTER)),
            Paragraph(ent_interp, 
                     ParagraphStyle('ei', parent=self.styles['body'], leading=15)),
        ]], colWidths=[cw * 0.25, cw * 0.75])
        ent_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GRAY_LT),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 16),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ]))
        story.append(ent_tbl)
        story.append(Spacer(1, 15))

        # ── SECTION 2: 7-Pass Distribution ────────────────────────────────────
        story.append(Paragraph("2. 7-Pass Semantic Matching Distribution", self.styles['h1']))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LT, spaceAfter=12))
        story.append(Paragraph(
            "Each payment is processed through seven progressively sophisticated "
            "matching passes. The table below shows how payments were classified.",
            self.styles['body']
        ))
        story.append(Spacer(1, 10))
        story.append(self._match_table(results["match_stats"], results["total_payments"]))
        story.append(Spacer(1, 15))

        # ── SECTION 3: Vendor Master Health ───────────────────────────────────
        story.append(Paragraph("3. Vendor Master Health", self.styles['h1']))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LT, spaceAfter=12))
        
        health = results.get("vendor_health", {})
        hs = health.get("health_score", 0)
        hs_c = TEAL if hs >= 80 else AMBER if hs >= 60 else CORAL
        
        hd = [
            ["Total Vendors", f"{health.get('total_vendors', 0):,}"],
            ["Duplicate Records", f"{health.get('duplicate_records', 0):,}"],
            ["Blank Names", f"{health.get('blank_names', 0):,}"],
            ["Short Names (<3 chars)", f"{health.get('short_names', 0):,}"],
            ["Health Score", f"{hs} / 100 — {health.get('health_label', '—')}"],
        ]
        
        ht = Table(hd, colWidths=[cw * 0.35, cw * 0.65])
        ht.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), PURPLE),
            ('TEXTCOLOR', (1, 4), (1, 4), hs_c),
            ('FONTNAME', (1, 4), (1, 4), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [GRAY_LT, WHITE]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.3, GRAY_LT),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(ht)
        story.append(PageBreak())

        # ── SECTION 4: Exception Detail ────────────────────────────────────────
        story.append(Paragraph("4. Exception Detail", self.styles['h1']))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LT, spaceAfter=12))
        story.append(Paragraph(
            f"The following {len(results['exceptions'])} exceptions are ranked by "
            f"confidence score (highest first). Each includes the control violated, "
            f"matching pass that triggered the flag, and a human-readable explanation.",
            self.styles['body']
        ))
        story.append(Spacer(1, 12))

        max_ex = min(len(results["exceptions"]), 100)
        for i, ex in enumerate(results["exceptions"][:max_ex], 1):
            story.append(self._exception_block(ex, i))

        if len(results["exceptions"]) > max_ex:
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                f"… and {len(results['exceptions']) - max_ex} additional exceptions. "
                "Export JSON or CSV for the complete list.",
                self.styles['body']
            ))

        # ── SECTION 5: Control Violation Summary ────────────────────────────────
        story.append(PageBreak())
        story.append(Paragraph("5. Control Violation Summary", self.styles['h1']))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LT, spaceAfter=12))
        story.append(Paragraph(
            "Count of exceptions per control type across this analysis run.",
            self.styles['body']
        ))
        story.append(Spacer(1, 10))

        from collections import Counter
        ctrl_counter: Counter = Counter()
        for ex in results["exceptions"]:
            for c in ex.get("control_ids", []):
                ctrl_counter[c] += 1

        if ctrl_counter:
            ctrl_rows = [["Control", "Name", "Category", "Severity", "Count"]]
            for cid, count in sorted(ctrl_counter.items(), key=lambda x: -x[1]):
                tax = CONTROL_TAXONOMY.get(cid, {})
                sev = tax.get("severity", "—")
                sev_c = CORAL if sev == "Critical" else AMBER if sev == "High" else TEAL
                ctrl_rows.append([
                    Paragraph(f"<b>{cid}</b>", self.styles['table_cell']),
                    Paragraph(tax.get("name", cid), self.styles['table_cell']),
                    Paragraph(tax.get("category", "—"), self.styles['table_cell']),
                    Paragraph(sev, ParagraphStyle('sev', parent=self.styles['table_cell'], textColor=sev_c)),
                    Paragraph(f"{count:,}", ParagraphStyle('cnt', parent=self.styles['table_cell_bold'], alignment=TA_RIGHT)),
                ])

            ct = Table(ctrl_rows, colWidths=[cw * 0.1, cw * 0.35, cw * 0.25, cw * 0.15, cw * 0.15])
            ct.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), NAVY),
                ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_LT]),
                ('GRID', (0, 0), (-1, -1), 0.3, GRAY_LT),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(ct)
        else:
            story.append(Paragraph("No control violations detected.", self.styles['body']))
        
        story.append(Spacer(1, 20))

        # ── SECTION 6: Recommendations ─────────────────────────────────────────
        story.append(Paragraph("6. Recommendations", self.styles['h1']))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LT, spaceAfter=12))

        recs = []
        if ent >= 20:
            recs.append(("Critical", 
                "Immediate escalation required — Control Entropy >20% indicates systemic "
                "vendor control failure. Freeze new vendor onboarding and review all "
                "high-confidence exceptions with management."))
        elif ent >= 10:
            recs.append(("High",
                "Investigate all High-risk exceptions flagged in Section 4. Prioritise "
                "items with Confidence Score >=70 and OBC (Obfuscation) control violations."))
        
        if ctrl_counter.get("VDC", 0) > 0:
            recs.append(("Medium",
                f"{ctrl_counter['VDC']} duplicate vendor payment(s) detected. Reconcile "
                "against payment authorisation records and implement pre-payment duplicate checks."))
        
        if ctrl_counter.get("VTC", 0) > 0:
            recs.append(("Medium",
                f"{ctrl_counter['VTC']} new vendor(s) received high-value payments. Verify "
                "onboarding documentation and approval sign-off for each."))
        
        if health.get("health_score", 100) < 80:
            recs.append(("Low",
                f"Vendor Master Health Score is {health.get('health_score', 0)}/100. "
                "Perform a master data cleanse — remove duplicates, fill blank names, "
                "and deactivate dormant records."))
        
        if not recs:
            recs.append(("Low",
                "No critical findings. Continue quarterly validation to maintain continuous assurance."))

        sev_c_map = {"Critical": CORAL, "High": AMBER, "Medium": PURPLE, "Low": TEAL}
        for sev, text in recs:
            rc = sev_c_map.get(sev, GRAY)
            row = Table([[
                Paragraph(f"<b>{sev}</b>", ParagraphStyle('rs', parent=self.styles['table_cell'], textColor=rc)),
                Paragraph(text, self.styles['body']),
            ]], colWidths=[cw * 0.12, cw * 0.88])
            row.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), GRAY_LT),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('LINEBELOW', (0, 0), (-1, -1), 0.3, WHITE),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(row)
            story.append(Spacer(1, 4))

        # ── Closing ────────────────────────────────────────────────────────────
        story.append(Spacer(1, 24))
        story.append(HRFlowable(width="80%", thickness=0.5, color=PURPLE, spaceAfter=12))
        story.append(Paragraph(
            '"If vendor controls have not been independently verified, '
            'their effectiveness cannot be assumed."',
            ParagraphStyle('quote', parent=self.styles['body'], alignment=TA_CENTER, textColor=PURPLE)
        ))
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            "AI Securewatch · sean@aisecurewatch.com · payreality.aisecurewatch.com",
            self.styles['small']
        ))

        # Build the PDF
        doc.build(story, onFirstPage=self._on_page, onLaterPages=self._on_page)
        self.logger.info(f"Report generated: {filepath}")
        return filepath