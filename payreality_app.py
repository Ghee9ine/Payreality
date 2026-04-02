"""
PayReality Desktop Application — Phase 2
Complete UI with Control Mapping, Explainability, Confidence Scoring, Audit Trail
"""

import sys
import os
import threading
import json
import smtplib
import webbrowser
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Optional, List

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.core import PayRealityEngine, CONTROL_TAXONOMY, DataValidationError
from src.reporting import PayRealityReport

# ── Theme ──────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

C = {
    "navy":       "#1A1752",
    "purple":     "#534AB7",
    "purple_lt":  "#EEEDFE",
    "teal":       "#0F6E56",
    "teal_lt":    "#E1F5EE",
    "amber":      "#854F0B",
    "amber_lt":   "#FAEEDA",
    "coral":      "#993C1D",
    "coral_lt":   "#FAECE7",
    "white":      "#FFFFFF",
    "ink":        "#1A1A1A",
    "muted":      "#5F5E5A",
    "gray_lt":    "#F1EFE8",
    "border":     "#D3D1C7",
    "bg":         "#F8F7F4",
    "card":       "#FFFFFF",
    "success":    "#0F6E56",
    "danger":     "#993C1D",
    "warning":    "#854F0B",
}

RISK_COLORS = {"High": C["coral"], "Medium": C["amber"], "Low": C["teal"]}
STRATEGY_COLORS = {
    "exact": C["teal"], "normalized": C["teal"],
    "token_sort": C["purple"], "partial": C["purple"],
    "levenshtein": C["amber"], "phonetic": C["amber"],
    "none": C["coral"],
}

# ── Fonts ──────────────────────────────────────────────────────────────────────
def F(size=13, weight="normal"):
    return ctk.CTkFont(family="Inter" if sys.platform == "darwin" else "Segoe UI",
                       size=size, weight=weight)


# ═══════════════════════════════════════════════════════════════════════════════
# Main Application
# ═══════════════════════════════════════════════════════════════════════════════

