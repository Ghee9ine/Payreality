"""
PayReality - Professional Desktop Application
Properly connected to backend with working dashboard display

Fixes applied:
- CTkInputDialog moved to main thread BEFORE spawning analysis thread (thread-safety)
- run_button and settings entry attributes initialised in __init__ before create_widgets()
- open_report() is now cross-platform (Windows / macOS / Linux)
- SQLite connections always obtained via _get_connection() — no mixed self.conn/cursor
- Email settings entries initialised to None before create_settings_tab() is called
- Added create_settings_tab() with email configuration UI
- Uses new thresholds from config (loaded in core engine)
"""

import sys
import os
import subprocess
import platform
import threading
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

PAD_X = 20
PAD_Y = 16
PAD_SMALL = 8
CARD_RADIUS = 12
BUTTON_HEIGHT = 40

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.core import PayRealityEngine, DataValidationError
from src.reporting import PayRealityReport
from src.config import PayRealityConfig


class PayRealityApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("PayReality | AI Securewatch")
        self.root.geometry("1400x900")
        self.root.configure(fg_color="#F9FAFB")
        self.root.minsize(1200, 700)

        self.colors = {
            'primary':       '#1A4B8C',
            'primary_hover': '#0F7B6B',
            'success':       '#2E7D32',
            'danger':        '#D32F2F',
            'warning':       '#ED6C02',
            'info':          '#0288D1',
            'bg':            '#F9FAFB',
            'card':          '#FFFFFF',
            'text':          '#1F2937',
            'text_light':    '#6B7280',
            'border':        '#E5E7EB',
            'hover':         '#F3F4F6'
        }

        self.master_file = None
        self.payments_file = None
        self.output_dir = None
        self.email_var = ctk.BooleanVar(value=False)
        self.current_results = None
        self.db_path = None

        # Pre‑declare widget attributes
        self.run_button = None
        self.smtp_entry = None
        self.port_entry = None
        self.email_user_entry = None
        self.email_pass_entry = None
        self.recipients_entry = None
        self.tree = None
        self.reports_frame = None

        self.init_database()
        self.setup_ui()
        self.load_history()
        self.check_sample_data()

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    def init_database(self):
        db_path = Path.home() / "PayReality_Data" / "payreality.db"
        db_path.parent.mkdir(exist_ok=True)
        self.db_path = str(db_path)

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, client_name TEXT, total_payments INTEGER,
            exception_count INTEGER, exception_spend REAL,
            entropy_score REAL, duplicate_count INTEGER,
            health_score REAL, report_path TEXT)''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS email_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            smtp_server TEXT, smtp_port INTEGER,
            email_user TEXT, email_password TEXT,
            recipient_list TEXT)''')

        for col, col_type in [("health_score", "REAL DEFAULT 0"),
                               ("duplicate_count", "INTEGER DEFAULT 0")]:
            try:
                cursor.execute(f"ALTER TABLE analysis_history ADD COLUMN {col} {col_type}")
            except Exception:
                pass

        conn.commit()
        conn.close()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def create_card(self, parent, title=None):
        card = ctk.CTkFrame(
            parent, fg_color=self.colors['card'],
            corner_radius=CARD_RADIUS, border_width=1,
            border_color=self.colors['border']
        )
        if title:
            ctk.CTkLabel(
                card, text=title,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=self.colors['text']
            ).pack(anchor="w", padx=PAD_X, pady=(PAD_Y, PAD_SMALL))
        return card

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def setup_ui(self):
        main = ctk.CTkFrame(self.root, fg_color=self.colors['bg'])
        main.pack(fill="both", expand=True)

        # ---- Header ----
        header = ctk.CTkFrame(main, height=70, fg_color=self.colors['card'], corner_radius=0)
        header.pack(fill="x")

        hcontent = ctk.CTkFrame(header, fg_color="transparent")
        hcontent.pack(fill="both", expand=True, padx=32, pady=12)

        ctk.CTkLabel(
            hcontent, text="PayReality",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.colors['primary']
        ).pack(side="left")

        ctk.CTkLabel(
            hcontent, text="Independent Control Validation",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_light']
        ).pack(side="left", padx=(8, 0))

        self.file_status = ctk.CTkLabel(
            hcontent, text="No files selected",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_light']
        )
        self.file_status.pack(side="right", padx=(0, 16))

        ctk.CTkButton(
            hcontent, text="?",
            command=self.show_help,
            width=32, height=32,
            fg_color="transparent",
            text_color=self.colors['text_light'],
            hover_color=self.colors['hover'],
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=16
        ).pack(side="right", padx=4)

        # ---- Notebook (tabs) ----
        self.notebook = ctk.CTkTabview(main, corner_radius=16,
                                       segmented_button_selected_color=self.colors['primary'])
        self.notebook.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        self.dashboard_tab = self.notebook.add("Dashboard")
        self.history_tab = self.notebook.add("History")
        self.reports_tab = self.notebook.add("Reports")
        self.settings_tab = self.notebook.add("Email")

        # ---- Dashboard content ----
        self.create_dashboard_content()

        # ---- History content ----
        self.create_history_content()

        # ---- Reports content ----
        self.create_reports_content()

        # ---- Email settings content ----
        self.create_settings_tab()

    def create_dashboard_content(self):
        """Create all dashboard UI elements inside the Dashboard tab."""
        scroll = ctk.CTkScrollableFrame(self.dashboard_tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Welcome header
        ctk.CTkLabel(
            scroll, text="Dashboard",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.colors['text']
        ).pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(
            scroll, text="Control validation for vendor payments",
            font=ctk.CTkFont(size=14),
            text_color=self.colors['text_light']
        ).pack(anchor="w", pady=(0, 24))

        # File selection card
        file_card = self.create_card(scroll, "Control Test")
        file_card.pack(fill="x", pady=(0, 24))

        master_frame = ctk.CTkFrame(file_card, fg_color="transparent")
        master_frame.pack(fill="x", padx=PAD_X, pady=4)

        self.master_status = ctk.CTkLabel(
            master_frame, text="Vendor Master: Not selected",
            text_color=self.colors['text_light']
        )
        self.master_status.pack(side="left")

        ctk.CTkButton(
            master_frame, text="Browse",
            command=lambda: self.select_file("master"),
            width=80, height=32,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_hover'],
            corner_radius=8
        ).pack(side="right")

        payments_frame = ctk.CTkFrame(file_card, fg_color="transparent")
        payments_frame.pack(fill="x", padx=PAD_X, pady=8)

        self.payments_status = ctk.CTkLabel(
            payments_frame, text="Payments: Not selected",
            text_color=self.colors['text_light']
        )
        self.payments_status.pack(side="left")

        ctk.CTkButton(
            payments_frame, text="Browse",
            command=lambda: self.select_file("payments"),
            width=80, height=32,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_hover'],
            corner_radius=8
        ).pack(side="right")

        ctk.CTkCheckBox(
            file_card, text="Send email report",
            variable=self.email_var,
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=PAD_X, pady=(16, 8))

        self.run_button = ctk.CTkButton(
            file_card, text="Run Analysis",
            command=self.run_analysis,
            height=BUTTON_HEIGHT,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_hover'],
            corner_radius=12,
            state="disabled"
        )
        self.run_button.pack(fill="x", padx=PAD_X, pady=(8, 12))

        self.progress = ctk.CTkProgressBar(file_card, height=4, corner_radius=2)
        self.progress.pack(fill="x", padx=PAD_X, pady=(0, 12))
        self.progress.set(0)

        self.status_text = ctk.CTkTextbox(
            file_card, height=100, corner_radius=CARD_RADIUS,
            fg_color=self.colors['hover']
        )
        self.status_text.pack(fill="x", padx=PAD_X, pady=(0, 16))

        # KPI row
        kpi_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=(0, 24))

        self.kpi_cards = {}
        for title, value, color in [
            ("Exceptions Found", "0",   self.colors['danger']),
            ("Exception Spend",  "R 0", self.colors['warning']),
            ("Control Entropy",  "0%",  self.colors['primary']),
            ("Vendor Health",    "0%",  self.colors['success']),
        ]:
            card = self.create_card(kpi_frame)
            card.pack(side="left", fill="both", expand=True, padx=6)
            ctk.CTkLabel(
                card, text=title,
                font=ctk.CTkFont(size=12),
                text_color=self.colors['text_light']
            ).pack(pady=(12, 4))
            val_label = ctk.CTkLabel(
                card, text=value,
                font=ctk.CTkFont(size=28, weight="bold"),
                text_color=color
            )
            val_label.pack(pady=(0, 12))
            self.kpi_cards[title] = val_label

        # Two‑column section
        col_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        col_frame.pack(fill="both", expand=True)

        left = ctk.CTkFrame(col_frame, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))

        right = ctk.CTkFrame(col_frame, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True, padx=(12, 0))

        # Trend chart
        chart_card = self.create_card(left, "Control Entropy Trend")
        chart_card.pack(fill="both", expand=True)

        self.figure = plt.Figure(figsize=(6, 3), dpi=100, facecolor='white')
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#F9FAFB')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.set_xlabel('Analysis #', fontsize=9, color=self.colors['text_light'])
        self.ax.set_ylabel('Entropy Score (%)', fontsize=9, color=self.colors['text_light'])

        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_card)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=PAD_X, pady=(0, 16))

        # Exceptions list
        ex_card = self.create_card(right, "Recent Exceptions")
        ex_card.pack(fill="both", expand=True)

        self.exceptions_frame = ctk.CTkScrollableFrame(
            ex_card, fg_color="transparent", height=180
        )
        self.exceptions_frame.pack(fill="both", expand=True, padx=PAD_X, pady=(0, 12))

        ctk.CTkLabel(
            self.exceptions_frame,
            text="Run analysis to see exceptions",
            text_color=self.colors['text_light']
        ).pack(pady=30)

    def create_history_content(self):
        """Create the History tab with a table of past analyses."""
        frame = ctk.CTkFrame(self.history_tab, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header with export button
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            header, text="Analysis History",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.colors['text']
        ).pack(side="left")

        export_btn = ctk.CTkButton(
            header, text="Export to Excel",
            command=self.export_to_excel,
            fg_color=self.colors['success'],
            hover_color="#059669",
            height=36,
            corner_radius=12
        )
        export_btn.pack(side="right")

        # Table
        card = self.create_card(frame)
        card.pack(fill="both", expand=True)

        columns = ("Date", "Client", "Payments", "Exceptions", "Duplicates", "Spend", "Entropy", "Health")
        self.tree = ttk.Treeview(card, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")

        scrollbar = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        scrollbar.pack(side="right", fill="y", pady=20)

        self.populate_history_table()

    def create_reports_content(self):
        """Create the Reports tab with a list of generated PDFs."""
        frame = ctk.CTkFrame(self.reports_tab, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        card = self.create_card(frame, "Generated Reports")
        card.pack(fill="both", expand=True)

        self.reports_list = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self.reports_list.pack(fill="both", expand=True, padx=20, pady=20)

        self.refresh_reports_list()

    def create_settings_tab(self):
        """Create the Email configuration UI inside the Email tab."""
        frame = ctk.CTkFrame(self.settings_tab, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        card = self.create_card(frame, "Email Configuration")
        card.pack(fill="both", expand=True)

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=24, pady=(0, 24))

        fields = [
            ("SMTP Server", "smtp.gmail.com", "smtp_entry"),
            ("Port", "587", "port_entry"),
            ("Email Address", "your-email@gmail.com", "email_user_entry"),
            ("Password", "your-password", "email_pass_entry"),
            ("Recipients (comma separated)", "auditor@company.com", "recipients_entry")
        ]

        for label, placeholder, attr in fields:
            row = ctk.CTkFrame(form, fg_color="transparent")
            row.pack(fill="x", pady=8)
            ctk.CTkLabel(row, text=label, width=120,
                         font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
            entry = ctk.CTkEntry(row, width=300, placeholder_text=placeholder, corner_radius=8)
            entry.pack(side="left", padx=12)
            setattr(self, attr, entry)
            if "pass" in attr:
                entry.configure(show="•")

        # Load saved settings
        self.load_email_settings()

        # Save button
        ctk.CTkButton(
            card, text="Save Settings", command=self.save_email_settings,
            fg_color=self.colors['primary'], height=40, corner_radius=12
        ).pack(pady=(0, 24))

    def load_email_settings(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT smtp_server, smtp_port, email_user, email_password, recipient_list "
            "FROM email_config LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            self.smtp_entry.delete(0, "end")
            self.smtp_entry.insert(0, row[0])
            self.port_entry.delete(0, "end")
            self.port_entry.insert(0, str(row[1]))
            self.email_user_entry.delete(0, "end")
            self.email_user_entry.insert(0, row[2])
            self.email_pass_entry.delete(0, "end")
            self.email_pass_entry.insert(0, row[3])
            self.recipients_entry.delete(0, "end")
            self.recipients_entry.insert(0, row[4])

    def save_email_settings(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM email_config")
        cursor.execute(
            '''INSERT INTO email_config
               (smtp_server, smtp_port, email_user, email_password, recipient_list)
               VALUES (?, ?, ?, ?, ?)''',
            (self.smtp_entry.get(), int(self.port_entry.get() or 587),
             self.email_user_entry.get(), self.email_pass_entry.get(),
             self.recipients_entry.get())
        )
        conn.commit()
        conn.close()
        self.log("Email settings saved")
        messagebox.showinfo("Success", "Email settings saved")

    # ------------------------------------------------------------------
    # File selection
    # ------------------------------------------------------------------

    def select_file(self, file_type):
        filepath = filedialog.askopenfilename(
            title=f"Select {file_type}",
            filetypes=[("CSV/Excel/PDF", "*.csv *.xlsx *.xls *.pdf"), ("All files", "*.*")]
        )
        if filepath:
            if file_type == "master":
                self.master_file = filepath
                self.master_status.configure(
                    text=f"Vendor Master: {os.path.basename(filepath)}",
                    text_color=self.colors['success']
                )
                self.log(f"Selected vendor master: {os.path.basename(filepath)}")
            else:
                self.payments_file = filepath
                self.payments_status.configure(
                    text=f"Payments: {os.path.basename(filepath)}",
                    text_color=self.colors['success']
                )
                self.log(f"Selected payments: {os.path.basename(filepath)}")

            if self.master_file and self.payments_file:
                self.run_button.configure(state="normal")
                if not self.output_dir:
                    self.output_dir = str(Path.home() / "Desktop" / "PayReality_Reports")
                    os.makedirs(self.output_dir, exist_ok=True)
                self.file_status.configure(
                    text=f"Ready: {os.path.basename(self.master_file)} | "
                         f"{os.path.basename(self.payments_file)}"
                )
                self.log("Both files selected. Click Run Analysis to start.")

    # ------------------------------------------------------------------
    # Analysis — dialog on main thread, client_name passed to thread
    # ------------------------------------------------------------------

    def run_analysis(self):
        if not self.master_file or not self.payments_file:
            messagebox.showwarning("Missing Files", "Please select both files")
            return

        dialog = ctk.CTkInputDialog(text="Enter client name:", title="Client")
        client_name = dialog.get_input() or "Client"

        self.run_button.configure(state="disabled", text="Processing...")
        self.progress.set(0)
        self.status_text.delete("1.0", "end")

        thread = threading.Thread(
            target=self._run_analysis_thread,
            args=(client_name,),
            daemon=True
        )
        thread.start()

    def _run_analysis_thread(self, client_name: str):
        try:
            self.progress.set(0.1)
            self.log("Starting analysis...")
            self.log(f"Client: {client_name}")

            self.progress.set(0.3)
            self.log("Loading and parsing files...")

            engine = PayRealityEngine(config=self._load_config())
            results = engine.run_analysis(
                self.master_file, self.payments_file, batch_size=10000
            )

            self.progress.set(0.6)
            self.log(f"✓ Found {results['exception_count']:,} exceptions")
            self.log(f"✓ Control Entropy Score: {results['entropy_score']:.1f}%")

            health_score = results.get('health_report', {}).get('health_score', 0)
            self.log(f"✓ Vendor Master Health: {health_score:.1f}%")

            duplicate_count = len(results.get('duplicates', []))
            if duplicate_count > 0:
                self.log(f"✓ Found {duplicate_count} potential duplicate vendors")

            self.progress.set(0.7)
            self.log("Generating PDF report...")

            reporter = PayRealityReport(client_name=client_name)
            report_path = reporter.generate_report(results, self.output_dir)
            self.log(f"✓ Report saved: {report_path}")

            self.progress.set(0.8)
            self.log("Saving to history...")
            self.save_to_history(results, client_name, report_path)

            if self.email_var.get():
                self.log("Sending email...")
                self.send_email_report(report_path, client_name, results)

            self.progress.set(1.0)
            self.root.after(0, lambda: self.display_results(results))
            self.log("✓ Analysis complete!")

            self.root.after(0, lambda: messagebox.showinfo(
                "Analysis Complete",
                f"Control Entropy Score: {results['entropy_score']:.1f}%\n"
                f"Exceptions Found: {results['exception_count']:,}\n"
                f"Exception Spend: R {results['exception_spend']:,.2f}\n"
                f"Vendor Master Health: {health_score:.1f}%\n\n"
                f"Report saved to:\n{report_path}"
            ))

        except DataValidationError as e:
            error_msg = str(e)
            self.log(f"✗ Error: {error_msg}")
            if "Missing required columns" in error_msg:
                friendly = (
                    "File Format Error\n\n"
                    "The file doesn't have the required columns.\n\n"
                    "Required: 'payee_name' and 'amount'\n\n"
                    "Check the sample files in data/sample/ for reference."
                )
                self.root.after(0, lambda: messagebox.showerror("File Format Error", friendly))
            elif "File not found" in error_msg:
                self.root.after(0, lambda: messagebox.showerror(
                    "File Not Found",
                    "The selected file could not be found.\n\nPlease check the path and try again."
                ))
            elif "empty" in error_msg.lower():
                self.root.after(0, lambda: messagebox.showerror(
                    "Empty File",
                    "The selected file appears to be empty.\n\nPlease check the file and try again."
                ))
            else:
                self.root.after(0, lambda: messagebox.showerror(
                    "Processing Error", f"An error occurred:\n\n{error_msg}"
                ))

        except Exception as e:
            error_msg = str(e)
            self.log(f"✗ Unexpected error: {error_msg}")
            self.root.after(0, lambda: messagebox.showerror(
                "Unexpected Error",
                f"An unexpected error occurred:\n\n{error_msg}\n\nPlease try again."
            ))

        finally:
            self.root.after(
                0, lambda: self.run_button.configure(state="normal", text="Run Analysis")
            )

    def _load_config(self):
        """Load configuration from file (used by the engine)."""
        config = PayRealityConfig()
        return config.config

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def display_results(self, results):
        self.current_results = results

        self.kpi_cards["Exceptions Found"].configure(
            text=f"{results.get('exception_count', 0):,}"
        )
        self.kpi_cards["Exception Spend"].configure(
            text=f"R {results.get('exception_spend', 0):,.0f}"
        )
        self.kpi_cards["Control Entropy"].configure(
            text=f"{results.get('entropy_score', 0):.1f}%"
        )
        health_score = results.get('health_report', {}).get('health_score', 0)
        self.kpi_cards["Vendor Health"].configure(text=f"{health_score:.0f}%")

        for w in self.exceptions_frame.winfo_children():
            w.destroy()

        exceptions = results.get('exceptions', [])[:5]
        if exceptions:
            for ex in exceptions:
                item = ctk.CTkFrame(
                    self.exceptions_frame, fg_color=self.colors['hover'], corner_radius=10
                )
                item.pack(fill="x", pady=2)

                risk = ex.get('risk_level', 'Low')
                risk_color = {
                    'High': self.colors['danger'],
                    'Medium': self.colors['warning'],
                    'Low': self.colors['success']
                }.get(risk, self.colors['text_light'])

                ctk.CTkLabel(
                    item, text=ex.get('payee_name', 'Unknown')[:40],
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=self.colors['text']
                ).pack(side="left", padx=12, pady=10)

                ctk.CTkLabel(
                    item, text=f"R {ex.get('amount', 0):,.0f}",
                    font=ctk.CTkFont(size=11),
                    text_color=self.colors['warning']
                ).pack(side="left", padx=8)

                ctk.CTkLabel(
                    item, text=risk,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    text_color=risk_color,
                    fg_color=self.colors['bg'],
                    corner_radius=8, padx=6, pady=2
                ).pack(side="left", padx=8)
        else:
            ctk.CTkLabel(
                self.exceptions_frame, text="No exceptions found",
                text_color=self.colors['text_light']
            ).pack(pady=30)

        self.update_trend_chart()
        self.populate_history_table()
        self.refresh_reports_list()

    def update_trend_chart(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT entropy_score FROM analysis_history ORDER BY date ASC")
        scores = [row[0] for row in cursor.fetchall()]
        conn.close()

        self.ax.clear()
        if scores:
            x = range(len(scores))
            self.ax.plot(
                x, scores, marker='o', linewidth=2,
                color=self.colors['primary'], markersize=6, markerfacecolor='white'
            )
            self.ax.fill_between(x, scores, alpha=0.15, color=self.colors['primary'])
            self.ax.set_xticks(x)
            self.ax.set_xticklabels([str(i + 1) for i in x], rotation=45, ha='right')
            self.ax.set_ylim(0, max(100, max(scores) + 10))
            self.ax.axhline(y=20, color=self.colors['warning'], linestyle='--', alpha=0.5)
            self.ax.axhline(y=40, color=self.colors['danger'], linestyle='--', alpha=0.5)
        else:
            self.ax.text(
                0.5, 0.5, "No data yet", ha='center', va='center',
                fontsize=12, color=self.colors['text_light']
            )
            self.ax.set_ylim(0, 100)

        self.ax.set_xlabel('Analysis #', fontsize=9, color=self.colors['text_light'])
        self.ax.set_ylabel('Entropy Score (%)', fontsize=9, color=self.colors['text_light'])
        self.canvas.draw()

    def populate_history_table(self):
        """Refresh the history table with data from the database."""
        if self.tree is None:
            return
        for row in self.tree.get_children():
            self.tree.delete(row)

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT date, client_name, total_payments, exception_count,
                          exception_spend, entropy_score, duplicate_count, health_score
                          FROM analysis_history ORDER BY date DESC''')
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            self.tree.insert("", "end", values=(
                row[0], row[1], f"{row[2]:,}", f"{row[3]:,}",
                f"{row[6]}", f"R {row[4]:,.0f}", f"{row[5]:.1f}%", f"{row[7]:.0f}%"
            ))

    def refresh_reports_list(self):
        """Refresh the reports list with generated PDFs."""
        if self.reports_list is None:
            return
        for w in self.reports_list.winfo_children():
            w.destroy()

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT date, client_name, report_path FROM analysis_history WHERE report_path IS NOT NULL ORDER BY date DESC")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            ctk.CTkLabel(
                self.reports_list,
                text="No reports yet",
                text_color=self.colors['text_light']
            ).pack(pady=40)
        else:
            for row in rows:
                if row[2] and os.path.exists(row[2]):
                    item = ctk.CTkFrame(self.reports_list, fg_color=self.colors['hover'], corner_radius=12)
                    item.pack(fill="x", pady=3)
                    ctk.CTkLabel(
                        item, text=f"{row[0]} - {row[1]}",
                        font=ctk.CTkFont(size=12)
                    ).pack(side="left", padx=16, pady=12)
                    ctk.CTkButton(
                        item, text="Open",
                        command=lambda p=row[2]: self.open_report(p),
                        width=70, height=32,
                        fg_color=self.colors['primary'],
                        corner_radius=8
                    ).pack(side="right", padx=16)

    # ------------------------------------------------------------------
    # History & reporting helpers
    # ------------------------------------------------------------------

    def load_history(self):
        """Called at startup to load trend chart and populate tables."""
        self.update_trend_chart()
        self.populate_history_table()
        self.refresh_reports_list()

    def save_to_history(self, results, client_name, report_path):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO analysis_history
               (date, client_name, total_payments, exception_count, exception_spend,
                entropy_score, duplicate_count, health_score, report_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                client_name,
                results['total_payments'],
                results['exception_count'],
                results['exception_spend'],
                results['entropy_score'],
                len(results.get('duplicates', [])),
                results.get('health_report', {}).get('health_score', 0),
                report_path
            )
        )
        conn.commit()
        conn.close()

        # Refresh UI
        self.populate_history_table()
        self.refresh_reports_list()
        self.update_trend_chart()

    def export_to_excel(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT date, client_name, total_payments, exception_count,
                          exception_spend, entropy_score, duplicate_count, health_score
                          FROM analysis_history ORDER BY date DESC''')
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            messagebox.showwarning("No Data", "No history to export")
            return

        df = pd.DataFrame(rows, columns=['Date', 'Client', 'Payments', 'Exceptions',
                                          'Exception Spend', 'Entropy Score', 'Duplicates', 'Health Score'])

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"payreality_history_{datetime.now().strftime('%Y%m%d')}"
        )

        if filepath:
            df.to_excel(filepath, index=False)
            self.log(f"Exported to Excel: {os.path.basename(filepath)}")
            messagebox.showinfo("Export Complete", f"Data exported to:\n{filepath}")

    # ------------------------------------------------------------------
    # Email
    # ------------------------------------------------------------------

    def send_email_report(self, report_path, client_name, results):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT smtp_server, smtp_port, email_user, email_password, recipient_list "
                "FROM email_config LIMIT 1"
            )
            config = cursor.fetchone()
            conn.close()

            if not config or not config[0]:
                self.log("Email not sent: No configuration")
                return

            smtp_server, smtp_port, email_user, email_password, recipient_list = config
            recipients = [r.strip() for r in recipient_list.split(',') if r.strip()]

            msg = MIMEMultipart()
            msg['Subject'] = f"PayReality Report - {client_name}"
            msg['From'] = email_user
            msg['To'] = ", ".join(recipients)

            health_score = results.get('health_report', {}).get('health_score', 0)
            body = (
                f"PayReality Control Validation Report\n\n"
                f"Client: {client_name}\n"
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Results:\n"
                f"- Control Entropy Score: {results['entropy_score']:.1f}%\n"
                f"- Total Payments: {results['total_payments']:,}\n"
                f"- Exceptions Found: {results['exception_count']:,}\n"
                f"- Exception Spend: R {results['exception_spend']:,.2f}\n"
                f"- Duplicate Vendors: {len(results.get('duplicates', []))}\n"
                f"- Vendor Master Health: {health_score:.1f}%\n\n"
                f"Full report attached."
            )
            msg.attach(MIMEText(body, 'plain'))

            with open(report_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(report_path)}"
                )
                msg.attach(part)

            with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
                server.starttls()
                server.login(email_user, email_password)
                server.send_message(msg)

            self.log(f"✓ Email sent to {len(recipients)} recipient(s)")
        except Exception as e:
            self.log(f"✗ Email failed: {str(e)}")

    # ------------------------------------------------------------------
    # Misc helpers
    # ------------------------------------------------------------------

    def log(self, msg: str):
        self.status_text.insert("end", f"{msg}\n")
        self.status_text.see("end")
        self.root.update()

    def check_sample_data(self):
        sample_master = Path("data/sample/vendor_master.csv")
        sample_payments = Path("data/sample/payments.csv")

        if sample_master.exists() and sample_payments.exists():
            if messagebox.askyesno("Sample Data Found", "Load sample data to test PayReality?"):
                self.master_file = str(sample_master)
                self.payments_file = str(sample_payments)
                self.master_status.configure(
                    text=f"Vendor Master: {sample_master.name}",
                    text_color=self.colors['success']
                )
                self.payments_status.configure(
                    text=f"Payments: {sample_payments.name}",
                    text_color=self.colors['success']
                )
                self.run_button.configure(state="normal")
                self.file_status.configure(text="Ready: sample data")
                self.log("Sample data loaded. Click Run Analysis to test.")

    def open_report(self, report_path: str):
        """Cross‑platform file opener"""
        if not os.path.exists(report_path):
            messagebox.showwarning("File Not Found", f"Report not found:\n{report_path}")
            return
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.run(["open", report_path], check=True)
            elif system == "Linux":
                subprocess.run(["xdg-open", report_path], check=True)
            else:
                os.startfile(report_path)
            self.log(f"Opened report: {os.path.basename(report_path)}")
        except Exception as e:
            messagebox.showerror("Could Not Open", f"Could not open report:\n{e}")

    def show_help(self):
        messagebox.showinfo(
            "How to Use PayReality",
            "PayReality — Quick Guide\n\n"
            "1. Select Vendor Master file (CSV/Excel)\n"
            "2. Select Payments file (CSV/Excel/PDF)\n"
            "3. Click Run Analysis\n"
            "4. View results on Dashboard\n"
            "5. PDF report saved to Desktop/PayReality_Reports\n\n"
            "Control Entropy Score: % of spend to unapproved vendors\n"
            "Vendor Health Score: Quality of your vendor master data"
        )

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PayRealityApp()
    app.run()