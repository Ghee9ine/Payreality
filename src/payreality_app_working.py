"""
PayReality Professional Desktop Application
Elegant Modern Design with Glassmorphism
"""

import sys
import os
import threading
import sqlite3
import smtplib
import csv
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

# Set theme and appearance - Modern Light with Elegant Accents
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.core import PayRealityEngine, DataValidationError
from src.reporting import PayRealityReport
from src.config import PayRealityConfig


class ModernCard(ctk.CTkFrame):
    """Elegant card with rounded corners and shadow effect"""
    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=24, **kwargs)
        self.configure(fg_color="white", border_width=0)


class PayRealityApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("PayReality")
        self.root.geometry("1400x900")
        self.root.minsize(1300, 800)
        
        # Elegant color palette
        self.colors = {
            'primary': "#6366F1",      # Indigo
            'primary_gradient': "#8B5CF6",  # Purple
            'secondary': "#06B6D4",    # Cyan
            'success': "#10B981",      # Emerald
            'danger': "#EF4444",       # Red
            'warning': "#F59E0B",      # Amber
            'info': "#3B82F6",         # Blue
            'bg': "#F9FAFB",           # Light gray background
            'card': "#FFFFFF",         # White cards
            'sidebar': "rgba(255,255,255,0.95)",  # Frosted white
            'text': "#111827",         # Dark gray
            'text_light': "#6B7280",   # Medium gray
            'border': "#E5E7EB",       # Light border
            'hover': "#F3F4F6",        # Hover state
            'gradient_start': "#6366F1",
            'gradient_end': "#8B5CF6"
        }
        
        # Data
        self.master_file = None
        self.payments_file = None
        self.output_dir = None
        self.current_report = None
        self.last_results = None
        self.history_data = []
        
        # Initialize database
        self.init_database()
        
        self.center_window()
        self.create_widgets()
        self.load_history()
        self.show_welcome_state()
        self.animate_entry()
    
    def init_database(self):
        db_path = Path.home() / "PayReality_Data" / "payreality.db"
        db_path.parent.mkdir(exist_ok=True)
        
        self.conn = sqlite3.connect(str(db_path))
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                client_name TEXT,
                total_payments INTEGER,
                exception_count INTEGER,
                exception_spend REAL,
                entropy_score REAL,
                vendor_count INTEGER,
                report_path TEXT
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_config (
                id INTEGER PRIMARY KEY,
                smtp_server TEXT,
                smtp_port INTEGER,
                email_user TEXT,
                email_password TEXT,
                recipient_list TEXT
            )
        ''')
        
        self.conn.commit()
    
    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def animate_entry(self):
        """Simple fade-in animation effect"""
        self.root.attributes('-alpha', 0)
        def fade_in(alpha=0):
            if alpha <= 1:
                self.root.attributes('-alpha', alpha)
                self.root.after(20, fade_in, alpha + 0.05)
        fade_in()
    
    def create_widgets(self):
        # Main container with gradient background
        self.main_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg'])
        self.main_frame.pack(fill="both", expand=True)
        
        # Header with gradient
        self.create_header()
        
        # Notebook with modern styling
        self.notebook = ctk.CTkTabview(self.main_frame, corner_radius=16, segmented_button_selected_color=self.colors['primary'])
        self.notebook.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        
        # Add tabs with icons
        self.dashboard_tab = self.notebook.add("✨ Dashboard")
        self.history_tab = self.notebook.add("📊 History")
        self.reports_tab = self.notebook.add("📄 Reports")
        self.settings_tab = self.notebook.add("⚙️ Settings")
        
        self.create_dashboard_tab()
        self.create_history_tab()
        self.create_reports_tab()
        self.create_settings_tab()
    
    def create_header(self):
        """Create elegant header with gradient and glass effect"""
        header = ctk.CTkFrame(self.main_frame, height=80, fg_color="white", corner_radius=0)
        header.pack(fill="x", pady=(0, 16))
        
        # Gradient effect using canvas
        content = ctk.CTkFrame(header, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=32, pady=16)
        
        # Logo and title
        title_frame = ctk.CTkFrame(content, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(
            title_frame,
            text="PayReality",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.colors['primary']
        ).pack(side="left")
        
        ctk.CTkLabel(
            title_frame,
            text="v2.0",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_light']
        ).pack(side="left", padx=(8, 0))
        
        ctk.CTkLabel(
            title_frame,
            text="Independent Control Validation",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_light']
        ).pack(side="left", padx=(12, 0))
        
        # Status indicator
        status_frame = ctk.CTkFrame(content, fg_color="transparent")
        status_frame.pack(side="right")
        
        self.status_indicator = ctk.CTkLabel(
            status_frame,
            text="● Ready",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['success']
        )
        self.status_indicator.pack()
    
    def create_dashboard_tab(self):
        # Scrollable frame for dashboard
        scroll_frame = ctk.CTkScrollableFrame(self.dashboard_tab, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Welcome banner
        welcome_card = ModernCard(scroll_frame)
        welcome_card.pack(fill="x", pady=(0, 24))
        
        welcome_frame = ctk.CTkFrame(welcome_card, fg_color="transparent")
        welcome_frame.pack(padx=24, pady=24)
        
        ctk.CTkLabel(
            welcome_frame,
            text="Welcome to PayReality",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.colors['text']
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            welcome_frame,
            text="Independent control validation for your payment processes",
            font=ctk.CTkFont(size=14),
            text_color=self.colors['text_light']
        ).pack(anchor="w", pady=(4, 0))
        
        # KPI Cards Row
        self.create_kpi_row(scroll_frame)
        
        # Two-column layout
        content = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        content.pack(fill="both", expand=True, pady=(24, 0))
        
        # Left column - Trend Chart
        left = ctk.CTkFrame(content, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        self.create_trend_chart(left)
        
        # Right column - File Selection & Exceptions
        right = ctk.CTkFrame(content, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True, padx=(12, 0))
        self.create_file_section(right)
        self.create_exceptions_list(right)
    
    def create_kpi_row(self, parent):
        kpi_frame = ctk.CTkFrame(parent, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=(0, 24))
        
        self.kpi_cards = {}
        kpis = [
            ("Exceptions Found", "0", self.colors['danger'], "⚠️"),
            ("Exception Spend", "R 0", self.colors['warning'], "💰"),
            ("Control Entropy", "0%", self.colors['primary'], "📈"),
            ("Total Payments", "0", self.colors['info'], "💳")
        ]
        
        for title, value, color, icon in kpis:
            card = ModernCard(kpi_frame)
            card.pack(side="left", fill="both", expand=True, padx=6)
            
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(padx=20, pady=20)
            
            ctk.CTkLabel(
                content,
                text=f"{icon} {title}",
                font=ctk.CTkFont(size=12),
                text_color=self.colors['text_light']
            ).pack()
            
            value_label = ctk.CTkLabel(
                content,
                text=value,
                font=ctk.CTkFont(size=28, weight="bold"),
                text_color=color
            )
            value_label.pack(pady=(8, 0))
            
            self.kpi_cards[title] = value_label
    
    def create_trend_chart(self, parent):
        card = ModernCard(parent)
        card.pack(fill="both", expand=True)
        
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 12))
        
        ctk.CTkLabel(
            header,
            text="📈 Control Entropy Trend",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors['text']
        ).pack(side="left")
        
        ctk.CTkLabel(
            header,
            text="Last 12 months",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_light']
        ).pack(side="right")
        
        # Matplotlib figure with modern styling
        self.figure = Figure(figsize=(7, 3.5), dpi=100, facecolor='white')
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#F9FAFB')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.grid(True, linestyle='--', alpha=0.5)
        self.ax.set_xlabel('Date', fontsize=9, color='#6B7280')
        self.ax.set_ylabel('Entropy Score (%)', fontsize=9, color='#6B7280')
        
        self.canvas = FigureCanvasTkAgg(self.figure, master=card)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=(0, 20))
    
    def create_file_section(self, parent):
        card = ModernCard(parent)
        card.pack(fill="x", pady=(0, 16))
        
        ctk.CTkLabel(
            card,
            text="🎯 Control Test",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors['text']
        ).pack(anchor="w", padx=20, pady=(20, 16))
        
        # File selection area
        self.master_status = ctk.CTkLabel(
            card,
            text="📁 Vendor Master: Not selected",
            font=ctk.CTkFont(size=13),
            text_color=self.colors['text_light']
        )
        self.master_status.pack(anchor="w", padx=20, pady=4)
        
        ctk.CTkButton(
            card,
            text="Browse",
            command=lambda: self.select_file("master"),
            width=120,
            height=36,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_gradient'],
            corner_radius=12
        ).pack(anchor="w", padx=20, pady=4)
        
        self.payments_status = ctk.CTkLabel(
            card,
            text="📄 Payments: Not selected",
            font=ctk.CTkFont(size=13),
            text_color=self.colors['text_light']
        )
        self.payments_status.pack(anchor="w", padx=20, pady=(12, 4))
        
        ctk.CTkButton(
            card,
            text="Browse",
            command=lambda: self.select_file("payments"),
            width=120,
            height=36,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_gradient'],
            corner_radius=12
        ).pack(anchor="w", padx=20, pady=4)
        
        # Email option
        self.email_var = ctk.BooleanVar(value=False)
        email_check = ctk.CTkCheckBox(
            card,
            text="📧 Email report after analysis",
            variable=self.email_var,
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text']
        )
        email_check.pack(anchor="w", padx=20, pady=(16, 12))
        
        # Run button
        self.run_button = ctk.CTkButton(
            card,
            text="▶ RUN ANALYSIS",
            command=self.run_analysis,
            height=48,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_gradient'],
            corner_radius=16,
            state="disabled"
        )
        self.run_button.pack(fill="x", padx=20, pady=(8, 16))
        
        # Progress
        self.progress = ctk.CTkProgressBar(
            card,
            height=4,
            corner_radius=2,
            fg_color=self.colors['border'],
            progress_color=self.colors['primary']
        )
        self.progress.pack(fill="x", padx=20, pady=(0, 16))
        self.progress.set(0)
        
        # Status text
        self.status_text = ctk.CTkTextbox(
            card,
            height=100,
            font=ctk.CTkFont(size=11),
            fg_color="#F9FAFB",
            border_width=0,
            corner_radius=12
        )
        self.status_text.pack(fill="x", padx=20, pady=(0, 20))
    
    def create_exceptions_list(self, parent):
        card = ModernCard(parent)
        card.pack(fill="both", expand=True)
        
        ctk.CTkLabel(
            card,
            text="🚨 Unapproved Vendors",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors['text']
        ).pack(anchor="w", padx=20, pady=(20, 12))
        
        self.exceptions_list = ctk.CTkScrollableFrame(
            card,
            fg_color="transparent",
            height=200
        )
        self.exceptions_list.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.exceptions_placeholder = ctk.CTkLabel(
            self.exceptions_list,
            text="✨ No exceptions yet. Run analysis to identify control gaps.",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_light']
        )
        self.exceptions_placeholder.pack(pady=40)
    
    def create_history_tab(self):
        frame = ctk.CTkFrame(self.history_tab, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header with export button
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        
        ctk.CTkLabel(
            header,
            text="📊 Analysis History",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.colors['text']
        ).pack(side="left")
        
        export_btn = ctk.CTkButton(
            header,
            text="📎 Export to Excel",
            command=self.export_to_excel,
            fg_color=self.colors['success'],
            hover_color="#059669",
            height=36,
            corner_radius=12
        )
        export_btn.pack(side="right")
        
        # Table
        card = ModernCard(frame)
        card.pack(fill="both", expand=True)
        
        from tkinter import ttk
        columns = ("Date", "Client", "Total Payments", "Exceptions", "Exception Spend", "Entropy Score")
        self.tree = ttk.Treeview(card, columns=columns, show="headings", height=15, style="Treeview")
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")
        
        scrollbar = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        scrollbar.pack(side="right", fill="y", pady=20)
    
    def create_reports_tab(self):
        frame = ctk.CTkFrame(self.reports_tab, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        card = ModernCard(frame)
        card.pack(fill="both", expand=True)
        
        ctk.CTkLabel(
            card,
            text="📄 Generated Reports",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors['text']
        ).pack(anchor="w", padx=20, pady=(20, 12))
        
        self.reports_list = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self.reports_list.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.reports_placeholder = ctk.CTkLabel(
            self.reports_list,
            text="📭 No reports yet. Run analysis to generate reports.",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_light']
        )
        self.reports_placeholder.pack(pady=40)
    
    def create_settings_tab(self):
        frame = ctk.CTkFrame(self.settings_tab, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        card = ModernCard(frame)
        card.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            card,
            text="✉️ Email Configuration",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors['text']
        ).pack(anchor="w", padx=20, pady=(20, 16))
        
        # Settings fields
        settings = [
            ("SMTP Server", "smtp.gmail.com", self.smtp_entry),
            ("Port", "587", self.port_entry),
            ("Email Address", "", self.email_user_entry),
            ("Password", "", self.email_pass_entry),
            ("Recipients (comma separated)", "", self.recipients_entry)
        ]
        
        for label, placeholder, attr in settings:
            frame_row = ctk.CTkFrame(card, fg_color="transparent")
            frame_row.pack(fill="x", padx=20, pady=6)
            
            ctk.CTkLabel(
                frame_row,
                text=label,
                width=120,
                font=ctk.CTkFont(size=12),
                text_color=self.colors['text']
            ).pack(side="left")
            
            entry = ctk.CTkEntry(
                frame_row,
                width=300,
                placeholder_text=placeholder,
                corner_radius=8,
                border_color=self.colors['border']
            )
            entry.pack(side="left", padx=10)
            
            # Store entry reference
            if label == "SMTP Server":
                self.smtp_entry = entry
            elif label == "Port":
                self.port_entry = entry
            elif label == "Email Address":
                self.email_user_entry = entry
            elif label == "Password":
                self.email_pass_entry = entry
                entry.configure(show="•")
            elif label == "Recipients (comma separated)":
                self.recipients_entry = entry
        
        # Save button
        save_btn = ctk.CTkButton(
            card,
            text="Save Settings",
            command=self.save_email_settings,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_gradient'],
            height=40,
            corner_radius=12
        )
        save_btn.pack(pady=(20, 20))
        
        self.load_email_settings()
    
    def load_email_settings(self):
        self.cursor.execute("SELECT smtp_server, smtp_port, email_user, email_password, recipient_list FROM email_config LIMIT 1")
        row = self.cursor.fetchone()
        if row:
            self.smtp_entry.insert(0, row[0] or "")
            self.port_entry.insert(0, str(row[1] or ""))
            self.email_user_entry.insert(0, row[2] or "")
            self.email_pass_entry.insert(0, row[3] or "")
            self.recipients_entry.insert(0, row[4] or "")
    
    def save_email_settings(self):
        self.cursor.execute("DELETE FROM email_config")
        self.cursor.execute('''
            INSERT INTO email_config (smtp_server, smtp_port, email_user, email_password, recipient_list)
            VALUES (?, ?, ?, ?, ?)
        ''', (self.smtp_entry.get(), int(self.port_entry.get() or 587),
              self.email_user_entry.get(), self.email_pass_entry.get(),
              self.recipients_entry.get()))
        self.conn.commit()
        self.status_indicator.configure(text="● Settings saved", text_color=self.colors['success'])
        self.root.after(2000, lambda: self.status_indicator.configure(text="● Ready", text_color=self.colors['success']))
        messagebox.showinfo("Success", "Email settings saved")
    
    def select_file(self, file_type):
        filetypes = [("CSV/Excel/PDF", "*.csv *.xlsx *.xls *.pdf"), ("All files", "*.*")]
        title = "Select Vendor Master" if file_type == "master" else "Select Payments"
        filepath = filedialog.askopenfilename(title=title, filetypes=filetypes)
        
        if filepath:
            if file_type == "master":
                self.master_file = filepath
                self.master_status.configure(text=f"📁 Vendor Master: {os.path.basename(filepath)}", text_color=self.colors['success'])
            else:
                self.payments_file = filepath
                self.payments_status.configure(text=f"📄 Payments: {os.path.basename(filepath)}", text_color=self.colors['success'])
            
            if self.master_file and self.payments_file:
                self.run_button.configure(state="normal")
                if not self.output_dir:
                    self.output_dir = str(Path.home() / "Desktop" / "PayReality_Reports")
                    os.makedirs(self.output_dir, exist_ok=True)
    
    def show_welcome_state(self):
        self.update_kpis(0, 0, 0, 0)
        self.status_text.insert("1.0", "✨ Ready. Select files to test payment controls.\n")
    
    def update_kpis(self, exceptions, exception_spend, entropy, total_payments):
        self.kpi_cards["Exceptions Found"].configure(text=f"{exceptions:,}")
        self.kpi_cards["Exception Spend"].configure(text=f"R {exception_spend:,.0f}")
        self.kpi_cards["Control Entropy"].configure(text=f"{entropy:.1f}%")
        self.kpi_cards["Total Payments"].configure(text=f"{total_payments:,}")
    
    def update_exceptions_list(self, exceptions):
        for widget in self.exceptions_list.winfo_children():
            widget.destroy()
        
        if not exceptions:
            ctk.CTkLabel(
                self.exceptions_list,
                text="✨ No control exceptions found",
                font=ctk.CTkFont(size=12),
                text_color=self.colors['text_light']
            ).pack(pady=40)
            return
        
        for ex in exceptions[:5]:
            item = ctk.CTkFrame(self.exceptions_list, fg_color=self.colors['hover'], corner_radius=12)
            item.pack(fill="x", pady=4)
            
            name = ex.get('payee_name', 'Unknown')[:35]
            amount = ex.get('amount', 0)
            
            ctk.CTkLabel(
                item,
                text=name,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=self.colors['text']
            ).pack(side="left", padx=16, pady=12)
            
            ctk.CTkLabel(
                item,
                text=f"R {amount:,.0f}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=self.colors['warning']
            ).pack(side="right", padx=16)
    
    def update_trend_chart(self):
        if not self.history_data:
            self.ax.clear()
            self.ax.text(0.5, 0.5, "No data yet. Run analysis to see trends.",
                        ha='center', va='center', transform=self.ax.transAxes,
                        fontsize=12, color='#6B7280')
            self.canvas.draw()
            return
        
        dates = [datetime.strptime(d[0], "%Y-%m-%d") for d in self.history_data[-12:]]
        entropy_scores = [d[4] for d in self.history_data[-12:]]
        
        self.ax.clear()
        self.ax.plot(dates, entropy_scores, marker='o', linewidth=2, 
                    color=self.colors['primary'], markersize=6, markerfacecolor='white',
                    markeredgewidth=2, markeredgecolor=self.colors['primary'])
        
        self.ax.fill_between(dates, entropy_scores, alpha=0.2, color=self.colors['primary'])
        self.ax.set_xlabel('Date', fontsize=9, color='#6B7280')
        self.ax.set_ylabel('Entropy Score (%)', fontsize=9, color='#6B7280')
        self.ax.grid(True, linestyle='--', alpha=0.5)
        self.ax.axhline(y=20, color='#F59E0B', linestyle='--', alpha=0.7, linewidth=1)
        self.ax.axhline(y=40, color='#EF4444', linestyle='--', alpha=0.7, linewidth=1)
        
        self.canvas.draw()
    
    def load_history(self):
        self.cursor.execute('''
            SELECT date, client_name, total_payments, exception_count, exception_spend, entropy_score, report_path
            FROM analysis_history ORDER BY date DESC
        ''')
        rows = self.cursor.fetchall()
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.history_data = []
        
        for widget in self.reports_list.winfo_children():
            widget.destroy()
        
        if not rows:
            placeholder = ctk.CTkLabel(
                self.reports_list,
                text="📭 No reports yet. Run analysis to generate reports.",
                font=ctk.CTkFont(size=12),
                text_color=self.colors['text_light']
            )
            placeholder.pack(pady=40)
        else:
            for row in rows:
                self.tree.insert("", "end", values=(
                    row[0], row[1], f"{row[2]:,}", f"{row[3]:,}",
                    f"R {row[4]:,.0f}", f"{row[5]:.1f}%"
                ))
                self.history_data.append((row[0], row[1], row[2], row[3], row[5]))
                
                if row[6] and os.path.exists(row[6]):
                    report_item = ctk.CTkFrame(self.reports_list, fg_color=self.colors['hover'], corner_radius=12)
                    report_item.pack(fill="x", pady=4)
                    
                    ctk.CTkLabel(
                        report_item,
                        text=f"📄 {row[0]} - {row[1]}",
                        font=ctk.CTkFont(size=12),
                        text_color=self.colors['text']
                    ).pack(side="left", padx=16, pady=12)
                    
                    ctk.CTkButton(
                        report_item,
                        text="Open",
                        width=80,
                        height=32,
                        command=lambda p=row[6]: self.open_report(p),
                        fg_color=self.colors['primary'],
                        hover_color=self.colors['primary_gradient'],
                        corner_radius=8
                    ).pack(side="right", padx=16)
        
        self.history_data.sort(key=lambda x: x[0])
        self.update_trend_chart()
    
    def save_to_history(self, results, client_name, report_path):
        self.cursor.execute('''
            INSERT INTO analysis_history (date, client_name, total_payments, exception_count, exception_spend, entropy_score, report_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              client_name, results['total_payments'], results['exception_count'],
              results['exception_spend'], results['entropy_score'], report_path))
        self.conn.commit()
        self.load_history()
    
    def send_report_email(self, report_path, client_name, results):
        try:
            self.cursor.execute("SELECT smtp_server, smtp_port, email_user, email_password, recipient_list FROM email_config LIMIT 1")
            config = self.cursor.fetchone()
            
            if not config or not all(config):
                self.log("📧 Email not sent: No email configuration found")
                return
            
            smtp_server, smtp_port, email_user, email_password, recipient_list = config
            recipients = [r.strip() for r in recipient_list.split(',')]
            
            msg = MIMEMultipart()
            msg['Subject'] = f"PayReality Report - {client_name}"
            msg['From'] = email_user
            msg['To'] = ", ".join(recipients)
            
            body = f"""
            PayReality Control Validation Report
            
            Client: {client_name}
            Analysis Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            
            Results:
            • Control Entropy Score: {results['entropy_score']:.1f}%
            • Total Payments: {results['total_payments']:,}
            • Exceptions Found: {results['exception_count']:,}
            • Exception Spend: R {results['exception_spend']:,.2f}
            
            Full report attached.
            
            --
            PayReality by AI Securewatch
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
            
            self.log(f"📧 Report emailed to {', '.join(recipients)}")
        except Exception as e:
            self.log(f"✗ Email failed: {str(e)}")
    
    def export_to_excel(self):
        self.cursor.execute('''
            SELECT date, client_name, total_payments, exception_count, exception_spend, entropy_score
            FROM analysis_history ORDER BY date DESC
        ''')
        rows = self.cursor.fetchall()
        
        if not rows:
            messagebox.showwarning("No Data", "No analysis history to export")
            return
        
        df = pd.DataFrame(rows, columns=['Date', 'Client', 'Total Payments', 'Exceptions', 'Exception Spend', 'Entropy Score'])
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"payreality_history_{datetime.now().strftime('%Y%m%d')}"
        )
        
        if filepath:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='History', index=False)
                
                # Add summary
                summary = df.groupby('Client').agg({
                    'Entropy Score': ['mean', 'max', 'min', 'count'],
                    'Exceptions': 'sum',
                    'Exception Spend': 'sum'
                }).round(2)
                summary.to_excel(writer, sheet_name='Client_Summary')
            
            self.log(f"📎 Exported to Excel: {filepath}")
            messagebox.showinfo("Export Complete", f"Data exported to:\n{filepath}")
    
    def open_report(self, report_path):
        if os.path.exists(report_path):
            os.startfile(report_path)
            self.log(f"📄 Opened report: {os.path.basename(report_path)}")
    
    def log(self, message):
        self.status_text.insert("end", f"{message}\n")
        self.status_text.see("end")
        self.root.update()
    
    def run_analysis(self):
        if not self.master_file or not self.payments_file:
            messagebox.showwarning("Missing Files", "Please select both files")
            return
        
        self.run_button.configure(state="disabled", text="⏳ PROCESSING...")
        self.progress.set(0)
        self.status_text.delete("1.0", "end")
        self.status_indicator.configure(text="● Processing", text_color=self.colors['warning'])
        
        thread = threading.Thread(target=self._run_analysis_thread)
        thread.daemon = True
        thread.start()
    
    def _run_analysis_thread(self):
        try:
            self.progress.set(0.1)
            self.log("✨ Starting PayReality Analysis")
            
            dialog = ctk.CTkInputDialog(text="Enter client name:", title="Client Information")
            client_name = dialog.get_input() or "Client"
            
            self.progress.set(0.3)
            self.log("📊 Loading files & running semantic matching...")
            
            config = PayRealityConfig()
            engine = PayRealityEngine()
            
            results = engine.run_analysis(self.master_file, self.payments_file, batch_size=10000)
            
            self.progress.set(0.7)
            self.log(f"✓ Found {results['exception_count']:,} control exceptions")
            self.log(f"✓ Control Entropy Score: {results['entropy_score']:.1f}%")
            
            self.update_kpis(results['exception_count'], results['exception_spend'],
                            results['entropy_score'], results['total_payments'])
            
            exceptions = []
            if results.get('exceptions'):
                for ex in results['exceptions'][:10]:
                    exceptions.append({
                        'payee_name': ex.get('payee_name', 'Unknown'),
                        'amount': ex.get('amount', 0)
                    })
            
            self.root.after(0, lambda: self.update_exceptions_list(exceptions))
            
            self.progress.set(0.8)
            self.log("📄 Generating PDF report...")
            
            reporter = PayRealityReport(client_name=client_name)
            report_path = reporter.generate_report(results, 
                self.output_dir or str(Path.home() / "Desktop" / "PayReality_Reports"))
            
            self.progress.set(0.9)
            self.log("💾 Saving to history...")
            self.save_to_history(results, client_name, report_path)
            
            self.progress.set(1.0)
            self.log("✨ ANALYSIS COMPLETE")
            self.log(f"📄 Report: {report_path}")
            
            self.last_results = results
            self.current_report = report_path
            
            if self.email_var.get():
                self.log("📧 Sending email report...")
                self.send_report_email(report_path, client_name, results)
            
            self.save_history_csv(results, client_name)
            
            self.root.after(0, lambda: messagebox.showinfo(
                "Analysis Complete",
                f"✨ Control Entropy Score: {results['entropy_score']:.1f}%\n"
                f"📊 Exceptions Found: {results['exception_count']:,}\n"
                f"💰 Exception Spend: R {results['exception_spend']:,.2f}"
            ))
            
        except Exception as e:
            self.log(f"✗ ERROR: {str(e)}")
            messagebox.showerror("Error", str(e))
        
        finally:
            self.root.after(0, lambda: self.run_button.configure(state="normal", text="▶ RUN ANALYSIS"))
            self.root.after(0, lambda: self.status_indicator.configure(text="● Ready", text_color=self.colors['success']))
    
    def save_history_csv(self, results, client_name):
        history_file = os.path.join(self.output_dir or str(Path.home() / "Desktop"), "payreality_history.csv")
        file_exists = os.path.isfile(history_file)
        
        with open(history_file, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Date", "Client", "Total Payments", "Exceptions", 
                                "Exception Spend", "Control Entropy Score"])
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                client_name,
                results['total_payments'],
                results['exception_count'],
                results['exception_spend'],
                results['entropy_score']
            ])
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PayRealityApp()
    app.run()