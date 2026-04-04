"""
PayReality Reporting Module - Phase 2 (Patched)

Patch applied:
  [RPT-1]  Currency symbol read from config (default "R") instead of being
           hardcoded. International clients receive the correct symbol.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.platypus import Flowable

W, H = A4

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
    "exact":                       "Exact Match",
    "normalized":                  "Normalised",
    "token_sort":                  "Token Sort",
    "partial":                     "Partial",
    "levenshtein":                 "Edit Distance",
    "phonetic":                    "Phonetic",
    "obfuscation_dot_spacing":     "Obfuscation",
    "obfuscation_leetspeak":       "Obfuscation",
    "obfuscation_char_repetition": "Obfuscation",
    "obfuscation_homoglyph":       "Obfuscation",
    "none":                        "No Match",
}


# ── Coloured Rule Flowable ────────────────────────────────────────────────────
class ColorBar(Flowable):
    def __init__(self, w, h, fill):
        super().__init__()
        self.width = w
        self.height = h
        self.fill = fill

    def draw(self):
        self.canv.setFillColor(self.fill)
        self.canv.rect(0, 0, self.width, self.height, stroke=0, fill=1)


# ── Report ────────────────────────────────────────────────────────────────────
class PayRealityReport:

    def __init__(self, client_name: str = "Client", config: Optional[Dict] = None):
        self.client_name = client_name
        self.config = config or {}
        self.logger = logging.getLogger("PayReality.Report")
        # [RPT-1] Currency symbol is configurable; default is South African Rand.
        self.currency = self.config.get("currency_symbol", "R")

    # ── Money formatter ───────────────────────────────────────────────────────

    def _fmt(self, amount: float) -> str:
        """Format a monetary amount with the configured currency symbol."""
        if amount >= 0:
            return f"{self.currency} {amount:,.0f}"
        return f"-{self.currency} {abs(amount):,.0f}"

    # ── Style helpers ─────────────────────────────────────────────────────────

    def _para(self, text, size=10, color=INK, bold=False, align=TA_LEFT, leading=None):
        return Paragraph(text, ParagraphStyle(
            "p",
            fontName="Helvetica-Bold" if bold else "Helvetica",
            fontSize=size,
            textColor=color,
            alignment=align,
            leading=leading or (size * 1.35),
        ))

    def _section(self, text):
        return Paragraph(text, ParagraphStyle(
            "sec",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=NAVY,
            spaceBefore=18,
            spaceAfter=6,
        ))

    def _rule(self, color=GRAY_LT):
        return HRFlowable(width="100%", thickness=0.5, color=color,
                          spaceAfter=10, spaceBefore=4)

    def _sp(self, h=6):
        return Spacer(1, h)

    # ── Page decorators ───────────────────────────────────────────────────────

    def _on_page(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, H - 28*mm, W, 28*mm, stroke=0, fill=1)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(20*mm, H - 18*mm, "PayReality")
        canvas.setFont("Helvetica", 9)
        canvas.drawString(20*mm, H - 24*mm, "Independent Control Verification Report")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(W - 20*mm, H - 18*mm, self.client_name)
        canvas.drawRightString(W - 20*mm, H - 24*mm, datetime.now().strftime("%d %B %Y"))
        canvas.setFillColor(TEAL)
        canvas.rect(0, H - 29.5*mm, W, 1.5*mm, stroke=0, fill=1)
        canvas.setStrokeColor(GRAY_LT)
        canvas.setLineWidth(0.4)
        canvas.line(20*mm, 18*mm, W - 20*mm, 18*mm)
        canvas.setFillColor(GRAY)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(20*mm, 12*mm, "AI Securewatch  ·  sean@aisecurewatch.com  ·  Confidential")
        canvas.drawRightString(W - 20*mm, 12*mm, f"Page {doc.page}")
        canvas.restoreState()

    # ── KPI bar ───────────────────────────────────────────────────────────────

    def _kpi_table(self, results: Dict):
        ent = results["entropy_score"]
        ent_color = CORAL if ent >= 20 else AMBER if ent >= 10 else TEAL

        def cell(val, lbl, c):
            return [
                Paragraph(val, ParagraphStyle("v", fontName="Helvetica-Bold",
                    fontSize=22, textColor=c, alignment=TA_CENTER)),
                Paragraph(lbl, ParagraphStyle("l", fontName="Helvetica",
                    fontSize=8, textColor=GRAY, alignment=TA_CENTER)),
            ]

        val_row = [
            cell(f"{results['total_payments']:,}",      "Total Payments",  PURPLE)[0],
            cell(f"{results['exception_count']:,}",     "Exceptions",      CORAL)[0],
            cell(self._fmt(results["exception_spend"]), "Exception Spend", AMBER)[0],   # [RPT-1]
            cell(f"{ent:.1f}%",                         "Control Entropy", ent_color)[0],
            cell(f"{results['vendor_health']['health_score']}",
                                                        "Master Health",   TEAL)[0],
        ]
        lbl_row = [
            cell(f"{results['total_payments']:,}",      "Total Payments",  PURPLE)[1],
            cell(f"{results['exception_count']:,}",     "Exceptions",      CORAL)[1],
            cell(self._fmt(results["exception_spend"]), "Exception Spend", AMBER)[1],
            cell(f"{ent:.1f}%",                         "Control Entropy", ent_color)[1],
            cell(f"{results['vendor_health']['health_score']}",
                                                        "Master Health",   TEAL)[1],
        ]
        cw = (W - 40*mm) / 5
        t = Table([val_row, lbl_row], colWidths=[cw]*5)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), GRAY_LT),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("LINEAFTER",     (0, 0), (3, -1), 0.5, GRAY_LT),
        ]))
        return t

    # ── Match distribution table ──────────────────────────────────────────────

    def _match_table(self, match_stats: Dict, total: int):
        headers = ["Pass", "Strategy", "Count", "% of Total"]
        rows = [headers]
        order = ["exact", "normalized", "token_sort", "partial",
                 "levenshtein", "phonetic", "obfuscation", "none"]
        colors_map = {
            "exact": TEAL, "normalized": TEAL,
            "token_sort": PURPLE, "partial": PURPLE,
            "levenshtein": AMBER, "phonetic": AMBER,
            "obfuscation": CORAL, "none": CORAL,
        }
        labels = {
            "exact": "1 — Exact Match", "normalized": "2 — Normalised",
            "token_sort": "3 — Token Sort", "partial": "4 — Partial",
            "levenshtein": "5 — Levenshtein", "phonetic": "6 — Phonetic",
            "obfuscation": "7 — Obfuscation", "none": "— No Match",
        }
        for s in order:
            count = match_stats.get(s, 0)
            pct = (count / total * 100) if total > 0 else 0
            c = colors_map.get(s, GRAY)
            rows.append([
                Paragraph(labels.get(s, s), ParagraphStyle("mt", fontName="Helvetica-Bold",
                    fontSize=9, textColor=c)),
                Paragraph(STRATEGY_LABELS.get(s, s), ParagraphStyle("ms",
                    fontName="Helvetica", fontSize=9, textColor=INK)),
                Paragraph(f"{count:,}", ParagraphStyle("mc", fontName="Helvetica",
                    fontSize=9, textColor=INK, alignment=TA_RIGHT)),
                Paragraph(f"{pct:.1f}%", ParagraphStyle("mp", fontName="Helvetica",
                    fontSize=9, textColor=INK, alignment=TA_RIGHT)),
            ])
        cw_total = W - 40*mm
        t = Table(rows, colWidths=[cw_total*0.38, cw_total*0.32, cw_total*0.15, cw_total*0.15])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, 0), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LT]),
            ("GRID",  (0, 0), (-1, -1), 0.3, GRAY_LT),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ]))
        return t

    # ── Exception detail block ────────────────────────────────────────────────

    def _exception_block(self, ex: Dict, index: int):
        risk    = ex.get("risk_level", "Low")
        risk_c  = RISK_COLORS.get(risk, GRAY)
        conf    = ex.get("confidence_score", 0)
        amount  = ex.get("amount", 0)
        controls    = ex.get("control_ids", [])
        explanation = ex.get("explanation", "")
        strategy    = STRATEGY_LABELS.get(ex.get("match_strategy", "none"),
                                          ex.get("match_strategy", "—"))

        cw = W - 40*mm
        header = Table([[
            Paragraph(f"#{index}", ParagraphStyle("idx",
                fontName="Helvetica-Bold", fontSize=10, textColor=WHITE)),
            Paragraph(ex.get("payee_name", "Unknown")[:60],
                ParagraphStyle("en", fontName="Helvetica-Bold", fontSize=10, textColor=WHITE)),
            Paragraph(self._fmt(amount),                                        # [RPT-1]
                ParagraphStyle("amt", fontName="Helvetica-Bold", fontSize=10,
                    textColor=WHITE, alignment=TA_RIGHT)),
        ]], colWidths=[cw*0.07, cw*0.65, cw*0.28])
        header.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ]))

        conf_c = CORAL if conf >= 70 else AMBER if conf >= 40 else TEAL
        meta = Table([[
            Paragraph(f"Risk: <b>{risk}</b>", ParagraphStyle("r",
                fontName="Helvetica", fontSize=9, textColor=risk_c)),
            Paragraph(f"Confidence: <b>{conf}/100</b>", ParagraphStyle("c",
                fontName="Helvetica", fontSize=9, textColor=conf_c)),
            Paragraph(f"Match: <b>{strategy}</b>", ParagraphStyle("s",
                fontName="Helvetica", fontSize=9, textColor=PURPLE)),
            Paragraph(f"Controls: <b>{', '.join(controls)}</b>", ParagraphStyle("ct",
                fontName="Helvetica", fontSize=9, textColor=CORAL)),
        ]], colWidths=[cw*0.2, cw*0.22, cw*0.28, cw*0.3])
        meta.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), PURPLE_LT),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            ("LINEAFTER", (0, 0), (2, 0), 0.5, GRAY_LT),
        ]))

        expl = Table([[
            Paragraph("Why flagged:", ParagraphStyle("wl",
                fontName="Helvetica-Bold", fontSize=8, textColor=GRAY)),
            Paragraph(explanation, ParagraphStyle("ex",
                fontName="Helvetica", fontSize=9, textColor=INK, leading=13)),
        ]], colWidths=[cw*0.13, cw*0.87])
        expl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), WHITE),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("VALIGN",  (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRAY_LT),
        ]))

        return KeepTogether([header, meta, expl, self._sp(4)])

    # ── Main generate ─────────────────────────────────────────────────────────

    def generate_report(self, results: Dict, output_dir: str) -> str:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean = self.client_name.replace(" ", "_")
        filepath = os.path.join(output_dir, f"PayReality_{clean}_{ts}.pdf")

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            leftMargin=20*mm, rightMargin=20*mm,
            topMargin=34*mm, bottomMargin=24*mm,
        )

        story = []
        cw = W - 40*mm

        # ── Cover ──────────────────────────────────────────────────────────────
        story += [
            self._sp(20),
            self._para("PAYREALITY", 32, NAVY, bold=True, align=TA_CENTER),
            self._para("Independent Control Verification Report", 13, PURPLE, align=TA_CENTER),
            self._sp(8),
            self._para(self.client_name, 16, INK, bold=True, align=TA_CENTER),
            self._para(datetime.now().strftime("%d %B %Y"), 11, GRAY, align=TA_CENTER),
            self._sp(24),
            self._rule(PURPLE),
            self._sp(12),
        ]

        story.append(self._kpi_table(results))
        story.append(self._sp(20))

        meta_data = [
            ["Run ID",        results.get("run_id", "—")],
            ["Analysis Date", datetime.now().strftime("%Y-%m-%d %H:%M")],
            ["Client",        results.get("client_name", "—")],
            ["Threshold",     f"{results.get('threshold', 80)}%"],
            ["Vendor Master", f"{results.get('master_file_hash', '—')} (sha256)"],
            ["Payments File", f"{results.get('payments_file_hash', '—')} (sha256)"],
        ]
        mt = Table(meta_data, colWidths=[cw*0.28, cw*0.72])
        mt.setStyle(TableStyle([
            ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE",  (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), PURPLE),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [GRAY_LT, WHITE]),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, GRAY_LT),
        ]))
        story.append(mt)
        story.append(PageBreak())

        # ── Section 1: Control Entropy ──────────────────────────────────────────
        story.append(self._section("1. Control Entropy Score"))
        story.append(self._rule())

        ent = results["entropy_score"]
        ent_interp = (
            "CRITICAL — Over 20% of spend bypassed approved vendor controls."
            if ent >= 20 else
            "WARNING — Between 10–20% of spend requires investigation."
            if ent >= 10 else
            "ACCEPTABLE — Control failure rate is within normal bounds."
        )
        story += [
            self._para(
                "The Control Entropy Score measures the percentage of total spend "
                "that bypassed approved vendor controls after all seven matching passes."
            ),
            self._sp(8),
        ]

        ent_c   = CORAL if ent >= 20 else AMBER if ent >= 10 else TEAL
        ent_tbl = Table([[
            Paragraph(f"{ent:.2f}%", ParagraphStyle("ent",
                fontName="Helvetica-Bold", fontSize=36,
                textColor=ent_c, alignment=TA_CENTER)),
            Paragraph(ent_interp, ParagraphStyle("ei",
                fontName="Helvetica", fontSize=10, textColor=INK, leading=15)),
        ]], colWidths=[cw*0.25, cw*0.75])
        ent_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), GRAY_LT),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
            ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ]))
        story.append(ent_tbl)
        story.append(self._sp(14))

        # ── Section 2: 7-Pass Distribution ────────────────────────────────────
        story.append(self._section("2. 7-Pass Semantic Matching Distribution"))
        story.append(self._rule())
        story.append(self._para(
            "Each payment is processed through seven progressively sophisticated matching passes. "
            "The table below shows how payments were classified by the engine."
        ))
        story.append(self._sp(8))
        story.append(self._match_table(results["match_stats"], results["total_payments"]))
        story.append(self._sp(14))

        # ── Section 3: Vendor Master Health ───────────────────────────────────
        story.append(self._section("3. Vendor Master Health"))
        story.append(self._rule())
        health = results.get("vendor_health", {})
        hs   = health.get("health_score", 0)
        hs_c = TEAL if hs >= 80 else AMBER if hs >= 60 else CORAL
        hd = [
            ["Total Vendors",     f"{health.get('total_vendors', 0):,}"],
            ["Duplicate Records", f"{health.get('duplicate_records', 0):,}"],
            ["Blank Names",       f"{health.get('blank_names', 0):,}"],
            ["Short Names",       f"{health.get('short_names', 0):,}"],
            ["Health Score",      f"{hs} / 100 — {health.get('health_label', '—')}"],
        ]
        ht = Table(hd, colWidths=[cw*0.35, cw*0.65])
        ht.setStyle(TableStyle([
            ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 0), (0, -1), PURPLE),
            ("TEXTCOLOR", (1, 4), (1, 4),  hs_c),
            ("FONTNAME",  (1, 4), (1, 4),  "Helvetica-Bold"),
            ("FONTSIZE",  (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [GRAY_LT, WHITE]),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, GRAY_LT),
        ]))
        story.append(ht)
        story.append(PageBreak())

        # ── Section 4: Exception Detail ────────────────────────────────────────
        story.append(self._section("4. Exception Detail"))
        story.append(self._rule())
        story.append(self._para(
            f"The following {len(results['exceptions'])} exceptions are ranked by confidence score "
            f"(highest first). Each includes the control violated, matching pass that triggered "
            f"the flag, and a human-readable explanation."
        ))
        story.append(self._sp(10))

        max_ex = min(len(results["exceptions"]), 50)
        for i, ex in enumerate(results["exceptions"][:max_ex], 1):
            story.append(self._exception_block(ex, i))

        if len(results["exceptions"]) > max_ex:
            story.append(self._sp(6))
            story.append(self._para(
                f"… and {len(results['exceptions']) - max_ex} additional exceptions. "
                "Export JSON/CSV for full list.",
                color=GRAY, size=9
            ))

        # ── Section 5: Controls Summary ────────────────────────────────────────
        story.append(PageBreak())
        story.append(self._section("5. Control Violation Summary"))
        story.append(self._rule())
        story.append(self._para(
            "Count of exceptions per control type across this analysis run."
        ))
        story.append(self._sp(8))

        from collections import Counter
        ctrl_counter: Counter = Counter()
        for ex in results["exceptions"]:
            for c in ex.get("control_ids", []):
                ctrl_counter[c] += 1

        from src.core import CONTROL_TAXONOMY
        ctrl_rows = [["Control ID", "Control Name", "Category", "Severity", "Count"]]
        for cid, count in sorted(ctrl_counter.items(), key=lambda x: -x[1]):
            tax = CONTROL_TAXONOMY.get(cid, {})
            sev = tax.get("severity", "—")
            sev_c = CORAL if sev == "Critical" else AMBER if sev == "High" else TEAL
            ctrl_rows.append([
                Paragraph(cid, ParagraphStyle("ci", fontName="Helvetica-Bold",
                    fontSize=9, textColor=PURPLE)),
                Paragraph(tax.get("name", cid), ParagraphStyle("cn",
                    fontName="Helvetica", fontSize=9, textColor=INK)),
                Paragraph(tax.get("category", "—"), ParagraphStyle("cc",
                    fontName="Helvetica", fontSize=9, textColor=GRAY)),
                Paragraph(sev, ParagraphStyle("cs", fontName="Helvetica-Bold",
                    fontSize=9, textColor=sev_c)),
                Paragraph(f"{count:,}", ParagraphStyle("cnt",
                    fontName="Helvetica-Bold", fontSize=9, textColor=INK, alignment=TA_RIGHT)),
            ])

        ct = Table(ctrl_rows, colWidths=[cw*0.1, cw*0.32, cw*0.28, cw*0.16, cw*0.14])
        ct.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, 0), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LT]),
            ("GRID",  (0, 0), (-1, -1), 0.3, GRAY_LT),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
        ]))
        story.append(ct)
        story.append(self._sp(20))

        # ── Section 6: Recommendations ─────────────────────────────────────────
        story.append(self._section("6. Recommendations"))
        story.append(self._rule())

        recs = []
        if ent >= 20:
            recs.append(("Critical",
                "Immediate escalation required — Control Entropy >20% indicates systemic vendor "
                "control failure. Freeze new vendor onboarding and review all high-confidence "
                "exceptions with management."))
        if ent >= 10:
            recs.append(("High",
                "Investigate all High-risk exceptions flagged in Section 4. Prioritise items with "
                "Confidence Score ≥70 and OBC (Obfuscation) control violations."))
        if ctrl_counter.get("VDC", 0) > 0:
            recs.append(("Medium",
                f"{ctrl_counter['VDC']} duplicate vendor payment(s) detected. Reconcile against "
                "payment authorisation records and implement pre-payment duplicate checks."))
        if ctrl_counter.get("VTC", 0) > 0:
            recs.append(("Medium",
                f"{ctrl_counter['VTC']} new vendor(s) received high-value payments. Verify "
                "onboarding documentation and approval sign-off for each."))
        if health.get("health_score", 100) < 80:
            recs.append(("Low",
                f"Vendor Master Health Score is {health.get('health_score', 0)}/100. Perform a "
                "master data cleanse — remove duplicates, fill blank names, and deactivate "
                "dormant records."))
        if not recs:
            recs.append(("Low",
                "No critical findings. Continue quarterly validation to maintain continuous assurance."))

        sev_c_map = {"Critical": CORAL, "High": AMBER, "Medium": PURPLE, "Low": TEAL}
        for sev, text in recs:
            rc = sev_c_map.get(sev, GRAY)
            row = Table([[
                Paragraph(sev, ParagraphStyle("rs", fontName="Helvetica-Bold",
                    fontSize=9, textColor=rc)),
                Paragraph(text, ParagraphStyle("rt", fontName="Helvetica",
                    fontSize=9, textColor=INK, leading=13)),
            ]], colWidths=[cw*0.12, cw*0.88])
            row.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), GRAY_LT),
                ("TOPPADDING",    (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING",   (0, 0), (-1, -1), 10),
                ("LINEBELOW",     (0, 0), (-1, -1), 0.3, WHITE),
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(row)
            story.append(self._sp(4))

        # ── Closing ────────────────────────────────────────────────────────────
        story.append(self._sp(24))
        story.append(self._rule(PURPLE))
        story.append(self._para(
            '"If vendor controls have not been independently verified, '
            'their effectiveness cannot be assumed."',
            size=10, color=PURPLE, bold=False, align=TA_CENTER
        ))
        story.append(self._sp(4))
        story.append(self._para(
            "AI Securewatch  ·  sean@aisecurewatch.com  ·  payreality.aisecurewatch.com",
            size=8, color=GRAY, align=TA_CENTER
        ))

        doc.build(story, onFirstPage=self._on_page, onLaterPages=self._on_page)
        self.logger.info(f"Report generated: {filepath}")
        return filepath