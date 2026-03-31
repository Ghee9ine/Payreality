"""
PayReality Professional Desktop Application
Audit Dashboard - Independent Control Validation
"""

import sys
import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
import pandas as pd
from datetime import datetime
from pathlib import Path

# Set theme and appearance
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core import PayRealityEngine, DataValidationError
from src.reporting import PayRealityReport
from src.config import PayRealityConfig


class PayRealityApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("PayReality | AI Securewatch")
        self.root.geometry("1300x800")
        self.root.minsize(1200, 700)
        
        # Light blue & white professional colors
        self.colors = {
            'primary': "#1E88E5",
            'primary_light': "#E3F2FD",
            'primary_dark': "#0D47A1",
            'success': "#2E7D32",
            'danger': "#C62828",
            'warning': "#ED6C02",
            'info': "#0288D1",
            'bg': "#FFFFFF",
            'card_bg': "#FFFFFF",
            'sidebar_bg': "#F8F9FA",
            'text': "#1A1A1A",
            'text_muted': "#6B7280",
            'border': "#E5E7EB",
            'hover': "#F3F4F6"
        }
        
        # Data
        self.master_file = None
        self.payments_file = None
        self.output_dir = None
        self.current_report = None
        self.last_results = None
        
        self.center_window()
        self.create_widgets()
        self.show_welcome_state()
    
    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        # Main container
        self.main_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg'])
        self.main_frame.pack(fill="both", expand=True)
        
        # Header
        self.create_header()
        
        # Two-column layout
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        
        # Left column - KPI Cards & Exceptions
        self.left_column = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.left_column.pack(side="left", fill="both", expand=True, padx=(0, 12))
        
        # Right column - Action Items & File Selection
        self.right_column = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.right_column.pack(side="right", fill="both", expand=True, padx=(12, 0))
        
        # Create dashboard sections
        self.create_kpi_row()
        self.create_exceptions_list()
        self.create_action_items()
        self.create_file_section()
    
    def create_header(self):
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=60)
        header.pack(fill="x", padx=24, pady=(16, 8))
        
        ctk.CTkLabel(
            header,
            text="PayReality",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.colors['primary']
        ).pack(side="left")
        
        ctk.CTkLabel(
            header,
            text="AI Securewatch",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_muted']
        ).pack(side="left", padx=(8, 0))
        
        ctk.CTkLabel(
            header,
            text="Independent Control Validation",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_muted']
        ).pack(side="right")
    
    def create_kpi_row(self):
        self.kpi_frame = ctk.CTkFrame(self.left_column, fg_color="transparent")
        self.kpi_frame.pack(fill="x", pady=(0, 16))
        
        self.kpi_cards = {}
        kpis = [
            ("Exceptions Found", "0", self.colors['danger']),
            ("Exception Spend", "R 0", self.colors['warning']),
            ("Control Entropy", "0%", self.colors['primary']),
            ("Total Payments", "0", self.colors['info'])
        ]
        
        for i, (title, value, color) in enumerate(kpis):
            card = ctk.CTkFrame(self.kpi_frame, fg_color=self.colors['card_bg'], 
                                corner_radius=12, border_width=1, border_color=self.colors['border'])
            card.pack(side="left", fill="both", expand=True, padx=4)
            
            ctk.CTkLabel(
                card, text=title,
                font=ctk.CTkFont(size=12),
                text_color=self.colors['text_muted']
            ).pack(pady=(12, 4))
            
            value_label = ctk.CTkLabel(
                card, text=value,
                font=ctk.CTkFont(size=28, weight="bold"),
                text_color=color
            )
            value_label.pack()
            
            subtitle = "from vendor master" if "Exceptions" in title else ""
            ctk.CTkLabel(
                card, text=subtitle,
                font=ctk.CTkFont(size=10),
                text_color=self.colors['text_muted']
            ).pack(pady=(4, 12))
            
            self.kpi_cards[title] = value_label
    
    def create_exceptions_list(self):
        card = ctk.CTkFrame(self.left_column, fg_color=self.colors['card_bg'],
                           corner_radius=12, border_width=1, border_color=self.colors['border'])
        card.pack(fill="both", expand=True)
        
        # Header
        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(16, 8))
        
        ctk.CTkLabel(
            header_frame, text="Unapproved Vendors",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors['text']
        ).pack(side="left")
        
        ctk.CTkLabel(
            header_frame, text="Payments to vendors not in master",
            font=ctk.CTkFont(size=11),
            text_color=self.colors['text_muted']
        ).pack(side="left", padx=(8, 0))
        
        # List frame
        self.exceptions_list = ctk.CTkScrollableFrame(card, fg_color="transparent", height=280)
        self.exceptions_list.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        # Placeholder
        self.exceptions_placeholder = ctk.CTkLabel(
            self.exceptions_list,
            text="Run analysis to identify control gaps",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_muted']
        )
        self.exceptions_placeholder.pack(pady=20)
    
    def create_action_items(self):
        card = ctk.CTkFrame(self.right_column, fg_color=self.colors['card_bg'],
                           corner_radius=12, border_width=1, border_color=self.colors['border'])
        card.pack(fill="x", pady=(0, 16))
        
        ctk.CTkLabel(
            card, text="Control Testing",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors['text']
        ).pack(anchor="w", padx=16, pady=(16, 8))
        
        self.actions_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.actions_frame.pack(fill="x", padx=16, pady=(0, 16))
        
        self.action_items = []
        default_actions = [
            ("📊 Select Vendor Master", "browse_master"),
            ("📄 Select Payment Transactions", "browse_payments"),
            ("▶ Test Control", "run")
        ]
        
        for text, action in default_actions:
            self.add_action_item(text, action)
    
    def add_action_item(self, text, action):
        item_frame = ctk.CTkFrame(self.actions_frame, fg_color=self.colors['hover'], corner_radius=8)
        item_frame.pack(fill="x", pady=4)
        
        ctk.CTkLabel(
            item_frame, text=text,
            font=ctk.CTkFont(size=13),
            text_color=self.colors['text']
        ).pack(side="left", padx=12, pady=10)
        
        btn = ctk.CTkButton(
            item_frame, text="→",
            width=32, height=28,
            fg_color="transparent",
            text_color=self.colors['primary'],
            hover_color=self.colors['border'],
            font=ctk.CTkFont(size=14, weight="bold"),
            command=lambda a=action: self.execute_action(a)
        )
        btn.pack(side="right", padx=8)
        
        self.action_items.append((item_frame, btn, text))
    
    def execute_action(self, action):
        if action == "browse_master":
            self.select_file("master")
        elif action == "browse_payments":
            self.select_file("payments")
        elif action == "run":
            self.run_analysis()
    
    def create_file_section(self):
        card = ctk.CTkFrame(self.right_column, fg_color=self.colors['card_bg'],
                           corner_radius=12, border_width=1, border_color=self.colors['border'])
        card.pack(fill="x")
        
        ctk.CTkLabel(
            card, text="Control Test Configuration",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors['text']
        ).pack(anchor="w", padx=16, pady=(16, 8))
        
        self.master_status = ctk.CTkLabel(
            card, text="Vendor Master: ❌ Not selected",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_muted'],
            anchor="w"
        )
        self.master_status.pack(fill="x", padx=16, pady=4)
        
        self.payments_status = ctk.CTkLabel(
            card, text="Payments: ❌ Not selected",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_muted'],
            anchor="w"
        )
        self.payments_status.pack(fill="x", padx=16, pady=4)
        
        self.output_status = ctk.CTkLabel(
            card, text="Report Output: Desktop",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_muted'],
            anchor="w"
        )
        self.output_status.pack(fill="x", padx=16, pady=(4, 16))
        
        # Progress bar
        self.progress = ctk.CTkProgressBar(card, height=6, corner_radius=3,
                                           fg_color=self.colors['border'],
                                           progress_color=self.colors['primary'])
        self.progress.pack(fill="x", padx=16, pady=(0, 16))
        self.progress.set(0)
        
        # Status text
        self.status_text = ctk.CTkTextbox(card, height=80, font=ctk.CTkFont(size=11),
                                          fg_color=self.colors['bg'],
                                          text_color=self.colors['text'],
                                          border_width=1,
                                          border_color=self.colors['border'])
        self.status_text.pack(fill="x", padx=16, pady=(0, 16))
    
    def show_welcome_state(self):
        self.update_kpis(0, 0, 0, 0)
        self.status_text.insert("1.0", "Ready. Select files to test payment controls.\n")
    
    def select_file(self, file_type):
        filetypes = [("CSV/Excel/PDF", "*.csv *.xlsx *.xls *.pdf"), ("All files", "*.*")]
        title = "Select Vendor Master" if file_type == "master" else "Select Payments"
        filepath = filedialog.askopenfilename(title=title, filetypes=filetypes)
        
        if filepath:
            if file_type == "master":
                self.master_file = filepath
                self.master_status.configure(text=f"Vendor Master: ✅ {os.path.basename(filepath)}", 
                                            text_color=self.colors['success'])
            else:
                self.payments_file = filepath
                self.payments_status.configure(text=f"Payments: ✅ {os.path.basename(filepath)}",
                                              text_color=self.colors['success'])
            
            self.status_text.insert("end", f"✓ Selected {os.path.basename(filepath)}\n")
            self.status_text.see("end")
    
    def update_kpis(self, exceptions, exception_spend, entropy, total_payments):
        self.kpi_cards["Exceptions Found"].configure(text=f"{exceptions:,}")
        self.kpi_cards["Exception Spend"].configure(text=f"R {exception_spend:,.0f}")
        self.kpi_cards["Control Entropy"].configure(text=f"{entropy:.1f}%")
        self.kpi_cards["Total Payments"].configure(text=f"{total_payments:,}")
    
    def update_exceptions_list(self, exceptions):
        # Clear placeholder
        for widget in self.exceptions_list.winfo_children():
            widget.destroy()
        
        if not exceptions:
            ctk.CTkLabel(
                self.exceptions_list,
                text="No control exceptions found",
                font=ctk.CTkFont(size=12),
                text_color=self.colors['text_muted']
            ).pack(pady=20)
            return
        
        for ex in exceptions[:5]:
            item = ctk.CTkFrame(self.exceptions_list, fg_color=self.colors['hover'], corner_radius=8)
            item.pack(fill="x", pady=2)
            
            name = ex['payee_name'][:35]
            amount = ex['amount']
            
            ctk.CTkLabel(
                item, text=name,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=self.colors['text']
            ).pack(side="left", padx=12, pady=10)
            
            ctk.CTkLabel(
                item, text=f"R {amount:,.0f}",
                font=ctk.CTkFont(size=12),
                text_color=self.colors['warning']
            ).pack(side="right", padx=12)
    
    def run_analysis(self):
        if not self.master_file or not self.payments_file:
            messagebox.showwarning("Missing Files", "Please select both Vendor Master and Payments files.")
            return
        
        self.status_text.delete("1.0", "end")
        self.progress.set(0)
        
        thread = threading.Thread(target=self._run_analysis_thread)
        thread.daemon = True
        thread.start()
    
    def _run_analysis_thread(self):
        try:
            self.progress.set(0.1)
            self.status_text.insert("end", "Starting control test...\n")
            
            dialog = ctk.CTkInputDialog(text="Enter client name:", title="Client")
            client_name = dialog.get_input() or "Client"
            
            self.progress.set(0.3)
            self.status_text.insert("end", "Loading files & running semantic matching...\n")
            
            config = PayRealityConfig()
            engine = PayRealityEngine()
            
            results = engine.run_analysis(self.master_file, self.payments_file, batch_size=10000)
            
            self.progress.set(0.7)
            self.status_text.insert("end", f"✓ Found {results['exception_count']:,} control exceptions\n")
            self.status_text.insert("end", f"✓ Control Entropy Score: {results['entropy_score']:.1f}%\n")
            
            self.update_kpis(
                results['exception_count'],
                results['exception_spend'],
                results['entropy_score'],
                results['total_payments']
            )
            
            # Build exceptions list
            exceptions = []
            if results.get('exceptions'):
                for ex in results['exceptions'][:10]:
                    exceptions.append({
                        'payee_name': ex.get('payee_name', 'Unknown'),
                        'amount': ex.get('amount', 0)
                    })
            
            self.root.after(0, lambda: self.update_exceptions_list(exceptions))
            
            self.progress.set(0.9)
            self.status_text.insert("end", "Generating audit report...\n")
            
            reporter = PayRealityReport(client_name=client_name)
            self.current_report = reporter.generate_report(results, 
                self.output_dir or str(Path.home() / "Desktop" / "PayReality_Reports"))
            
            self.progress.set(1.0)
            self.status_text.insert("end", f"✓ Report: {self.current_report}\n")
            self.status_text.insert("end", "Control test complete.\n")
            
            # Update action items
            self.root.after(0, lambda: self.update_action_items_after_analysis(results))
            
            messagebox.showinfo("Control Test Complete", 
                f"Control Entropy Score: {results['entropy_score']:.1f}%\n"
                f"Exceptions Found: {results['exception_count']:,}\n"
                f"Exception Spend: R {results['exception_spend']:,.2f}")
            
        except Exception as e:
            self.status_text.insert("end", f"ERROR: {str(e)}\n")
            messagebox.showerror("Error", str(e))
    
    def update_action_items_after_analysis(self, results):
        # Clear old action items
        for item, btn, text in self.action_items:
            item.destroy()
        self.action_items.clear()
        
        # Add new actions based on results
        if results['exception_count'] > 0:
            self.add_action_item(f"🔴 Review {results['exception_count']} control exceptions", "review")
        
        self.add_action_item("📄 Open Audit Report", "open_report")
        self.add_action_item("🔄 Run New Control Test", "run")
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PayRealityApp()
    app.run()