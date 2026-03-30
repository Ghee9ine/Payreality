"""
PayReality Reporting Module
Professional PDF generation with executive summaries, recommendations, and methodology
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import os
import logging

class PayRealityReport:
    def __init__(self, client_name: str = "Client", logo_path: str = None):
        self.client_name = client_name
        self.logo_path = logo_path
        self.logger = logging.getLogger('PayReality')
        
    def generate_report(self, results: dict, output_dir: str) -> str:
        """
        Generate comprehensive PDF report
        """
        filename = f"payreality_report_{self.client_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(output_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4, 
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=72)
        
        styles = getSampleStyleSheet()
        story = []
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0B2B40'),
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#E67E22'),
            spaceBefore=20,
            spaceAfter=12
        )
        
        # Title page
        story.append(Paragraph("PayReality", title_style))
        story.append(Paragraph("Independent Control Validation Report", styles['Heading2']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Client: {self.client_name}", styles['Normal']))
        story.append(Paragraph(f"Report Date: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
        story.append(Paragraph(f"Analysis Period: {results.get('analysis_period', 'Full payment history')}", styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", section_style))
        story.append(Spacer(1, 12))
        
        summary_text = f"""
        This report presents the findings of an independent control validation of your vendor payment process.
        The analysis examined {results['total_payments']:,} payments totaling R {results['total_spend']:,.2f}.
        
        <b>Key Finding:</b> A Control Entropy Score of <b>{results['entropy_score']:.1f}%</b> was identified,
        meaning that {results['entropy_score']:.1f}% of total spend was paid to vendors not formally approved
        in your vendor master file. This represents <b>R {results['exception_spend']:,.2f}</b> in payments
        that bypassed standard procurement controls.
        """
        story.append(Paragraph(summary_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Control Entropy Score
        story.append(Paragraph("Control Entropy Score", section_style))
        story.append(Spacer(1, 12))
        
        # Create gauge-like visual for entropy score
        entropy = results['entropy_score']
        entropy_color = colors.green
        if entropy > 20:
            entropy_color = colors.orange
        if entropy > 40:
            entropy_color = colors.red
            
        entropy_table_data = [
            ["Metric", "Value", "Risk Level"],
            ["Control Entropy Score", f"{entropy:.1f}%", self._get_risk_level(entropy)],
            ["Total Spend", f"R {results['total_spend']:,.2f}", ""],
            ["Exception Spend", f"R {results['exception_spend']:,.2f}", ""],
            ["Exception Count", f"{results['exception_count']:,}", f"{results['exception_count']/results['total_payments']*100:.1f}% of payments"]
        ]
        
        entropy_table = Table(entropy_table_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        entropy_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('TEXTCOLOR', (2, 1), (2, 1), entropy_color),
            ('FONTNAME', (2, 1), (2, 1), 'Helvetica-Bold'),
        ]))
        story.append(entropy_table)
        story.append(Spacer(1, 20))
        
        # Risk Assessment
        story.append(Paragraph("Risk Assessment", section_style))
        story.append(Spacer(1, 12))
        risk_text = self._get_risk_assessment(entropy, results['exception_count'], results['total_payments'])
        story.append(Paragraph(risk_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Exceptions Summary
        story.append(Paragraph("Exception Summary", section_style))
        story.append(Spacer(1, 12))
        
        # Show top 10 exceptions by amount
        if results.get('exceptions'):
            exceptions_sorted = sorted(results['exceptions'], key=lambda x: x['amount'], reverse=True)[:10]
            exception_data = [["Vendor Name", "Amount", "Match Score"]]
            for ex in exceptions_sorted:
                exception_data.append([
                    ex['payee_name'][:50], 
                    f"R {ex['amount']:,.2f}", 
                    f"{ex['match_score']}%"
                ])
            
            exception_table = Table(exception_data, colWidths=[3.5*inch, 1.5*inch, 1*inch])
            exception_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(exception_table)
            
            if len(results['exceptions']) > 10:
                story.append(Paragraph(f"\n... and {len(results['exceptions']) - 10} additional exceptions.", styles['Normal']))
        else:
            story.append(Paragraph("No exceptions found. Your vendor payment controls appear to be operating effectively.", styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # Recommendations
        story.append(Paragraph("Recommendations", section_style))
        story.append(Spacer(1, 12))
        
        recommendations = self._generate_recommendations(entropy, results['exception_count'], results['master_vendor_count'])
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", styles['Normal']))
            story.append(Spacer(1, 6))
        
        story.append(Spacer(1, 20))
        
        # Methodology
        story.append(Paragraph("Methodology", section_style))
        story.append(Spacer(1, 12))
        
        methodology_text = """
        PayReality performs independent control validation using the following approach:
        
        <b>1. Data Extraction:</b> Raw vendor master and payment transaction data is extracted from your ERP system.
        
        <b>2. Semantic Matching:</b> The actual payee name from each payment is compared against the approved vendor master 
        using advanced fuzzy matching algorithms that account for:
        • Typos and spelling variations
        • Abbreviations and acronyms
        • Corporate suffix variations (Ltd, Inc, Corp, etc.)
        • Word order differences
        • Phonetic similarities
        
        <b>3. Exception Identification:</b> Payments that cannot be confidently matched to an approved vendor are flagged as exceptions.
        
        <b>4. Control Entropy Calculation:</b> The Control Entropy Score represents the percentage of total spend that bypassed approved controls.
        
        <b>5. Independent Validation:</b> Unlike ERP controls that rely on Vendor IDs, PayReality performs independent validation using the actual payee name, ensuring true control effectiveness.
        """
        story.append(Paragraph(methodology_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Build PDF
        doc.build(story)
        self.logger.info(f"PDF report generated: {filepath}")
        return filepath
    
    def _get_risk_level(self, entropy: float) -> str:
        if entropy < 5:
            return "LOW"
        elif entropy < 20:
            return "MEDIUM"
        elif entropy < 40:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def _get_risk_assessment(self, entropy: float, exception_count: int, total_payments: int) -> str:
        if entropy < 5:
            return "Your vendor payment controls appear to be operating effectively. The low Control Entropy Score indicates that most payments are being made to approved vendors. Maintain current controls and monitor for any changes."
        elif entropy < 20:
            return "Your vendor payment controls show moderate decay. A significant portion of payments are being made to vendors outside the approved master. Recommend investigating the top exceptions and reinforcing procurement policies."
        elif entropy < 40:
            return "Your vendor payment controls are showing significant decay. A substantial portion of spend is bypassing approved controls. Immediate investigation is recommended to identify root causes and implement corrective actions."
        else:
            return "CRITICAL: Your vendor payment controls are severely compromised. The majority of payments are being made to vendors outside the approved master. Immediate executive attention and comprehensive remediation is required."
    
    def _generate_recommendations(self, entropy: float, exception_count: int, master_count: int) -> list:
        recommendations = []
        
        if entropy > 10:
            recommendations.append("Review top 10 exception vendors to determine if they should be formally onboarded to the vendor master")
        
        if exception_count > 0:
            recommendations.append("Implement a monthly exception review process to prevent control decay")
        
        if master_count < 100:
            recommendations.append("Consider expanding vendor master to include frequently used but unapproved vendors")
        
        if entropy > 20:
            recommendations.append("Conduct root cause analysis to understand why controls are being bypassed (process issues, training gaps, or system limitations)")
        
        recommendations.append("Establish a regular (monthly/quarterly) Control Entropy Score tracking to monitor control effectiveness over time")
        
        if entropy > 30:
            recommendations.append("Escalate findings to audit committee and consider implementing enhanced procurement controls")
        
        return recommendations