class PayRealityApp:

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("PayReality — Independent Control Verification")
        self.root.geometry("1480x920")
        self.root.minsize(1200, 780)
        self.root.configure(fg_color=C["bg"])

        self.engine = PayRealityEngine()
        self.current_results: Optional[Dict] = None
        self.master_file: Optional[str] = None
        self.payments_file: Optional[str] = None
        self.output_dir: str = str(Path.home() / "Desktop" / "PayReality_Reports")
        self.email_var = ctk.BooleanVar(value=False)
        self._filter_risk = ctk.StringVar(value="All")
        self._filter_ctrl = ctk.StringVar(value="All")
        self._sort_by = ctk.StringVar(value="Confidence ↓")
        self._search_var = ctk.StringVar()

        os.makedirs(self.output_dir, exist_ok=True)

        self._build_ui()
        self._switch_tab("Dashboard")

    # ── Top-level layout ──────────────────────────────────────────────────────

    def _build_ui(self):
        # Sidebar
        self.sidebar = ctk.CTkFrame(self.root, width=220, fg_color=C["navy"],
                                     corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Main area
        self.main = ctk.CTkFrame(self.root, fg_color=C["bg"], corner_radius=0)
        self.main.pack(side="left", fill="both", expand=True)

        self._build_sidebar()
        self._build_topbar()
        self.content = ctk.CTkFrame(self.main, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=28, pady=(16, 24))

    def _build_sidebar(self):
        # Logo block
        logo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo.pack(fill="x", padx=20, pady=(28, 24))
        ctk.CTkLabel(logo, text="PayReality", font=F(20, "bold"),
                     text_color="#FFFFFF").pack(anchor="w")
        ctk.CTkLabel(logo, text="Phase 2 — ICV Platform", font=F(10),
                     text_color="#AFA9EC").pack(anchor="w", pady=(2, 0))

        # Divider
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#3C3489").pack(fill="x",
                     padx=16, pady=(0, 16))

        # Nav buttons
        self._nav_btns: Dict[str, ctk.CTkButton] = {}
        tabs = [
            ("Dashboard",   "⬡"),
            ("Exceptions",  "⚑"),
            ("History",     "◷"),
            ("Reports",     "⬒"),
            ("Settings",    "⚙"),
            ("Email",       "✉"),
        ]
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.pack(fill="x")
        for name, icon in tabs:
            btn = ctk.CTkButton(
                nav_frame, text=f"  {icon}  {name}",
                font=F(13), anchor="w",
                fg_color="transparent", text_color="#CECBF6",
                hover_color="#3C3489",
                height=44, corner_radius=8,
                command=lambda n=name: self._switch_tab(n),
            )
            btn.pack(fill="x", padx=12, pady=2)
            self._nav_btns[name] = btn

        # Bottom: tagline
        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(fill="both", expand=True)
        ctk.CTkLabel(
            self.sidebar,
            text='"Controls must be\nindependently verified."',
            font=F(9), text_color="#534AB7",
            justify="center",
        ).pack(pady=(0, 20), padx=16)

    def _build_topbar(self):
        bar = ctk.CTkFrame(self.main, height=52, fg_color=C["card"],
                           corner_radius=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        self._page_title = ctk.CTkLabel(bar, text="Dashboard",
                                         font=F(16, "bold"), text_color=C["ink"])
        self._page_title.pack(side="left", padx=28)

        self._run_id_label = ctk.CTkLabel(bar, text="", font=F(10),
                                           text_color=C["muted"])
        self._run_id_label.pack(side="right", padx=28)

        ctk.CTkFrame(self.main, height=1, fg_color=C["border"]).pack(fill="x")

    def _switch_tab(self, name: str):
        for n, btn in self._nav_btns.items():
            if n == name:
                btn.configure(fg_color=C["purple"], text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color="#CECBF6")
        self._page_title.configure(text=name)
        for w in self.content.winfo_children():
            w.destroy()
        {
            "Dashboard":  self._show_dashboard,
            "Exceptions": self._show_exceptions,
            "History":    self._show_history,
            "Reports":    self._show_reports,
            "Settings":   self._show_settings,
            "Email":      self._show_email,
        }[name]()

    # ══════════════════════════════════════════════════════════════════════════
    # DASHBOARD TAB
    # ══════════════════════════════════════════════════════════════════════════

    def _show_dashboard(self):
        # ── KPI row ────────────────────────────────────────────────────────────
        kpi_row = ctk.CTkFrame(self.content, fg_color="transparent")
        kpi_row.pack(fill="x", pady=(0, 20))
        self._kpi_cards = {}

        kpis = [
            ("exceptions",  "Exceptions",     "0",     C["coral"]),
            ("spend",       "Exception Spend","R 0",   C["amber"]),
            ("entropy",     "Control Entropy","0.0%",  C["purple"]),
            ("total",       "Total Payments", "0",     C["teal"]),
            ("confidence",  "Avg Confidence", "—",     C["navy"]),
        ]
        for key, label, default, color in kpis:
            card = ctk.CTkFrame(kpi_row, fg_color=C["card"], corner_radius=12)
            card.pack(side="left", fill="both", expand=True, padx=5)
            ctk.CTkLabel(card, text=label, font=F(10), text_color=C["muted"]).pack(
                anchor="w", padx=16, pady=(14, 2))
            val = ctk.CTkLabel(card, text=default, font=F(26, "bold"), text_color=color)
            val.pack(anchor="w", padx=16, pady=(0, 14))
            self._kpi_cards[key] = val

        # ── Bottom row: chart + upload panel ──────────────────────────────────
        bottom = ctk.CTkFrame(self.content, fg_color="transparent")
        bottom.pack(fill="both", expand=True)

        # Trend chart
        chart_card = ctk.CTkFrame(bottom, fg_color=C["card"], corner_radius=12)
        chart_card.pack(side="left", fill="both", expand=True, padx=(0, 12))

        ctk.CTkLabel(chart_card, text="Control Entropy Trend",
                     font=F(13, "bold"), text_color=C["ink"]).pack(
                     anchor="w", padx=18, pady=(16, 6))

        self._figure = plt.Figure(figsize=(6, 3.2), dpi=100, facecolor=C["card"])
        self._ax = self._figure.add_subplot(111)
        self._style_axes(self._ax)
        self._canvas = FigureCanvasTkAgg(self._figure, master=chart_card)
        self._canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(0, 16))
        self._refresh_chart()

        # Upload / run panel
        run_card = ctk.CTkFrame(bottom, fg_color=C["card"], corner_radius=12,
                                 width=340)
        run_card.pack(side="right", fill="y", padx=(12, 0))
        run_card.pack_propagate(False)

        ctk.CTkLabel(run_card, text="New Analysis", font=F(14, "bold"),
                     text_color=C["ink"]).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(run_card, text="Load files and run the 7-pass engine",
                     font=F(10), text_color=C["muted"]).pack(anchor="w", padx=20, pady=(0, 14))

        # Master file
        self._master_label = ctk.CTkLabel(run_card, text="Vendor Master — not selected",
                                           font=F(10), text_color=C["muted"])
        self._master_label.pack(anchor="w", padx=20, pady=(0, 4))
        ctk.CTkButton(run_card, text="Browse Vendor Master",
                      command=lambda: self._pick_file("master"),
                      height=34, font=F(11), fg_color=C["purple"],
                      hover_color=C["navy"], corner_radius=8).pack(
                      fill="x", padx=20, pady=(0, 12))

        # Payments file
        self._payments_label = ctk.CTkLabel(run_card, text="Payments — not selected",
                                             font=F(10), text_color=C["muted"])
        self._payments_label.pack(anchor="w", padx=20, pady=(0, 4))
        ctk.CTkButton(run_card, text="Browse Payments File",
                      command=lambda: self._pick_file("payments"),
                      height=34, font=F(11), fg_color=C["purple"],
                      hover_color=C["navy"], corner_radius=8).pack(
                      fill="x", padx=20, pady=(0, 12))

        # Threshold slider
        ctk.CTkLabel(run_card, text="Match Threshold", font=F(10, "bold"),
                     text_color=C["ink"]).pack(anchor="w", padx=20, pady=(4, 2))
        thresh_row = ctk.CTkFrame(run_card, fg_color="transparent")
        thresh_row.pack(fill="x", padx=20, pady=(0, 10))
        self._thresh_var = ctk.IntVar(value=80)
        self._thresh_label = ctk.CTkLabel(thresh_row, text="80%",
                                           font=F(11, "bold"), text_color=C["purple"])
        self._thresh_label.pack(side="right")
        ctk.CTkSlider(thresh_row, from_=50, to=95, number_of_steps=45,
                      variable=self._thresh_var,
                      command=lambda v: self._thresh_label.configure(
                          text=f"{int(float(v))}%"),
                      fg_color=C["purple_lt"], button_color=C["purple"],
                      progress_color=C["purple"]).pack(side="left", fill="x",
                      expand=True, padx=(0, 10))

        ctk.CTkCheckBox(run_card, text="Send email report",
                        variable=self.email_var, font=F(11),
                        checkbox_height=18, checkbox_width=18,
                        fg_color=C["purple"]).pack(anchor="w", padx=20, pady=(0, 8))

        self._run_btn = ctk.CTkButton(
            run_card, text="▶  Run Analysis",
            command=self._run_analysis,
            height=46, font=F(14, "bold"),
            fg_color=C["navy"], hover_color=C["purple"],
            corner_radius=10,
            state="disabled" if not (self.master_file and self.payments_file) else "normal",
        )
        self._run_btn.pack(fill="x", padx=20, pady=(4, 8))

        self._progress = ctk.CTkProgressBar(run_card, height=4,
                                             fg_color=C["gray_lt"],
                                             progress_color=C["purple"])
        self._progress.pack(fill="x", padx=20, pady=(0, 8))
        self._progress.set(0)

        self._log_box = ctk.CTkTextbox(run_card, height=110, font=F(9),
                                        corner_radius=8,
                                        fg_color=C["bg"], border_width=1,
                                        border_color=C["border"],
                                        text_color=C["muted"])
        self._log_box.pack(fill="x", padx=20, pady=(0, 18))

        if self.current_results:
            self._refresh_kpis(self.current_results)

    def _style_axes(self, ax):
        ax.set_facecolor(C["card"])
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_color(C["border"])
        ax.spines["bottom"].set_color(C["border"])
        ax.tick_params(colors=C["muted"], labelsize=8)

    def _refresh_chart(self):
        data = self.engine.get_entropy_trend()
        self._ax.clear()
        self._style_axes(self._ax)
        if data:
            scores = [d["entropy_score"] for d in data]
            x = range(len(scores))
            self._ax.plot(x, scores, marker="o", linewidth=2,
                          color=C["purple"], markersize=5,
                          markerfacecolor=C["card"], markeredgewidth=1.5)
            self._ax.fill_between(x, scores, alpha=0.12, color=C["purple"])
            self._ax.axhline(y=10, color=C["amber"], linestyle="--", alpha=0.4, linewidth=0.8)
            self._ax.axhline(y=20, color=C["coral"], linestyle="--", alpha=0.4, linewidth=0.8)
            self._ax.set_ylim(0, max(max(scores) * 1.2, 30))
            self._ax.set_xlabel("Run #", fontsize=8, color=C["muted"])
            self._ax.set_ylabel("Entropy %", fontsize=8, color=C["muted"])
        else:
            self._ax.text(0.5, 0.5, "No analyses yet", transform=self._ax.transAxes,
                          ha="center", va="center", fontsize=11, color=C["muted"])
            self._ax.set_xlim(0, 1); self._ax.set_ylim(0, 1)
        try:
            self._canvas.draw()
        except Exception:
            pass

    def _refresh_kpis(self, results: Dict):
        exc = results.get("exception_count", 0)
        spend = results.get("exception_spend", 0)
        entropy = results.get("entropy_score", 0.0)
        total = results.get("total_payments", 0)
        exceptions = results.get("exceptions", [])
        avg_conf = (sum(e.get("confidence_score", 0) for e in exceptions) /
                    len(exceptions)) if exceptions else 0

        self._kpi_cards["exceptions"].configure(text=f"{exc:,}")
        self._kpi_cards["spend"].configure(text=f"R {spend:,.0f}")
        self._kpi_cards["entropy"].configure(text=f"{entropy:.1f}%")
        self._kpi_cards["total"].configure(text=f"{total:,}")
        self._kpi_cards["confidence"].configure(text=f"{avg_conf:.0f}/100")

        if hasattr(self, "_run_id_label"):
            self._run_id_label.configure(
                text=f"Run ID: {results.get('run_id', '—')}  ·  "
                     f"{results.get('client_name', '')}  ·  "
                     f"{results.get('timestamp', '')[:16]}"
            )

    # ══════════════════════════════════════════════════════════════════════════
    # EXCEPTIONS TAB
    # ══════════════════════════════════════════════════════════════════════════

    def _show_exceptions(self):
        if not self.current_results:
            self._empty_state("No analysis run yet.\nRun an analysis from the Dashboard tab.")
            return

        exceptions = self.current_results.get("exceptions", [])

        # ── Filter / search bar ────────────────────────────────────────────────
        bar = ctk.CTkFrame(self.content, fg_color=C["card"], corner_radius=10)
        bar.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(bar, text="Filter:", font=F(11), text_color=C["muted"]).pack(
            side="left", padx=(14, 6), pady=10)

        ctk.CTkOptionMenu(bar, variable=self._filter_risk,
                          values=["All", "High", "Medium", "Low"],
                          width=110, height=30, font=F(11),
                          fg_color=C["purple_lt"], text_color=C["purple"],
                          button_color=C["purple"], button_hover_color=C["navy"],
                          command=lambda _: self._render_exceptions_table(exceptions)).pack(
                          side="left", padx=4, pady=10)

        ctrl_vals = ["All"] + sorted(CONTROL_TAXONOMY.keys())
        ctk.CTkOptionMenu(bar, variable=self._filter_ctrl,
                          values=ctrl_vals, width=110, height=30, font=F(11),
                          fg_color=C["purple_lt"], text_color=C["purple"],
                          button_color=C["purple"], button_hover_color=C["navy"],
                          command=lambda _: self._render_exceptions_table(exceptions)).pack(
                          side="left", padx=4, pady=10)

        ctk.CTkLabel(bar, text="Sort:", font=F(11), text_color=C["muted"]).pack(
            side="left", padx=(12, 6), pady=10)
        ctk.CTkOptionMenu(bar, variable=self._sort_by,
                          values=["Confidence ↓", "Risk Score ↓", "Amount ↓", "Alphabetical"],
                          width=150, height=30, font=F(11),
                          fg_color=C["purple_lt"], text_color=C["purple"],
                          button_color=C["purple"], button_hover_color=C["navy"],
                          command=lambda _: self._render_exceptions_table(exceptions)).pack(
                          side="left", padx=4, pady=10)

        ctk.CTkLabel(bar, text="Search:", font=F(11), text_color=C["muted"]).pack(
            side="left", padx=(12, 4), pady=10)
        search = ctk.CTkEntry(bar, textvariable=self._search_var,
                              placeholder_text="Payee name…",
                              width=180, height=30, font=F(11),
                              fg_color=C["bg"], border_color=C["border"],
                              text_color=C["ink"])
        search.pack(side="left", padx=4, pady=10)
        self._search_var.trace_add("write", lambda *_: self._render_exceptions_table(exceptions))

        # Export buttons
        ctk.CTkButton(bar, text="Export JSON", width=90, height=30,
                      font=F(11), fg_color=C["teal"], hover_color=C["navy"],
                      corner_radius=6,
                      command=self._export_json).pack(side="right", padx=4, pady=10)
        ctk.CTkButton(bar, text="Export CSV", width=90, height=30,
                      font=F(11), fg_color=C["teal"], hover_color=C["navy"],
                      corner_radius=6,
                      command=self._export_csv).pack(side="right", padx=4, pady=10)

        ctk.CTkLabel(bar, text=f"{len(exceptions)} exceptions",
                     font=F(11, "bold"), text_color=C["coral"]).pack(
                     side="right", padx=12, pady=10)

        # ── Table container ────────────────────────────────────────────────────
        self._exc_container = ctk.CTkFrame(self.content, fg_color="transparent")
        self._exc_container.pack(fill="both", expand=True)
        self._render_exceptions_table(exceptions)

    def _apply_filters(self, exceptions: List[Dict]) -> List[Dict]:
        risk_f = self._filter_risk.get()
        ctrl_f = self._filter_ctrl.get()
        search = self._search_var.get().lower()
        sort = self._sort_by.get()

        out = exceptions
        if risk_f != "All":
            out = [e for e in out if e.get("risk_level") == risk_f]
        if ctrl_f != "All":
            out = [e for e in out if ctrl_f in e.get("control_ids", [])]
        if search:
            out = [e for e in out if search in e.get("payee_name", "").lower()]

        key_fn = {
            "Confidence ↓": lambda e: -e.get("confidence_score", 0),
            "Risk Score ↓": lambda e: -e.get("risk_score", 0),
            "Amount ↓":     lambda e: -e.get("amount", 0),
            "Alphabetical": lambda e: e.get("payee_name", "").lower(),
        }.get(sort, lambda e: -e.get("confidence_score", 0))
        return sorted(out, key=key_fn)

    def _render_exceptions_table(self, exceptions: List[Dict]):
        for w in self._exc_container.winfo_children():
            w.destroy()

        filtered = self._apply_filters(exceptions)

        # Column headers
        cols = [
            ("#",           40),
            ("Payee Name",  220),
            ("Amount",      100),
            ("Controls",    120),
            ("Confidence",  90),
            ("Risk",        70),
            ("Strategy",    100),
            ("Explanation", 0),   # expands
        ]
        hdr = ctk.CTkFrame(self._exc_container, fg_color=C["navy"],
                           corner_radius=8, height=36)
        hdr.pack(fill="x", pady=(0, 2))
        hdr.pack_propagate(False)
        for title, w in cols:
            ctk.CTkLabel(hdr, text=title, font=F(10, "bold"),
                         text_color="#AFA9EC",
                         width=w if w else 1).pack(
                         side="left",
                         padx=(12 if title == "#" else 6, 4),
                         pady=0, fill="x",
                         expand=(w == 0))

        # Scrollable rows
        scroll = ctk.CTkScrollableFrame(self._exc_container,
                                         fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        if not filtered:
            ctk.CTkLabel(scroll, text="No exceptions match the current filters.",
                         font=F(12), text_color=C["muted"]).pack(pady=40)
            return

        for i, ex in enumerate(filtered):
            self._exc_row(scroll, i + 1, ex)

    def _exc_row(self, parent, index: int, ex: Dict):
        risk = ex.get("risk_level", "Low")
        conf = ex.get("confidence_score", 0)
        risk_c = RISK_COLORS.get(risk, C["muted"])
        conf_c = C["coral"] if conf >= 70 else C["amber"] if conf >= 40 else C["teal"]
        strategy = ex.get("match_strategy", "none")
        strat_c = STRATEGY_COLORS.get(strategy.split("_")[0] if "_" in strategy else strategy,
                                       C["muted"])
        strat_label = {
            "exact": "Exact", "normalized": "Normalised",
            "token_sort": "Token Sort", "partial": "Partial",
            "levenshtein": "Levenshtein", "phonetic": "Phonetic",
            "none": "No Match",
        }.get(strategy.split("_")[0] if strategy.startswith("obfuscation") else strategy,
              "Obfuscation" if strategy.startswith("obfuscation") else strategy)

        bg = C["card"] if index % 2 == 1 else C["bg"]

        row = ctk.CTkFrame(parent, fg_color=bg, corner_radius=0, height=42)
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)

        def add(text, width, color=C["ink"], bold=False, expand=False):
            ctk.CTkLabel(row, text=text, font=F(10, "bold" if bold else "normal"),
                         text_color=color, width=width,
                         anchor="w").pack(
                         side="left",
                         padx=(12 if expand is False and width == 40 else 6, 4),
                         fill="x" if expand else "none",
                         expand=expand)

        add(f"{index}", 40, C["muted"])
        add(ex.get("payee_name", "")[:34], 220, C["ink"], bold=True)
        add(f"R {ex.get('amount', 0):,.0f}", 100, C["amber"])
        add(", ".join(ex.get("control_ids", [])), 120, C["purple"], bold=True)
        add(f"{conf}/100", 90, conf_c, bold=True)
        add(risk, 70, risk_c, bold=True)
        add(strat_label, 100, strat_c)
        # Explanation (truncated, expandable)
        expl = ex.get("explanation", "")[:120] + ("…" if len(ex.get("explanation", "")) > 120 else "")
        ctk.CTkLabel(row, text=expl, font=F(9), text_color=C["muted"],
                     anchor="w").pack(side="left", fill="x", expand=True, padx=(6, 12))

        # Click to expand detail
        row.bind("<Button-1>", lambda e, ex=ex: self._show_exception_detail(ex))
        for child in row.winfo_children():
            child.bind("<Button-1>", lambda e, ex=ex: self._show_exception_detail(ex))

    def _show_exception_detail(self, ex: Dict):
        """Modal-style detail panel for a single exception."""
        win = ctk.CTkToplevel(self.root)
        win.title(f"Exception Detail — {ex.get('payee_name', '')}")
        win.geometry("700x560")
        win.configure(fg_color=C["bg"])
        win.grab_set()

        scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=24, pady=20)

        risk = ex.get("risk_level", "Low")
        conf = ex.get("confidence_score", 0)

        # Header
        h = ctk.CTkFrame(scroll, fg_color=C["navy"], corner_radius=10)
        h.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(h, text=ex.get("payee_name", ""),
                     font=F(16, "bold"), text_color="#FFFFFF").pack(
                     anchor="w", padx=18, pady=(14, 4))
        ctk.CTkLabel(h, text=f"R {ex.get('amount', 0):,.2f}  ·  {ex.get('payment_date', '—')[:10]}",
                     font=F(11), text_color="#AFA9EC").pack(anchor="w", padx=18, pady=(0, 14))

        def section(title, color=C["purple"]):
            ctk.CTkLabel(scroll, text=title, font=F(12, "bold"),
                         text_color=color).pack(anchor="w", pady=(14, 4))
            ctk.CTkFrame(scroll, height=1, fg_color=C["border"]).pack(fill="x", pady=(0, 8))

        def field(label, value, val_color=C["ink"]):
            row = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label, font=F(10), text_color=C["muted"],
                         width=160, anchor="w").pack(side="left", padx=12, pady=7)
            ctk.CTkLabel(row, text=str(value), font=F(10, "bold"),
                         text_color=val_color, anchor="w").pack(
                         side="left", padx=8, pady=7, fill="x", expand=True)

        section("Control Assessment")
        risk_c = RISK_COLORS.get(risk, C["muted"])
        conf_c = C["coral"] if conf >= 70 else C["amber"] if conf >= 40 else C["teal"]
        field("Risk Level", risk, risk_c)
        field("Confidence Score", f"{conf} / 100", conf_c)
        field("Controls Violated", ", ".join(ex.get("control_ids", [])), C["purple"])
        field("Control Names", "\n".join(ex.get("control_names", [])), C["ink"])

        section("Matching Detail")
        field("Match Strategy", ex.get("match_strategy", "—"))
        field("Match Score", f"{ex.get('match_score', 0)}%")
        field("Matched Vendor", ex.get("matched_vendor") or "No match found",
              C["teal"] if ex.get("matched_vendor") else C["coral"])
        field("Passes Tried", " → ".join(ex.get("passes_tried", [])))

        section("Explanation")
        expl_box = ctk.CTkTextbox(scroll, height=100, font=F(10),
                                   fg_color=C["card"], border_width=1,
                                   border_color=C["border"], text_color=C["ink"],
                                   corner_radius=8)
        expl_box.pack(fill="x", pady=(0, 8))
        expl_box.insert("1.0", ex.get("explanation", "—"))
        expl_box.configure(state="disabled")

        section("Vendor Timeline")
        field("First Seen", ex.get("first_seen") or "—")
        field("Last Seen", ex.get("last_seen") or "—")
        field("Payment Count", f"{ex.get('payment_count', 0):,}")
        field("Tenure", f"{ex.get('tenure_days', 0)} days")
        field("Total Vendor Spend", f"R {ex.get('total_vendor_spend', 0):,.2f}")

        if ex.get("risk_reasons"):
            section("Risk Factors")
            for r in ex["risk_reasons"]:
                ctk.CTkLabel(scroll, text=f"  • {r}", font=F(10),
                             text_color=C["ink"]).pack(anchor="w", pady=1)

        ctk.CTkButton(win, text="Close", command=win.destroy,
                      fg_color=C["purple"], hover_color=C["navy"],
                      height=36, corner_radius=8, font=F(12)).pack(
                      pady=14, padx=24)

    # ══════════════════════════════════════════════════════════════════════════
    # HISTORY TAB
    # ══════════════════════════════════════════════════════════════════════════

    def _show_history(self):
        # Header row
        top = ctk.CTkFrame(self.content, fg_color="transparent")
        top.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(top, text="Analysis History", font=F(15, "bold"),
                     text_color=C["ink"]).pack(side="left")
        ctk.CTkButton(top, text="Export Excel", width=110, height=32,
                      font=F(11), fg_color=C["teal"], hover_color=C["navy"],
                      corner_radius=8, command=self._export_history_excel).pack(
                      side="right")

        card = ctk.CTkFrame(self.content, fg_color=C["card"], corner_radius=12)
        card.pack(fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("PR.Treeview",
                         background=C["card"],
                         foreground=C["ink"],
                         rowheight=34,
                         fieldbackground=C["card"],
                         borderwidth=0,
                         font=("Segoe UI", 10))
        style.configure("PR.Treeview.Heading",
                         background=C["navy"],
                         foreground="#FFFFFF",
                         font=("Segoe UI", 10, "bold"),
                         relief="flat")
        style.map("PR.Treeview",
                  background=[("selected", C["purple_lt"])],
                  foreground=[("selected", C["ink"])])

        cols = ("Date", "Client", "Payments", "Exceptions", "Entropy",
                "Spend", "Duplicates", "Run ID")
        self._hist_tree = ttk.Treeview(card, columns=cols,
                                        show="headings", style="PR.Treeview",
                                        height=18)
        widths = [150, 160, 90, 90, 90, 120, 90, 100]
        for col, w in zip(cols, widths):
            self._hist_tree.heading(col, text=col)
            self._hist_tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(card, orient="vertical",
                            command=self._hist_tree.yview)
        self._hist_tree.configure(yscrollcommand=vsb.set)
        self._hist_tree.pack(side="left", fill="both", expand=True,
                              padx=(16, 0), pady=16)
        vsb.pack(side="right", fill="y", pady=16, padx=(0, 8))

        self._load_history_rows()

    def _load_history_rows(self):
        if not hasattr(self, "_hist_tree"):
            return
        for item in self._hist_tree.get_children():
            self._hist_tree.delete(item)
        for row in self.engine.get_history():
            self._hist_tree.insert("", "end", values=(
                row["timestamp"][:16],
                row["client_name"] or "—",
                f"{row['total_payments']:,}",
                f"{row['exception_count']:,}",
                f"{row['entropy_score']:.1f}%",
                f"R {row['exception_spend']:,.0f}",
                f"{row['duplicate_count'] or 0}",
                row["run_id"],
            ))

    # ══════════════════════════════════════════════════════════════════════════
    # REPORTS TAB
    # ══════════════════════════════════════════════════════════════════════════

    def _show_reports(self):
        top = ctk.CTkFrame(self.content, fg_color="transparent")
        top.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(top, text="Saved Reports", font=F(15, "bold"),
                     text_color=C["ink"]).pack(side="left")
        ctk.CTkButton(top, text="Open Folder", width=110, height=32,
                      font=F(11), fg_color=C["purple"], hover_color=C["navy"],
                      corner_radius=8,
                      command=lambda: webbrowser.open(self.output_dir)).pack(side="right")

        scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        rows = self.engine.get_history()
        reports = [r for r in rows if r.get("report_path") and
                   os.path.exists(r["report_path"])]

        if not reports:
            self._empty_state("No reports saved yet.", parent=scroll)
            return

        for r in reports:
            card = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=10,
                                 height=60)
            card.pack(fill="x", pady=4)
            card.pack_propagate(False)

            ctk.CTkLabel(card, text=r["timestamp"][:16],
                         font=F(10), text_color=C["muted"],
                         width=140).pack(side="left", padx=(14, 8), pady=12)
            ctk.CTkLabel(card, text=r["client_name"] or "—",
                         font=F(11, "bold"), text_color=C["ink"]).pack(
                         side="left", padx=4, pady=12)
            ctk.CTkLabel(card,
                         text=f"{r['exception_count']} exceptions  ·  {r['entropy_score']:.1f}% entropy",
                         font=F(10), text_color=C["muted"]).pack(
                         side="left", padx=12, pady=12)
            ctk.CTkButton(card, text="Open PDF", width=80, height=30,
                          font=F(10), fg_color=C["purple"],
                          hover_color=C["navy"], corner_radius=6,
                          command=lambda p=r["report_path"]: os.startfile(p)
                          if sys.platform == "win32"
                          else webbrowser.open(f"file://{p}")).pack(
                          side="right", padx=14)

    # ══════════════════════════════════════════════════════════════════════════
    # SETTINGS TAB
    # ══════════════════════════════════════════════════════════════════════════

    def _show_settings(self):
        scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        def section(title):
            ctk.CTkLabel(scroll, text=title, font=F(14, "bold"),
                         text_color=C["ink"]).pack(anchor="w", pady=(18, 4))
            ctk.CTkFrame(scroll, height=1, fg_color=C["border"]).pack(
                fill="x", pady=(0, 12))

        def setting_row(label, desc, widget_factory):
            row = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=8)
            row.pack(fill="x", pady=4)
            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", fill="both", expand=True, padx=16, pady=10)
            ctk.CTkLabel(left, text=label, font=F(11, "bold"),
                         text_color=C["ink"]).pack(anchor="w")
            ctk.CTkLabel(left, text=desc, font=F(9),
                         text_color=C["muted"]).pack(anchor="w", pady=(2, 0))
            widget_factory(row)

        section("Matching Engine")

        self._cfg_threshold = ctk.IntVar(value=80)
        self._cfg_phonetic   = ctk.BooleanVar(value=True)
        self._cfg_obfuscation = ctk.BooleanVar(value=True)

        def thresh_widget(parent):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(side="right", padx=16)
            lbl = ctk.CTkLabel(f, text=f"{self._cfg_threshold.get()}%",
                               font=F(11, "bold"), text_color=C["purple"], width=40)
            lbl.pack(side="right")
            ctk.CTkSlider(f, from_=50, to=95, number_of_steps=45,
                          variable=self._cfg_threshold,
                          command=lambda v: lbl.configure(text=f"{int(float(v))}%"),
                          width=160, fg_color=C["purple_lt"],
                          button_color=C["purple"],
                          progress_color=C["purple"]).pack(side="left")

        setting_row("Default Match Threshold",
                    "Minimum similarity score (50–95%) to consider a vendor matched",
                    thresh_widget)

        def toggle(var):
            return lambda parent: ctk.CTkSwitch(
                parent, text="", variable=var, width=50,
                fg_color=C["border"], progress_color=C["purple"],
                button_color=C["purple"]).pack(side="right", padx=16, pady=12)

        setting_row("Enable Phonetic Matching",
                    "Pass 6 — catch Smith/Smyth-style name variations",
                    toggle(self._cfg_phonetic))
        setting_row("Enable Obfuscation Detection",
                    "Pass 7 — detect dot-spacing, leetspeak, homoglyphs",
                    toggle(self._cfg_obfuscation))

        section("Output")

        self._cfg_output_dir = ctk.StringVar(value=self.output_dir)

        def output_dir_widget(parent):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(side="right", padx=16, pady=8)
            ctk.CTkEntry(f, textvariable=self._cfg_output_dir,
                         width=240, height=30, font=F(10),
                         fg_color=C["bg"], border_color=C["border"],
                         text_color=C["ink"]).pack(side="left", padx=(0, 6))
            ctk.CTkButton(f, text="Browse", width=70, height=30,
                          font=F(10), fg_color=C["purple"],
                          hover_color=C["navy"], corner_radius=6,
                          command=self._pick_output_dir).pack(side="left")

        setting_row("Report Output Directory",
                    "Where PDF, JSON, and CSV exports are saved",
                    output_dir_widget)

        section("Control Taxonomy")
        for cid, tax in CONTROL_TAXONOMY.items():
            card = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=8)
            card.pack(fill="x", pady=3)
            sev_c = {"Critical": C["coral"], "High": C["amber"],
                     "Medium": C["purple"], "Low": C["teal"]}.get(
                     tax["severity"], C["muted"])
            ctk.CTkLabel(card, text=cid, font=F(10, "bold"),
                         text_color=C["purple"], width=50).pack(
                         side="left", padx=14, pady=8)
            ctk.CTkLabel(card, text=tax["name"], font=F(10, "bold"),
                         text_color=C["ink"], width=220).pack(
                         side="left", padx=4)
            ctk.CTkLabel(card, text=tax["category"], font=F(9),
                         text_color=C["muted"], width=180).pack(side="left", padx=4)
            ctk.CTkLabel(card, text=tax["severity"], font=F(9, "bold"),
                         text_color=sev_c).pack(side="left", padx=4)

        ctk.CTkButton(scroll, text="Save Settings", height=40,
                      font=F(13, "bold"), fg_color=C["navy"],
                      hover_color=C["purple"], corner_radius=10,
                      command=self._save_settings).pack(
                      fill="x", pady=(20, 8))

    def _pick_output_dir(self):
        d = filedialog.askdirectory(title="Select Output Directory")
        if d:
            self.output_dir = d
            if hasattr(self, "_cfg_output_dir"):
                self._cfg_output_dir.set(d)

    def _save_settings(self):
        self.output_dir = self._cfg_output_dir.get()
        os.makedirs(self.output_dir, exist_ok=True)
        messagebox.showinfo("Saved", "Settings saved successfully.")

    # ══════════════════════════════════════════════════════════════════════════
    # EMAIL TAB
    # ══════════════════════════════════════════════════════════════════════════

    def _show_email(self):
        scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        card = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=12)
        card.pack(fill="x", pady=(0, 16), padx=0)

        ctk.CTkLabel(card, text="Email Configuration",
                     font=F(15, "bold"), text_color=C["ink"]).pack(
                     anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(card, text="Automatically deliver PDF reports after each analysis run.",
                     font=F(10), text_color=C["muted"]).pack(anchor="w", padx=24,
                     pady=(0, 16))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=24, pady=(0, 20))
        form.grid_columnconfigure(1, weight=1)

        fields = [
            ("SMTP Server",    "smtp.gmail.com",          "smtp",    False),
            ("Port",           "587",                     "port",    False),
            ("Email Address",  "sender@company.com",      "user",    False),
            ("Password",       "",                        "pass",    True),
            ("Recipients",     "audit@company.com, ...",  "recv",    False),
        ]
        self._email_entries: Dict[str, ctk.CTkEntry] = {}
        for i, (lbl, ph, key, secret) in enumerate(fields):
            ctk.CTkLabel(form, text=lbl, font=F(11, "bold"),
                         text_color=C["ink"],
                         anchor="e", width=130).grid(row=i, column=0,
                         padx=(0, 12), pady=6, sticky="e")
            e = ctk.CTkEntry(form, placeholder_text=ph,
                             height=34, font=F(11),
                             fg_color=C["bg"], border_color=C["border"],
                             text_color=C["ink"],
                             show="•" if secret else "")
            e.grid(row=i, column=1, pady=6, sticky="ew")
            self._email_entries[key] = e

        self._load_email()

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(0, 20))
        ctk.CTkButton(row, text="Save Settings", width=140, height=36,
                      font=F(12), fg_color=C["navy"], hover_color=C["purple"],
                      corner_radius=8, command=self._save_email).pack(
                      side="left", padx=(0, 10))
        ctk.CTkButton(row, text="Send Test Email", width=140, height=36,
                      font=F(12), fg_color=C["teal"], hover_color=C["navy"],
                      corner_radius=8, command=self._test_email).pack(side="left")

        # Template preview
        preview = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=12)
        preview.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(preview, text="Email Template Preview",
                     font=F(13, "bold"), text_color=C["ink"]).pack(
                     anchor="w", padx=24, pady=(16, 8))
        tpl = ctk.CTkTextbox(preview, height=160, font=F(10),
                              fg_color=C["bg"], border_width=1,
                              border_color=C["border"], text_color=C["muted"],
                              corner_radius=8)
        tpl.pack(fill="x", padx=24, pady=(0, 16))
        tpl.insert("1.0", (
            "Subject: PayReality Report — {client_name}\n\n"
            "PayReality Control Verification Report\n"
            "Client:            {client_name}\n"
            "Date:              {date}\n\n"
            "Summary:\n"
            "  Control Entropy:   {entropy:.1f}%\n"
            "  Total Payments:    {total_payments:,}\n"
            "  Exceptions Found:  {exception_count:,}\n"
            "  Exception Spend:   R {exception_spend:,.2f}\n\n"
            "Full PDF report attached.\n\n"
            "AI Securewatch — sean@aisecurewatch.com"
        ))
        tpl.configure(state="disabled")

    def _load_email(self):
        try:
            with self.engine._db() as conn:
                row = conn.execute(
                    "SELECT smtp_server, smtp_port, email_user, "
                    "email_password, recipient_list FROM email_config LIMIT 1"
                ).fetchone()
            if row and row[0]:
                vals = {"smtp": row[0], "port": str(row[1]),
                        "user": row[2], "pass": row[3], "recv": row[4]}
                for k, v in vals.items():
                    e = self._email_entries.get(k)
                    if e:
                        e.delete(0, "end")
                        e.insert(0, v or "")
        except Exception:
            pass

    def _save_email(self):
        smtp   = self._email_entries["smtp"].get()
        port   = self._email_entries["port"].get()
        user   = self._email_entries["user"].get()
        pw     = self._email_entries["pass"].get()
        recv   = self._email_entries["recv"].get()
        try:
            with self.engine._db() as conn:
                conn.execute("DELETE FROM email_config")
                conn.execute(
                    "INSERT INTO email_config (smtp_server, smtp_port, email_user, "
                    "email_password, recipient_list) VALUES (?,?,?,?,?)",
                    (smtp, int(port or 587), user, pw, recv)
                )
            messagebox.showinfo("Saved", "Email settings saved.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _test_email(self):
        self._save_email()
        self._send_email(None, "Test", {
            "entropy_score": 0, "total_payments": 0,
            "exception_count": 0, "exception_spend": 0,
        }, is_test=True)

    # ══════════════════════════════════════════════════════════════════════════
    # FILE PICKER
    # ══════════════════════════════════════════════════════════════════════════

    def _pick_file(self, kind: str):
        path = filedialog.askopenfilename(
            title=f"Select {'Vendor Master' if kind == 'master' else 'Payments File'}",
            filetypes=[("CSV / Excel", "*.csv *.xlsx *.xls"), ("All files", "*.*")],
        )
        if not path:
            return
        name = os.path.basename(path)
        if kind == "master":
            self.master_file = path
            if hasattr(self, "_master_label"):
                self._master_label.configure(
                    text=f"✓ {name}", text_color=C["teal"])
        else:
            self.payments_file = path
            if hasattr(self, "_payments_label"):
                self._payments_label.configure(
                    text=f"✓ {name}", text_color=C["teal"])

        if self.master_file and self.payments_file:
            if hasattr(self, "_run_btn"):
                self._run_btn.configure(state="normal")

    # ══════════════════════════════════════════════════════════════════════════
    # ANALYSIS RUNNER
    # ══════════════════════════════════════════════════════════════════════════

    def _run_analysis(self):
        if not self.master_file or not self.payments_file:
            messagebox.showwarning("Files required",
                                   "Please select both Vendor Master and Payments files.")
            return

        dlg = ctk.CTkInputDialog(text="Enter client / engagement name:",
                                  title="Client Name")
        client = dlg.get_input()
        if client is None:
            return
        client = client.strip() or "Client"

        self._run_btn.configure(state="disabled", text="⏳  Running…")
        self._progress.set(0)
        if hasattr(self, "_log_box"):
            self._log_box.delete("1.0", "end")

        def thread():
            try:
                threshold = int(self._thresh_var.get()) if hasattr(self, "_thresh_var") else 80

                def progress(pct, msg):
                    self._progress.set(pct)
                    self._log(msg)
                    self.root.update_idletasks()

                results = self.engine.run_analysis(
                    self.master_file,
                    self.payments_file,
                    threshold=threshold,
                    client_name=client,
                    progress_callback=progress,
                )

                self.current_results = results
                self._log(f"✓ {results['exception_count']:,} exceptions found")
                self._log(f"✓ Entropy: {results['entropy_score']:.2f}%")
                self._log(f"✓ Run ID: {results['run_id']}")

                # Generate report
                self._log("Generating PDF report…")
                reporter = PayRealityReport(client_name=client)
                report_path = reporter.generate_report(results, self.output_dir)
                self._log(f"✓ Report: {os.path.basename(report_path)}")

                # Save to history
                self.engine.save_run(
                    results["run_id"], client,
                    results["master_file_hash"],
                    results["payments_file_hash"],
                    threshold, results, report_path,
                )

                # Email
                if self.email_var.get():
                    self._send_email(report_path, client, results)

                self._progress.set(1.0)

                # Refresh UI on main thread
                self.root.after(0, lambda: self._on_analysis_complete(results))

            except DataValidationError as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "File Format Error",
                    f"{e}\n\nVendor Master needs: vendor_name\n"
                    "Payments need: payee_name, amount"
                ))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, lambda: self._run_btn.configure(
                    state="normal", text="▶  Run Analysis"))

        threading.Thread(target=thread, daemon=True).start()

    def _on_analysis_complete(self, results: Dict):
        self._refresh_kpis(results)
        self._refresh_chart()

        exc = results["exception_count"]
        high = sum(1 for e in results["exceptions"] if e["risk_level"] == "High")
        messagebox.showinfo(
            "Analysis Complete",
            f"Run ID: {results['run_id']}\n\n"
            f"Control Entropy: {results['entropy_score']:.2f}%\n"
            f"Exceptions: {exc:,}  ({high} High-risk)\n"
            f"Exception Spend: R {results['exception_spend']:,.2f}\n\n"
            "Go to the Exceptions tab to review findings.",
        )

    def _log(self, msg: str):
        if hasattr(self, "_log_box"):
            self._log_box.insert("end", f"{msg}\n")
            self._log_box.see("end")

    # ══════════════════════════════════════════════════════════════════════════
    # EXPORTS
    # ══════════════════════════════════════════════════════════════════════════

    def _export_json(self):
        if not self.current_results:
            messagebox.showwarning("No data", "Run an analysis first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=f"payreality_{self.current_results['run_id']}.json",
            filetypes=[("JSON", "*.json")],
        )
        if path:
            self.engine.export_json(self.current_results, path)
            messagebox.showinfo("Exported", f"JSON saved to:\n{path}")

    def _export_csv(self):
        if not self.current_results:
            messagebox.showwarning("No data", "Run an analysis first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"payreality_{self.current_results['run_id']}.csv",
            filetypes=[("CSV", "*.csv")],
        )
        if path:
            self.engine.export_csv(self.current_results, path)
            messagebox.showinfo("Exported", f"CSV saved to:\n{path}")

    def _export_history_excel(self):
        import pandas as pd
        rows = self.engine.get_history()
        if not rows:
            messagebox.showwarning("No Data", "No history to export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=f"payreality_history_{datetime.now().strftime('%Y%m%d')}.xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if path:
            pd.DataFrame(rows).to_excel(path, index=False)
            messagebox.showinfo("Exported", f"Saved to:\n{path}")

    # ══════════════════════════════════════════════════════════════════════════
    # EMAIL
    # ══════════════════════════════════════════════════════════════════════════

    def _send_email(self, report_path: Optional[str], client: str,
                    results: Dict, is_test: bool = False):
        try:
            with self.engine._db() as conn:
                cfg = conn.execute(
                    "SELECT smtp_server, smtp_port, email_user, "
                    "email_password, recipient_list FROM email_config LIMIT 1"
                ).fetchone()
            if not cfg or not cfg[0]:
                self._log("Email not configured.")
                return
            smtp, port, user, pw, recv_str = cfg
            recipients = [r.strip() for r in (recv_str or "").split(",") if r.strip()]
            if not recipients:
                self._log("No recipients configured.")
                return

            subj = ("PayReality — Test Email" if is_test
                    else f"PayReality Report — {client}")
            body = (
                f"PayReality Control Verification Report\n"
                f"Client:          {client}\n"
                f"Date:            {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                f"Control Entropy:  {results.get('entropy_score', 0):.1f}%\n"
                f"Total Payments:   {results.get('total_payments', 0):,}\n"
                f"Exceptions:       {results.get('exception_count', 0):,}\n"
                f"Exception Spend:  R {results.get('exception_spend', 0):,.2f}\n\n"
                f"{'[TEST EMAIL — no report attached]' if is_test else 'PDF report attached.'}\n\n"
                f"AI Securewatch — sean@aisecurewatch.com"
            )
            msg = MIMEMultipart()
            msg["Subject"] = subj
            msg["From"] = user
            msg["To"] = ", ".join(recipients)
            msg.attach(MIMEText(body, "plain"))

            if report_path and os.path.exists(report_path) and not is_test:
                with open(report_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition",
                                    f"attachment; filename={os.path.basename(report_path)}")
                    msg.attach(part)

            with smtplib.SMTP(smtp, int(port)) as server:
                server.starttls()
                server.login(user, pw)
                server.send_message(msg)

            self._log(f"✓ Email sent to {len(recipients)} recipient(s)")
            if is_test:
                messagebox.showinfo("Email Sent", "Test email sent successfully.")
        except Exception as e:
            self._log(f"Email failed: {e}")
            if is_test:
                messagebox.showerror("Email Error", str(e))

    # ══════════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ══════════════════════════════════════════════════════════════════════════

    def _empty_state(self, text: str, parent=None):
        p = parent or self.content
        ctk.CTkLabel(p, text=text, font=F(13), text_color=C["muted"],
                     justify="center").pack(expand=True)

    def run(self):
        self.root.mainloop()


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
        handlers=[
            logging.FileHandler(
                Path.home() / "PayReality_Data" / "payreality.log",
                encoding="utf-8"
            ) if (Path.home() / "PayReality_Data").exists()
            else logging.StreamHandler(),
            logging.StreamHandler(),
        ],
    )
    app = PayRealityApp()
    app.run()
