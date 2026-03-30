import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from rapidfuzz import fuzz, process
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import os
from datetime import datetime

class PayRealityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PayReality - Independent Control Validation")
        self.root.geometry("700x600")
        
        # Variables
        self.master_file = None
        self.payments_file = None
        
        # Create GUI
        self.create_widgets()
    
    def create_widgets(self):
        # Title
        title = tk.Label(self.root, text="PayReality", font=("Arial", 24, "bold"))
        title.pack(pady=10)
        
        subtitle = tk.Label(self.root, text="Independent Control Validation", font=("Arial", 12))
        subtitle.pack(pady=5)
        
        # Frame for files
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=20)
        
        # Vendor Master File
        tk.Label(file_frame, text="Vendor Master File:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        self.master_label = tk.Label(file_frame, text="No file selected", fg="gray", width=40, anchor="w")
        self.master_label.grid(row=0, column=1, padx=5)
        tk.Button(file_frame, text="Browse", command=self.load_master).grid(row=0, column=2)
        
        # Payments File
        tk.Label(file_frame, text="Payments File:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=5)
        self.payments_label = tk.Label(file_frame, text="No file selected", fg="gray", width=40, anchor="w")
        self.payments_label.grid(row=1, column=1, padx=5)
        tk.Button(file_frame, text="Browse", command=self.load_payments).grid(row=1, column=2)
        
        # Run button
        self.run_button = tk.Button(self.root, text="Run Analysis", command=self.run_analysis, state="disabled", 
                                    bg="blue", fg="white", font=("Arial", 12), padx=20, pady=5)
        self.run_button.pack(pady=20)
        
        # Progress bar
        self.progress = ttk.Progressbar(self.root, length=400, mode='indeterminate')
        self.progress.pack(pady=10)
        
        # Status text
        self.status_text = tk.Text(self.root, height=15, width=80)
        self.status_text.pack(pady=10)
        
        # Scrollbar for status
        scrollbar = tk.Scrollbar(self.status_text)
        scrollbar.pack(side="right", fill="y")
        self.status_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.status_text.yview)
    
    def load_master(self):
        self.master_file = filedialog.askopenfilename(
            title="Select Vendor Master File",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if self.master_file:
            self.master_label.config(text=os.path.basename(self.master_file), fg="black")
            self.check_ready()
    
    def load_payments(self):
        self.payments_file = filedialog.askopenfilename(
            title="Select Payments File",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if self.payments_file:
            self.payments_label.config(text=os.path.basename(self.payments_file), fg="black")
            self.check_ready()
    
    def check_ready(self):
        if self.master_file and self.payments_file:
            self.run_button.config(state="normal")
    
    def clean_name(self, name):
        if pd.isna(name):
            return ""
        name = str(name).lower().strip()
        suffixes = [' ltd', ' inc', ' corp', ' llc', ' pty', ' technologies', ' solutions', ' pty ltd']
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[: -len(suffix)]
        return name.strip()
    
    def run_analysis(self):
        self.run_button.config(state="disabled")
        self.progress.start()
        self.status_text.delete(1.0, tk.END)
        self.status_text.insert(tk.END, "Starting analysis...\n")
        self.root.update()
        
        try:
            # Load files
            self.status_text.insert(tk.END, "Loading files...\n")
            self.root.update()
            
            master_df = pd.read_csv(self.master_file)
            payments_df = pd.read_csv(self.payments_file)
            
            self.status_text.insert(tk.END, f"Loaded {len(master_df)} vendors, {len(payments_df)} payments\n")
            self.root.update()
            
            # Get vendor names
            master_vendors = master_df['vendor_name'].tolist()
            master_clean = [(v, self.clean_name(v)) for v in master_vendors]
            master_clean_names = [c for _, c in master_clean]
            
            # Process payments
            self.status_text.insert(tk.END, "Running fuzzy matching...\n")
            self.root.update()
            
            exceptions = []
            total_spend = 0
            exception_spend = 0
            results = []
            
            for idx, row in payments_df.iterrows():
                payee = row['payee_name']
                amount = row['amount']
                total_spend += amount
                
                payee_clean = self.clean_name(payee)
                
                # Check if payee is in master
                if payee in master_vendors or payee_clean in master_clean_names:
                    matched = payee
                    status = "APPROVED"
                else:
                    # Try fuzzy matching
                    result = process.extractOne(payee_clean, master_clean_names, scorer=fuzz.token_sort_ratio)
                    if result and result[1] >= 80:
                        matched = next(v for v, c in master_clean if c == result[0])
                        status = "MATCHED"
                    else:
                        matched = None
                        status = "EXCEPTION"
                        exceptions.append(payee)
                        exception_spend += amount
                
                results.append((payee, matched, status, amount))
                
                if idx % 100 == 0:
                    self.status_text.insert(tk.END, f"Processed {idx+1} payments...\n")
                    self.root.update()
            
            # Calculate Control Entropy Score
            entropy_score = (exception_spend / total_spend * 100) if total_spend > 0 else 0
            
            # Generate PDF report
            self.status_text.insert(tk.END, "Generating PDF report...\n")
            self.root.update()
            
            report_file = self.generate_pdf_report(results, total_spend, exception_spend, entropy_score, len(payments_df))
            
            # Save exceptions to CSV
            exceptions_df = payments_df[payments_df['payee_name'].isin(exceptions)]
            csv_file = os.path.join(os.path.dirname(self.master_file), "payreality_exceptions.csv")
            exceptions_df.to_csv(csv_file, index=False)
            
            # Show summary
            self.status_text.insert(tk.END, "\n" + "="*50 + "\n")
            self.status_text.insert(tk.END, "PAYREALITY REPORT SUMMARY\n")
            self.status_text.insert(tk.END, "="*50 + "\n")
            self.status_text.insert(tk.END, f"Total Payments: {len(payments_df)}\n")
            self.status_text.insert(tk.END, f"Total Spend: R {total_spend:,.2f}\n")
            self.status_text.insert(tk.END, f"Exceptions Found: {len(exceptions)}\n")
            self.status_text.insert(tk.END, f"Exception Spend: R {exception_spend:,.2f}\n")
            self.status_text.insert(tk.END, f"Control Entropy Score: {entropy_score:.2f}%\n")
            self.status_text.insert(tk.END, "="*50 + "\n")
            
            if exceptions:
                self.status_text.insert(tk.END, "\nExceptions Found:\n")
                for e in exceptions[:10]:
                    self.status_text.insert(tk.END, f"  - {e}\n")
                if len(exceptions) > 10:
                    self.status_text.insert(tk.END, f"  ... and {len(exceptions)-10} more\n")
            
            self.status_text.insert(tk.END, f"\nReports saved:\n")
            self.status_text.insert(tk.END, f"  PDF: {report_file}\n")
            self.status_text.insert(tk.END, f"  CSV: {csv_file}\n")
            self.status_text.insert(tk.END, "\nAnalysis complete!\n")
            
            messagebox.showinfo("Complete", f"Analysis complete!\n\nControl Entropy Score: {entropy_score:.2f}%\nExceptions Found: {len(exceptions)}\n\nReports saved to the same folder as your payment file.")
            
        except Exception as e:
            self.status_text.insert(tk.END, f"\nERROR: {str(e)}\n")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        
        finally:
            self.progress.stop()
            self.run_button.config(state="normal")
    
    def generate_pdf_report(self, results, total_spend, exception_spend, entropy_score, total_payments):
        # Get the directory of the payments file
        output_dir = os.path.dirname(self.payments_file)
        report_file = os.path.join(output_dir, f"payreality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        
        doc = SimpleDocTemplate(report_file, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, spaceAfter=30)
        story.append(Paragraph("PayReality", title_style))
        story.append(Paragraph("Independent Control Validation Report", styles['Heading2']))
        story.append(Spacer(1, 20))
        
        # Summary
        story.append(Paragraph("Executive Summary", styles['Heading2']))
        summary_data = [
            ["Metric", "Value"],
            ["Total Payments Analysed", str(total_payments)],
            ["Total Spend", f"R {total_spend:,.2f}"],
            ["Exception Payments Found", str(len([r for r in results if r[2] == 'EXCEPTION']))],
            ["Exception Spend", f"R {exception_spend:,.2f}"],
            ["Control Entropy Score", f"{entropy_score:.2f}%"]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Exceptions
        exceptions = [r for r in results if r[2] == 'EXCEPTION']
        if exceptions:
            story.append(Paragraph("Exception Details", styles['Heading2']))
            story.append(Paragraph("The following payments were made to vendors not found in your approved vendor master:", styles['Normal']))
            story.append(Spacer(1, 10))
            
            exception_data = [["Payee Name", "Status"]]
            for e in exceptions[:20]:
                exception_data.append([e[0], "NOT APPROVED"])
            
            exception_table = Table(exception_data, colWidths=[4*inch, 1.5*inch])
            exception_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(exception_table)
            
            if len(exceptions) > 20:
                story.append(Paragraph(f"\n... and {len(exceptions)-20} more exceptions. See the full CSV report for complete details.", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        return report_file

if __name__ == "__main__":
    root = tk.Tk()
    app = PayRealityApp(root)
    root.mainloop()