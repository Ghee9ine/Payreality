"""
PayReality Reporting Module
Professional PDF generation with executive summaries, recommendations, and methodology
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os
import logging
from typing import Dict, List, Optional

class PayRealityReport:
    def __init__(self, client_name: str = "Client", config: Optional[Dict] = None):
        self.client_name = client_name
        self.config = config or {}
        self.logger = logging.getLogger('PayReality')
        
        # Report styling
        self.colors = {
            'primary': colors.HexColor('#0B2B40'),
            'accent': colors.HexColor('#E67E22'),
            'success': colors.HexColor('#27AE60'),
            'warning': colors.HexColor('#F39C12'),
            'danger': colors.HexColor('#E74C3C'),
            'gray': colors.HexColor('#95A5A6'),
            'light_gray': colors.HexColor('#ECF0F1')
        }
        
    def generate_report(self, results: dict, output_dir: str) -> str:
        """
        Generate comprehensive PDF report
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"PayReality_Report_{self.client_name.replace(' ', '_')}_{timestamp}.pdf"
        filepath = os.path.join(output_dir, filename)
        
        self.logger.info(f"Generating PDF report: {filepath}")
        
        doc = SimpleDocTemplate(filepath, pagesize=A4,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=72)
        
        styles = getSampleStyleSheet()
        story = []
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=self.colors['primary'],
            alignment=TA_CENTER,
            spaceAfter=20,
            fontName='Helvetica-Bold'
        )
        
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=18,
            textColor=self.colors['accent'],
            spaceBefore=20,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        
        subsection_style = ParagraphStyle(
            'SubSectionHeader',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=self.colors['primary'],
            spaceBefore=15,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
        
        # Title page
        story.append(Paragraph("PayReality", title_style))
        story.append(Paragraph("Independent Control Validation Report", styles['Heading2']))
        story.append(Spacer(1, 24))
        
        # Report metadata
        metadata = [
            ["Client:", self.client_name],
            ["Report Date:", datetime.now().strftime('%B %d, %Y')],
            ["Analysis Period:", results.get('analysis_period', 'Full payment history')],
            ["Total Payments:", f"{results['total_payments']:,}"],
            ["Total Spend:", f"R {results['total_spend']:,.2f}"],
            ["Report ID:", f"PR-{timestamp}"]
        ]
        
        metadata_table = Table(metadata, colWidths=[2.5*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.colors['gray']),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(metadata_table)
        story.append(Spacer(1, 30))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", section_style))
        story.append(Spacer(1, 12))
        
        entropy = results['entropy_score']
        risk_level = self._get_risk_level(entropy)
        risk_color = self._get_risk_color(risk_level)
        
        summary_text = f"""
        This report presents the findings of an independent control validation of your vendor payment process.
        The analysis examined <b>{results['total_payments']:,}</b> payments totaling 
        <b>R {results['total_spend']:,.2f}</b>.
        
        <b><font color='{risk_color}'>Key Finding:</font></b> A Control Entropy Score of <b>{entropy:.1f}%</b> was identified,
        meaning that <b>{entropy:.1f}%</b> of total spend was paid to vendors not formally approved
        in your vendor master file. This represents <b>R {results['exception_spend']:,.2f}</b> in payments
        that bypassed standard procurement controls.
        
        <b>Risk Level: {risk_level}</b> - {self._get_risk_description(entropy)}
        """
        story.append(Paragraph(summary_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Control Entropy Score (visual)
        story.append(Paragraph("Control Entropy Score", section_style))
        story.append(Spacer(1, 12))
        
        # Create score card
        score_data = [
            ["Metric", "Value", "Status"],
            ["Control Entropy Score", f"{entropy:.1f}%", risk_level],
            ["Total Spend", f"R {results['total_spend']:,.2f}", ""],
            ["Exception Spend", f"R {results['exception_spend']:,.2f}", f"{entropy:.1f}% of total"],
            ["Exception Count", f"{results['exception_count']:,}", f"{results['exception_count']/results['total_payments']*100:.1f}% of payments"]
        ]
        
        score_table = Table(score_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), self.colors['light_gray']),
            ('GRID', (0, 0), (-1, -1), 1, self.colors['gray']),
            ('TEXTCOLOR', (2, 1), (2, 1), risk_color),
            ('FONTNAME', (2, 1), (2, 1), 'Helvetica-Bold'),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 20))
        
        # Match Statistics
        if results.get('match_stats'):
            story.append(Paragraph("Matching Statistics", subsection_style))
            story.append(Spacer(1, 8))
            
            match_data = [["Strategy", "Count", "Percentage"]]
            total = results['total_payments']
            for strategy, count in sorted(results['match_stats'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total * 100) if total > 0 else 0
                strategy_name = strategy.replace('_', ' ').title()
                match_data.append([strategy_name, f"{count:,}", f"{percentage:.1f}%"])
            
            match_table = Table(match_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
            match_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.colors['gray']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, self.colors['gray']),
            ]))
            story.append(match_table)
            story.append(Spacer(1, 20))
        
        # Top Exceptions
        if results.get('exceptions'):
            story.append(Paragraph("Top Exception Vendors", subsection_style))
            story.append(Spacer(1, 8))
            
            max_exceptions = self.config.get('max_exceptions_in_report', 20)
            top_exceptions = sorted(results['exceptions'], key=lambda x: x['amount'], reverse=True)[:max_exceptions]
            
            exception_data = [["Vendor Name", "Amount", "Match Score"]]
            for ex in top_exceptions:
                exception_data.append([
                    ex['payee_name'][:60], 
                    f"R {ex['amount']:,.2f}", 
                    f"{ex.get('match_score', 0)}%"
                ])
            
            exception_table = Table(exception_data, colWidths=[4*inch, 1.2*inch, 0.8*inch])
            exception_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.colors['gray']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, self.colors['gray']),
                ('BACKGROUND', (0, 1), (-1, -1), self.colors['light_gray']),
            ]))
            story.append(exception_table)
            
            if len(results['exceptions']) > max_exceptions:
                story.append(Paragraph(
                    f"\n... and {len(results['exceptions']) - max_exceptions} additional exceptions. "
                    f"See the CSV export for complete details.",
                    styles['Italic']
                ))
        else:
            story.append(Paragraph(
                "<b>✓ No exceptions found.</b> Your vendor payment controls appear to be operating effectively.",
                styles['Normal']
            ))
        
        story.append(Spacer(1, 20))
        
        # Recommendations
        if self.config.get('include_recommendations', True):
            story.append(Paragraph("Recommendations", section_style))
            story.append(Spacer(1, 12))
            
            recommendations = self._generate_recommendations(
                results['entropy_score'], 
                results['exception_count'], 
                results['master_vendor_count'],
                results.get('match_stats', {})
            )
            
            for i, rec in enumerate(recommendations, 1):
                story.append(Paragraph(f"<b>{i}.</b> {rec}", styles['Normal']))
                story.append(Spacer(1, 6))
            
            story.append(Spacer(1, 20))
        
        # Methodology
        if self.config.get('include_methodology', True):
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
            
            <b>3. Multiple Matching Strategies:</b> Our engine uses five distinct matching strategies:
            • Exact Clean Match: After cleaning (removing suffixes, punctuation)
            • Token Sort Ratio: Handles word order variations
            • Partial Ratio: Handles extra words in vendor names
            • Phonetic Matching: Catches similar-sounding names
            • Quick Ratio: A fast fallback for close matches
            
            <b>4. Exception Identification:</b> Payments that cannot be confidently matched to an approved vendor (score below configurable threshold) are flagged as exceptions.
            
            <b>5. Control Entropy Calculation:</b> The Control Entropy Score represents the percentage of total spend that bypassed approved controls.
            
            <b>6. Independent Validation:</b> Unlike ERP controls that rely on Vendor IDs, PayReality performs independent validation using the actual payee name, ensuring true control effectiveness.
            """
            story.append(Paragraph(methodology_text, styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Footer
        story.append(Spacer(1, 30))
        footer_text = f"""
        <font size=8 color='{self.colors['gray']}'>
        PayReality v1.0 - Independent Control Validation<br/>
        Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
        This report is for internal use only.
        </font>
        """
        story.append(Paragraph(footer_text, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        self.logger.info(f"✓ PDF report generated: {filepath}")
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
    
    def _get_risk_color(self, risk_level: str) -> str:
        colors_map = {
            "LOW": "#27AE60",
            "MEDIUM": "#F39C12",
            "HIGH": "#E67E22",
            "CRITICAL": "#E74C3C"
        }
        return colors_map.get(risk_level, "#95A5A6")
    
    def _get_risk_description(self, entropy: float) -> str:
        if entropy < 5:
            return "Controls are operating effectively. Maintain current processes."
        elif entropy < 20:
            return "Controls show moderate decay. Recommend investigating top exceptions."
        elif entropy < 40:
            return "Controls are significantly compromised. Immediate review recommended."
        else:
            return "CRITICAL: Controls are severely compromised. Executive attention required."
    
    def _generate_recommendations(self, entropy: float, exception_count: int, 
                                   master_count: int, match_stats: Dict = None) -> List[str]:
        recommendations = []
        
        # Priority based on entropy
        if entropy > 30:
            recommendations.append("Escalate findings to audit committee immediately")
        
        if entropy > 10:
            recommendations.append("Review top exception vendors to determine if they should be formally onboarded")
        
        if exception_count > 0:
            recommendations.append("Implement a monthly exception review process to prevent control decay")
        
        if master_count < 100:
            recommendations.append("Consider expanding vendor master to include frequently used but unapproved vendors")
        
        if entropy > 20:
            recommendations.append("Conduct root cause analysis to understand why controls are being bypassed")
        
        # Match strategy based recommendations
        if match_stats:
            phonetic_matches = match_stats.get('phonetic', 0)
            if phonetic_matches > 0:
                recommendations.append(f"Review {phonetic_matches:,} phonetic matches - these may indicate data entry errors or intentional obfuscation")
        
        # Standard recommendations
        recommendations.append("Establish a regular (monthly/quarterly) Control Entropy Score tracking")
        
        if exception_count > 10:
            recommendations.append("Consider implementing automated controls for one-time vendor creation")
        
        return recommendations[:7]  # Limit to top 7