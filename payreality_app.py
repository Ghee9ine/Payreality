"""
PayReality - Professional Desktop Application
Complete version with 7-Pass Semantic Matching display
"""

import sys
import os
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
from tkinter import filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.core import PayRealityEngine, DataValidationError
from src.reporting import PayRealityReport
from src.config import PayRealityConfig


class PayRealityApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("PayReality")
        self.root.geometry("1400x900")
        self.root.configure(fg_color="#FFFFFF")
        
        self.colors = {
            'primary': '#3B82F6',
            'accent': '#8B5CF6',
            'success': '#22C55E',
            'danger': '#EF4444',
            'warning': '#F97316',
            'text': '#1E293B',
            'text_light': '#64748B',
            'border': '#E2E8F0',
            'bg': '#FFFFFF',
            'hover': '#F8FAFC'
        }
        
        self.master_file = None
        self.payments_file = None
        self.output_dir = None
        self.email_var = ctk.BooleanVar(value=False)
        
        # Store current results for persistence
        self.current_results = None
        self.current_exceptions = []
        
        # Database
        self.db_path = None
        self.init_database()
        
        self.setup_ui()
        self.load_history()
        
        # Check for sample data
        self.check_sample_data()
    
    def init_database(self):
        """Initialize database with thread-safe connection handling"""
        db_path = Path.home() / "PayReality_Data" / "payreality.db"
        db_path.parent.mkdir(exist_ok=True)
        self.db_path = str(db_path)
        
        # Create tables on main thread
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, client_name TEXT, total_payments INTEGER,
            exception_count INTEGER, exception_spend REAL,
            entropy_score REAL, duplicate_count INTEGER,
            report_path TEXT)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS email_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            smtp_server TEXT, smtp_port INTEGER,
            email_user TEXT, email_password TEXT,
            recipient_list TEXT)''')
        
        try:
            cursor.execute("ALTER TABLE analysis_history ADD COLUMN duplicate_count INTEGER DEFAULT 0")
        except:
            pass
        
        conn.commit()
        conn.close()
    
    def _get_connection(self):
        """Get a database connection for the current thread"""
        return sqlite3.connect(self.db_path)
    
    def setup_ui(self):
        main = ctk.CTkFrame(self.root, fg_color="#FFFFFF")
        main.pack(fill="both", expand=True)
        
        # Header
        header = ctk.CTkFrame(main, fg_color="#FFFFFF", height=70)
        header.pack(fill="x", padx=40, pady=(20, 0))
        
        ctk.CTkLabel(header, text="PayReality", 
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color=self.colors['primary']).pack(side="left")
        
        ctk.CTkLabel(header, text="v2.0",
                     font=ctk.CTkFont(size=12),
                     text_color=self.colors['text_light']).pack(side="left", padx=(8, 0))
        
        ctk.CTkLabel(header, text="7-Pass Semantic Matching",
                     font=ctk.CTkFont(size=12),
                     text_color=self.colors['accent']).pack(side="left", padx=(8, 0))
        
        ctk.CTkLabel(header, text="Independent Control Validation",
                     font=ctk.CTkFont(size=12),
                     text_color=self.colors['text_light']).pack(side="left", padx=(8, 0))
        
        # Help button
        help_btn = ctk.CTkButton(
            header, text="?", command=self.show_help,
            width=30, height=30, fg_color="transparent",
            text_color=self.colors['text_light'],
            hover_color=self.colors['hover'],
            font=ctk.CTkFont(size=14, weight="bold")
        )
        help_btn.pack(side="right", padx=10)
        
        ctk.CTkFrame(main, height=1, fg_color=self.colors['border']).pack(fill="x", padx=40, pady=(16, 24))
        
        # Tab buttons
        tab_frame = ctk.CTkFrame(main, fg_color="transparent")
        tab_frame.pack(fill="x", padx=40)
        
        self.tab_buttons = {}
        tabs = ["Dashboard", "History", "Reports", "Email"]
        
        for i, tab in enumerate(tabs):
            btn = ctk.CTkButton(
                tab_frame, text=tab, command=lambda t=tab: self.switch_tab(t),
                fg_color="transparent", text_color=self.colors['text_light'],
                hover_color=self.colors['hover'], width=80, height=40,
                font=ctk.CTkFont(size=14, weight="bold")
            )
            btn.pack(side="left", padx=(0 if i == 0 else 4, 0))
            self.tab_buttons[tab] = btn
        
        self.content_frame = ctk.CTkFrame(main, fg_color="#FFFFFF")
        self.content_frame.pack(fill="both", expand=True, padx=40, pady=(24, 40))
        
        self.current_tab = "Dashboard"
        self.tab_buttons["Dashboard"].configure(fg_color=self.colors['primary'], text_color="#FFFFFF")
        self.show_dashboard()
    
    def show_help(self):
        """Display help information"""
        help_text = """PayReality - Quick Guide

1. Select Vendor Master (CSV/Excel)
   Must have vendor names column
   (vendor_name, vendor, supplier, name)

2. Select Payments (CSV/Excel/PDF)
   Must have payee name and amount
   (payee_name, payee, vendor, amount, value, total)

3. Click Run Analysis
   7-pass semantic matching engine processes each payment
   - Exact → Normalized → Token Sort → Partial → Levenshtein → Phonetic → Obfuscation

4. Results appear on Dashboard
   - KPI cards show summary
   - Exceptions list shows unapproved vendors with tenure and risk
   - PDF report saved to Desktop/PayReality_Reports

5. View past analyses in History tab
6. Find and open reports in Reports tab

7. Configure email in Email tab to receive reports automatically

Need help? sean@aisecurewatch.com"""
        messagebox.showinfo("How to Use PayReality", help_text)
    
    def check_sample_data(self):
        """Check if sample data exists and offer to load it"""
        sample_master = Path("data/sample/vendor_master.csv")
        sample_payments = Path("data/sample/payments.csv")
        
        if sample_master.exists() and sample_payments.exists():
            response = messagebox.askyesno(
                "Sample Data Found",
                "Load sample data to test PayReality?\n\n"
                "This will load example vendor and payment files so you can test the analysis."
            )
            if response:
                self.master_file = str(sample_master)
                self.master_status.configure(text=f"Vendor Master: {sample_master.name}", 
                                              text_color=self.colors['success'])
                self.payments_file = str(sample_payments)
                self.payments_status.configure(text=f"Payments: {sample_payments.name}", 
                                                text_color=self.colors['success'])
                self.run_button.configure(state="normal")
                self.log("✓ Sample data loaded. Click Run Analysis to test.")
    
    def switch_tab(self, tab):
        for t, btn in self.tab_buttons.items():
            if t == tab:
                btn.configure(fg_color=self.colors['primary'], text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color=self.colors['text_light'])
        
        self.current_tab = tab
        
        for w in self.content_frame.winfo_children():
            w.destroy()
        
        if tab == "Dashboard":
            self.show_dashboard()
        elif tab == "History":
            self.show_history()
        elif tab == "Reports":
            self.show_reports()
        elif tab == "Email":
            self.show_email()
    
    def show_dashboard(self):
        # KPI Row
        kpi_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=(0, 32))
        
        self.kpi_cards = {}
        kpis = [
            ("Exceptions Found", self.colors['danger']),
            ("Exception Spend", self.colors['warning']),
            ("Control Entropy", self.colors['primary']),
            ("Total Payments", self.colors['success'])
        ]
        
        for title, color in kpis:
            card = ctk.CTkFrame(kpi_frame, fg_color="#F8FAFC", corner_radius=16)
            card.pack(side="left", fill="both", expand=True, padx=6)
            
            ctk.CTkLabel(card, text=title,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=self.colors['text_light']).pack(pady=(16, 4))
            val = ctk.CTkLabel(card, text="0", 
                               font=ctk.CTkFont(size=32, weight="bold"),
                               text_color=color)
            val.pack(pady=(0, 16))
            self.kpi_cards[title] = val
        
        # Two columns
        row = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        row.pack(fill="both", expand=True)
        
        left = ctk.CTkFrame(row, fg_color="#F8FAFC", corner_radius=16)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        
        ctk.CTkLabel(left, text="Control Entropy Trend",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=self.colors['text']).pack(anchor="w", padx=20, pady=(16, 12))
        
        self.figure = plt.Figure(figsize=(5, 3), dpi=100, facecolor='#F8FAFC')
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#F8FAFC')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.canvas = FigureCanvasTkAgg(self.figure, master=left)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        right = ctk.CTkFrame(row, fg_color="#F8FAFC", corner_radius=16)
        right.pack(side="right", fill="both", expand=True, padx=(12, 0))
        
        ctk.CTkLabel(right, text="Control Test",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=self.colors['text']).pack(anchor="w", padx=20, pady=(16, 16))
        
        self.master_status = ctk.CTkLabel(right, text="Vendor Master: Not selected",
                                           text_color=self.colors['text_light'])
        self.master_status.pack(anchor="w", padx=20, pady=4)
        ctk.CTkButton(right, text="Browse", command=lambda: self.select_file("master"),
                      width=100, height=32, fg_color=self.colors['primary'],
                      corner_radius=8).pack(anchor="w", padx=20, pady=4)
        
        self.payments_status = ctk.CTkLabel(right, text="Payments: Not selected",
                                             text_color=self.colors['text_light'])
        self.payments_status.pack(anchor="w", padx=20, pady=(12, 4))
        ctk.CTkButton(right, text="Browse", command=lambda: self.select_file("payments"),
                      width=100, height=32, fg_color=self.colors['primary'],
                      corner_radius=8).pack(anchor="w", padx=20, pady=4)
        
        self.email_checkbox = ctk.CTkCheckBox(right, text="Send email report",
                                               variable=self.email_var,
                                               font=ctk.CTkFont(size=12))
        self.email_checkbox.pack(anchor="w", padx=20, pady=(20, 12))
        
        self.run_button = ctk.CTkButton(right, text="Run Analysis",
                                         command=self.run_analysis,
                                         height=44, fg_color=self.colors['primary'],
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         corner_radius=12, state="disabled")
        self.run_button.pack(fill="x", padx=20, pady=(8, 16))
        
        self.progress = ctk.CTkProgressBar(right, height=4, corner_radius=2)
        self.progress.pack(fill="x", padx=20, pady=(0, 12))
        self.progress.set(0)
        
        self.status_text = ctk.CTkTextbox(right, height=100, corner_radius=12,
                                           fg_color="#FFFFFF", border_width=1,
                                           border_color=self.colors['border'])
        self.status_text.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkLabel(right, text="Recent Exceptions",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=self.colors['text']).pack(anchor="w", padx=20, pady=(0, 8))
        
        self.exceptions_frame = ctk.CTkScrollableFrame(right, fg_color="#FFFFFF", height=200)
        self.exceptions_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.exceptions_placeholder = ctk.CTkLabel(self.exceptions_frame, text="No exceptions yet",
                                                    text_color=self.colors['text_light'])
        self.exceptions_placeholder.pack(pady=20)
        
        # Restore results if they exist
        if self.current_results:
            self.display_results(self.current_results)
    
    def show_history(self):
        frame = ctk.CTkFrame(self.content_frame, fg_color="#F8FAFC", corner_radius=16)
        frame.pack(fill="both", expand=True)
        
        export_btn = ctk.CTkButton(frame, text="Export to Excel", 
                                    command=self.export_to_excel,
                                    fg_color=self.colors['success'], height=32,
                                    corner_radius=8)
        export_btn.pack(anchor="e", padx=20, pady=(12, 0))
        
        from tkinter import ttk
        columns = ("Date", "Client", "Payments", "Exceptions", "Duplicates", "Spend", "Entropy")
        
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        scrollbar.pack(side="right", fill="y", pady=20)
        
        self.refresh_history_table()
    
    def refresh_history_table(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if hasattr(self, 'tree'):
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            cursor.execute("SELECT date, client_name, total_payments, exception_count, exception_spend, entropy_score, duplicate_count FROM analysis_history ORDER BY date DESC")
            rows = cursor.fetchall()
            
            for row in rows:
                self.tree.insert("", "end", values=(
                    row[0], row[1], f"{row[2]:,}", f"{row[3]:,}",
                    f"{row[6] if row[6] else 0}", f"R {row[4]:,.0f}", f"{row[5]:.1f}%"
                ))
        
        conn.close()
    
    def show_reports(self):
        self.reports_frame = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        self.reports_frame.pack(fill="both", expand=True)
        self.refresh_reports_list()
    
    def refresh_reports_list(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if hasattr(self, 'reports_frame'):
            for w in self.reports_frame.winfo_children():
                w.destroy()
            
            cursor.execute("SELECT date, client_name, report_path FROM analysis_history WHERE report_path IS NOT NULL ORDER BY date DESC")
            rows = cursor.fetchall()
            
            if not rows:
                ctk.CTkLabel(self.reports_frame, text="No reports yet",
                             text_color=self.colors['text_light']).pack(pady=40)
            else:
                for row in rows:
                    if row[2] and os.path.exists(row[2]):
                        item = ctk.CTkFrame(self.reports_frame, fg_color="#F8FAFC", corner_radius=8)
                        item.pack(fill="x", pady=2)
                        ctk.CTkLabel(item, text=f"{row[0]} - {row[1]}",
                                     font=ctk.CTkFont(size=11)).pack(side="left", padx=12, pady=8)
                        ctk.CTkButton(item, text="Open", command=lambda p=row[2]: self.open_report(p),
                                      width=60, height=28, fg_color=self.colors['primary'],
                                      corner_radius=6).pack(side="right", padx=12)
        
        conn.close()
    
    def show_email(self):
        card = ctk.CTkFrame(self.content_frame, fg_color="#F8FAFC", corner_radius=16)
        card.pack(fill="both", expand=True, pady=20)
        
        ctk.CTkLabel(card, text="Email Configuration",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=self.colors['text']).pack(anchor="w", padx=24, pady=(24, 8))
        
        ctk.CTkLabel(card, text="Configure email settings to receive reports automatically",
                     font=ctk.CTkFont(size=12),
                     text_color=self.colors['text_light']).pack(anchor="w", padx=24, pady=(0, 24))
        
        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=24, pady=(0, 24))
        
        fields = [
            ("SMTP Server", "smtp.gmail.com", "smtp_entry"),
            ("Port", "587", "port_entry"),
            ("Email Address", "your-email@gmail.com", "email_user_entry"),
            ("Password", "your-password", "email_pass_entry"),
            ("Recipients", "auditor@company.com", "recipients_entry")
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
        
        self.load_email_settings()
        
        save_btn = ctk.CTkButton(card, text="Save Settings", command=self.save_email_settings,
                                  fg_color=self.colors['primary'], height=40, corner_radius=12)
        save_btn.pack(pady=(0, 24))
    
    def load_email_settings(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT smtp_server, smtp_port, email_user, email_password, recipient_list FROM email_config LIMIT 1")
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
        cursor.execute('''INSERT INTO email_config (smtp_server, smtp_port, email_user, email_password, recipient_list)
                           VALUES (?, ?, ?, ?, ?)''',
                        (self.smtp_entry.get(), int(self.port_entry.get() or 587),
                         self.email_user_entry.get(), self.email_pass_entry.get(),
                         self.recipients_entry.get()))
        conn.commit()
        conn.close()
        self.log("Email settings saved")
        messagebox.showinfo("Success", "Email settings saved")
    
    def select_file(self, file_type):
        filepath = filedialog.askopenfilename(
            title=f"Select {file_type}",
            filetypes=[("CSV/Excel/PDF", "*.csv *.xlsx *.xls *.pdf"), ("All files", "*.*")]
        )
        if filepath:
            if file_type == "master":
                self.master_file = filepath
                self.master_status.configure(text=f"Vendor Master: {os.path.basename(filepath)}",
                                              text_color=self.colors['success'])
            else:
                self.payments_file = filepath
                self.payments_status.configure(text=f"Payments: {os.path.basename(filepath)}",
                                                text_color=self.colors['success'])
            
            if self.master_file and self.payments_file:
                self.run_button.configure(state="normal")
                if not self.output_dir:
                    self.output_dir = str(Path.home() / "Desktop" / "PayReality_Reports")
                    os.makedirs(self.output_dir, exist_ok=True)
    
    def display_results(self, results):
        """Display results on dashboard with full tenure, frequency, and match strategy details"""
        self.current_results = results
        
        self.update_kpis(
            results['exception_count'],
            results['exception_spend'],
            results['entropy_score'],
            results['total_payments']
        )
        
        # Update exceptions list with detailed information
        for w in self.exceptions_frame.winfo_children():
            w.destroy()
        
        exceptions = results.get('exceptions', [])[:5]
        if exceptions:
            for ex in exceptions:
                # Main card
                card = ctk.CTkFrame(self.exceptions_frame, fg_color="#F8FAFC", corner_radius=12)
                card.pack(fill="x", pady=4, padx=2)
                
                # Row 1: Vendor name and amount
                row1 = ctk.CTkFrame(card, fg_color="transparent")
                row1.pack(fill="x", padx=12, pady=(10, 4))
                
                name = ex.get('payee_name', 'Unknown')[:40]
                amount = ex.get('amount', 0)
                
                ctk.CTkLabel(row1, text=name, font=ctk.CTkFont(size=13, weight="bold"),
                             text_color=self.colors['text']).pack(side="left")
                ctk.CTkLabel(row1, text=f"R {amount:,.0f}", font=ctk.CTkFont(size=13, weight="bold"),
                             text_color=self.colors['warning']).pack(side="right")
                
                # Row 2: Tenure and frequency
                row2 = ctk.CTkFrame(card, fg_color="transparent")
                row2.pack(fill="x", padx=12, pady=2)
                
                first_seen = ex.get('first_seen', '')
                last_seen = ex.get('last_seen', '')
                payment_count = ex.get('payment_count', 0)
                tenure_days = ex.get('tenure_days', 0)
                
                if tenure_days > 0:
                    if tenure_days > 365:
                        years = tenure_days // 365
                        months = (tenure_days % 365) // 30
                        tenure_text = f"{years}y {months}m"
                    elif tenure_days > 30:
                        months = tenure_days // 30
                        days = tenure_days % 30
                        tenure_text = f"{months}m {days}d"
                    else:
                        tenure_text = f"{tenure_days}d"
                    
                    ctk.CTkLabel(row2, text=f"📅 Active: {tenure_text}", font=ctk.CTkFont(size=10),
                                 text_color=self.colors['text_light']).pack(side="left", padx=(0, 12))
                
                if payment_count > 0:
                    freq_text = f"🔄 {payment_count} payment{'s' if payment_count != 1 else ''}"
                    ctk.CTkLabel(row2, text=freq_text, font=ctk.CTkFont(size=10),
                                 text_color=self.colors['text_light']).pack(side="left", padx=(0, 12))
                
                # Row 3: First and last seen dates
                row3 = ctk.CTkFrame(card, fg_color="transparent")
                row3.pack(fill="x", padx=12, pady=2)
                
                if first_seen:
                    ctk.CTkLabel(row3, text=f"First: {first_seen[:10]}", font=ctk.CTkFont(size=9),
                                 text_color=self.colors['text_light']).pack(side="left", padx=(0, 12))
                
                if last_seen:
                    ctk.CTkLabel(row3, text=f"Last: {last_seen[:10]}", font=ctk.CTkFont(size=9),
                                 text_color=self.colors['text_light']).pack(side="left")
                
                # Row 4: Risk level and match strategy
                row4 = ctk.CTkFrame(card, fg_color="transparent")
                row4.pack(fill="x", padx=12, pady=(2, 2))
                
                risk = ex.get('risk_level', 'Low')
                risk_color = {'High': '#EF4444', 'Medium': '#F97316', 'Low': '#22C55E'}.get(risk, '#64748B')
                match_strategy = ex.get('match_strategy', 'none').replace('_', ' ').title()
                
                ctk.CTkLabel(row4, text=f"Risk: {risk}", font=ctk.CTkFont(size=10, weight="bold"),
                             text_color=risk_color).pack(side="left")
                
                # Show match strategy if it was matched (not exception)
                if match_strategy != 'None' and match_strategy != 'None':
                    strategy_color = {
                        'Exact': '#22C55E', 'Normalized': '#3B82F6', 'Token Sort': '#8B5CF6', 
                        'Partial': '#EC4899', 'Levenshtein': '#F59E0B', 'Phonetic': '#06B6D4',
                        'Obfuscation': '#EF4444'
                    }.get(match_strategy, '#64748B')
                    ctk.CTkLabel(row4, text=f"Matched: {match_strategy}", font=ctk.CTkFont(size=9),
                                 text_color=strategy_color).pack(side="left", padx=(8, 0))
                
                # Row 5: Risk reasons
                row5 = ctk.CTkFrame(card, fg_color="transparent")
                row5.pack(fill="x", padx=12, pady=(2, 10))
                
                reasons = ex.get('risk_reasons', [])
                if reasons:
                    reason_text = reasons[0][:40]
                    ctk.CTkLabel(row5, text=f"• {reason_text}", font=ctk.CTkFont(size=9),
                                 text_color=self.colors['text_light']).pack(side="left")
        else:
            ctk.CTkLabel(self.exceptions_frame, text="No exceptions found",
                         text_color=self.colors['text_light']).pack(pady=30)
        
        # Update trend chart
        self.update_trend_chart()
    
    def update_kpis(self, exceptions, spend, entropy, total):
        self.kpi_cards["Exceptions Found"].configure(text=f"{exceptions:,}")
        self.kpi_cards["Exception Spend"].configure(text=f"R {spend:,.0f}")
        self.kpi_cards["Control Entropy"].configure(text=f"{entropy:.1f}%")
        self.kpi_cards["Total Payments"].configure(text=f"{total:,}")
    
    def update_trend_chart(self):
        """Update trend chart with all historical data"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT entropy_score FROM analysis_history ORDER BY date ASC")
        rows = cursor.fetchall()
        conn.close()
        
        scores = [row[0] for row in rows]
        
        self.ax.clear()
        if scores:
            self.ax.plot(range(len(scores)), scores, marker='o', linewidth=2, color=self.colors['primary'],
                         markersize=6, markerfacecolor='white')
            self.ax.fill_between(range(len(scores)), scores, alpha=0.15, color=self.colors['primary'])
            self.ax.set_xticks(range(len(scores)))
            self.ax.set_xticklabels([f"{i+1}" for i in range(len(scores))], rotation=45, ha='right')
            self.ax.set_ylim(0, max(100, max(scores) + 10))
            self.ax.axhline(y=20, color=self.colors['warning'], linestyle='--', alpha=0.5)
            self.ax.axhline(y=40, color=self.colors['danger'], linestyle='--', alpha=0.5)
            self.ax.set_xlabel('Analysis #', fontsize=9, color=self.colors['text_light'])
            self.ax.set_ylabel('Entropy Score (%)', fontsize=9, color=self.colors['text_light'])
        else:
            self.ax.text(0.5, 0.5, "No data yet", ha='center', va='center',
                         fontsize=12, color=self.colors['text_light'])
            self.ax.set_ylim(0, 100)
        
        self.canvas.draw()
    
    def load_history(self):
        """Load history for trend chart"""
        self.update_trend_chart()
    
    def save_to_history(self, results, client_name, report_path):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        duplicate_count = len(results.get('duplicates', []))
        cursor.execute('''INSERT INTO analysis_history 
            (date, client_name, total_payments, exception_count, exception_spend, entropy_score, duplicate_count, report_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), client_name,
             results['total_payments'], results['exception_count'],
             results['exception_spend'], results['entropy_score'],
             duplicate_count, report_path))
        conn.commit()
        conn.close()
        
        # Refresh UI
        self.refresh_history_table()
        self.refresh_reports_list()
        self.update_trend_chart()
    
    def export_to_excel(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT date, client_name, total_payments, exception_count, exception_spend, entropy_score, duplicate_count FROM analysis_history")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            messagebox.showwarning("No Data", "No history to export")
            return
        
        df = pd.DataFrame(rows, columns=['Date', 'Client', 'Payments', 'Exceptions', 'Exception Spend', 'Entropy Score', 'Duplicates'])
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"payreality_history_{datetime.now().strftime('%Y%m%d')}"
        )
        
        if filepath:
            df.to_excel(filepath, index=False)
            self.log(f"Exported to Excel")
            messagebox.showinfo("Success", f"Exported to {filepath}")
    
    def open_report(self, path):
        if os.path.exists(path):
            os.startfile(path)
            self.log(f"Opened: {os.path.basename(path)}")
    
    def log(self, msg):
        if hasattr(self, 'status_text'):
            self.status_text.insert("end", f"{msg}\n")
            self.status_text.see("end")
            self.root.update()
    
    def run_analysis(self):
        if not self.master_file or not self.payments_file:
            return
        
        self.run_button.configure(state="disabled", text="Processing...")
        self.progress.set(0)
        self.status_text.delete("1.0", "end")
        
        thread = threading.Thread(target=self._run_analysis_thread)
        thread.daemon = True
        thread.start()
    
    def _run_analysis_thread(self):
        try:
            self.progress.set(0.1)
            self.log("Starting analysis...")
            
            dialog = ctk.CTkInputDialog(text="Enter client name:", title="Client")
            client_name = dialog.get_input() or "Client"
            
            self.progress.set(0.3)
            self.log("Loading files...")
            
            config = PayRealityConfig()
            engine = PayRealityEngine()
            results = engine.run_analysis(self.master_file, self.payments_file, batch_size=10000)
            
            self.progress.set(0.7)
            self.log(f"Found {results['exception_count']:,} exceptions")
            self.log(f"Control Entropy Score: {results['entropy_score']:.1f}%")
            
            # Show match statistics
            match_stats = results.get('match_stats', {})
            if match_stats:
                self.log("7-Pass Matching Results:")
                for strategy, count in sorted(match_stats.items(), key=lambda x: x[1], reverse=True):
                    if count > 0:
                        percentage = (count / results['total_payments'] * 100) if results['total_payments'] > 0 else 0
                        self.log(f"  {strategy.replace('_', ' ').title()}: {count:,} ({percentage:.1f}%)")
            
            # Store results
            self.current_results = results
            
            self.progress.set(0.8)
            self.log("Generating report...")
            
            reporter = PayRealityReport(client_name=client_name)
            report_path = reporter.generate_report(results, self.output_dir)
            self.log(f"Report saved to: {report_path}")
            
            self.progress.set(0.9)
            self.save_to_history(results, client_name, report_path)
            
            if self.email_var.get():
                self.log("Sending email...")
                self.send_email_report(report_path, client_name, results)
            
            self.progress.set(1.0)
            
            # Display results on dashboard
            self.root.after(0, lambda: self.display_results(results))
            
            self.log("Analysis complete")
            
            duplicate_count = len(results.get('duplicates', []))
            obfuscation_count = match_stats.get('obfuscation', 0)
            
            message_text = f"Control Entropy Score: {results['entropy_score']:.1f}%\n"
            message_text += f"Exceptions Found: {results['exception_count']:,}\n"
            message_text += f"Exception Spend: R {results['exception_spend']:,.2f}\n"
            message_text += f"Duplicates Found: {duplicate_count}\n"
            if obfuscation_count > 0:
                message_text += f"Obfuscation Detected: {obfuscation_count} payments\n"
            message_text += f"\nReport saved to:\n{report_path}"
            
            messagebox.showinfo("Complete", message_text)
            
        except DataValidationError as e:
            error_msg = str(e)
            if "Missing required columns" in error_msg:
                self.log(f"✗ File format error: {error_msg}")
                messagebox.showerror("File Format Error", 
                    "The file doesn't have the required columns.\n\n"
                    "Vendor Master needs: vendor_name\n"
                    "Payments need: payee_name and amount\n\n"
                    "Check the sample files in data/sample/ for reference.")
            else:
                self.log(f"✗ Error: {error_msg}")
                messagebox.showerror("Error", error_msg)
        except Exception as e:
            self.log(f"✗ Error: {str(e)}")
            messagebox.showerror("Error", str(e))
        
        finally:
            self.run_button.configure(state="normal", text="Run Analysis")
    
    def send_email_report(self, report_path, client_name, results):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT smtp_server, smtp_port, email_user, email_password, recipient_list FROM email_config LIMIT 1")
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
            
            match_stats = results.get('match_stats', {})
            obfuscation_count = match_stats.get('obfuscation', 0)
            
            body = f"""
PayReality Control Validation Report

Client: {client_name}
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Results:
- Control Entropy Score: {results['entropy_score']:.1f}%
- Total Payments: {results['total_payments']:,}
- Exceptions Found: {results['exception_count']:,}
- Exception Spend: R {results['exception_spend']:,.2f}
- Duplicate Vendors: {len(results.get('duplicates', []))}
- Obfuscation Detected: {obfuscation_count}

Full report attached.
"""
            msg.attach(MIMEText(body, 'plain'))
            
            with open(report_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(report_path)}")
                msg.attach(part)
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_user, email_password)
                server.send_message(msg)
            
            self.log(f"Email sent to {len(recipients)} recipient(s)")
        except Exception as e:
            self.log(f"Email failed: {str(e)}")
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PayRealityApp()
    app.run()