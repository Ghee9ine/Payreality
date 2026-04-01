"""
PayReality Reporting Module
Professional PDF generation with executive summaries, recommendations, and methodology
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
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
        self.inch = inch
        
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
        
        # Create styles
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            textColor=self.colors['primary'],
            alignment=TA_CENTER,
            spaceAfter=20,
            fontName='Helvetica-Bold'
        )
        
        self.section_style = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=18,
            textColor=self.colors['accent'],
            spaceBefore=20,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        
        self.subsection_style = ParagraphStyle(
            'SubSectionHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=self.colors['primary'],
            spaceBefore=15,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
    
    def generate_report(self, results: dict, output_dir: str) -> str:
        """
        Generate comprehensive PDF report with Vendor Master Health Score
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"PayReality_Report_{self.client_name.replace(' ', '_')}_{timestamp}.pdf"
        filepath = os.path.join(output_dir, filename)
        
        self.logger.info(f"Generating PDF report: {filepath}")
        
        doc = SimpleDocTemplate(filepath, pagesize=A4,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=72)
        
        story = []
        
        # Title page
        story.append(Paragraph("PayReality", self.title_style))
        story.append(Paragraph("Independent Control Validation Report", self.styles['Heading2']))
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
        story.append(Paragraph("Executive Summary", self.section_style))
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
        story.append(Paragraph(summary_text, self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Vendor Master Health Score
        health_report = results.get('health_report')
        if health_report:
            story.append(Paragraph("Vendor Master Health", self.section_style))
            story.append(Spacer(1, 12))
            
            health_score = health_report['health_score']
            health_level = health_report['health_level']
            health_color = health_report['health_color']
            
            health_data = [
                ["Metric", "Score", "Status"],
                ["Overall Health", f"{health_score:.1f}%", health_level],
                ["Completeness", f"{health_report['metrics']['completeness_score']:.1f}%", ""],
                ["Duplicate Rate", f"{health_report['metrics']['duplicate_rate']:.1f}%", ""],
                ["Format Quality", f"{health_report['metrics']['format_score']:.1f}%", ""],
            ]
            
            if health_report['metrics']['dormancy_rate'] is not None:
                health_data.append(["Dormancy Rate", f"{health_report['metrics']['dormancy_rate']:.1f}%", ""])
                health_data.append(["Orphan Rate", f"{health_report['metrics']['orphan_rate']:.1f}%", ""])
            
            health_table = Table(health_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
            health_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, self.colors['gray']),
                ('BACKGROUND', (0, 1), (-1, -1), self.colors['light_gray']),
                ('TEXTCOLOR', (2, 1), (2, 1), colors.HexColor(health_color)),
                ('FONTNAME', (2, 1), (2, 1), 'Helvetica-Bold'),
            ]))
            story.append(health_table)
            story.append(Spacer(1, 20))
            
            # Duplicate Examples
            if health_report['metrics']['duplicate_examples']:
                story.append(Paragraph("Potential Duplicate Vendors", self.subsection_style))
                story.append(Spacer(1, 8))
                
                dup_data = [["Normalized Name", "Variations", "Count"]]
                for dup in health_report['metrics']['duplicate_examples'][:5]:
                    dup_data.append([
                        dup['normalized'][:40],
                        ", ".join(dup['variations'][:2]),
                        str(dup['count'])
                    ])
                
                dup_table = Table(dup_data, colWidths=[2*inch, 2.5*inch, 0.8*inch])
                dup_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), self.colors['gray']),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('GRID', (0, 0), (-1, -1), 1, self.colors['gray']),
                ]))
                story.append(dup_table)
                story.append(Spacer(1, 20))
            
            # Completeness Issues
            if health_report['metrics']['completeness_issues']:
                story.append(Paragraph("Vendors Missing Critical Data", self.subsection_style))
                story.append(Spacer(1, 8))
                
                missing_data = [["Vendor Name", "Missing Fields"]]
                for issue in health_report['metrics']['completeness_issues'][:10]:
                    missing_data.append([
                        issue['vendor'][:40],
                        ", ".join(issue['missing_fields'])
                    ])
                
                missing_table = Table(missing_data, colWidths=[3*inch, 2.5*inch])
                missing_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), self.colors['gray']),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('GRID', (0, 0), (-1, -1), 1, self.colors['gray']),
                ]))
                story.append(missing_table)
                story.append(Spacer(1, 20))
        
        # Control Entropy Score
        story.append(Paragraph("Control Entropy Score", self.section_style))
        story.append(Spacer(1, 12))
        
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
        
        # 7-Pass Semantic Matching Results
        if results.get('match_stats'):
            story.append(Paragraph("7-Pass Semantic Matching Results", self.section_style))
            story.append(Spacer(1, 8))
            
            match_explanation = """
            PayReality uses a <b>7-pass semantic matching engine</b> to identify payments that should be linked to approved vendors:
            
            <b>Pass 1 - Exact:</b> Perfect character-for-character matches<br/>
            <b>Pass 2 - Normalized:</b> Matches after cleaning (case, punctuation, suffixes)<br/>
            <b>Pass 3 - Token Sort:</b> Handles word order variations<br/>
            <b>Pass 4 - Partial:</b> Handles extra words in vendor names<br/>
            <b>Pass 5 - Levenshtein:</b> Catches typos and character errors<br/>
            <b>Pass 6 - Phonetic:</b> Matches similar-sounding names<br/>
            <b>Pass 7 - Obfuscation:</b> Detects intentional hiding (dots, leetspeak, repeated characters)<br/>
            """
            story.append(Paragraph(match_explanation, self.styles['Normal']))
            story.append(Spacer(1, 12))
            
            match_data = [["Match Strategy", "Count", "Percentage", "Description"]]
            strategy_descriptions = {
                'exact': 'Perfect character match',
                'normalized': 'Match after cleaning',
                'token_sort': 'Word order variation',
                'partial': 'Extra words ignored',
                'levenshtein': 'Typo/character error',
                'phonetic': 'Sound-alike match',
                'obfuscation': 'Intentional hiding detected',
                'none': 'No match (exception)'
            }
            
            total = results['total_payments']
            for strategy in ['exact', 'normalized', 'token_sort', 'partial', 'levenshtein', 'phonetic', 'obfuscation', 'none']:
                count = results['match_stats'].get(strategy, 0)
                percentage = (count / total * 100) if total > 0 else 0
                desc = strategy_descriptions.get(strategy, '')
                match_data.append([
                    strategy.replace('_', ' ').title(),
                    f"{count:,}",
                    f"{percentage:.1f}%",
                    desc
                ])
            
            match_summary_table = Table(match_data, colWidths=[1.5*inch, 1*inch, 1*inch, 2.5*inch])
            match_summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.colors['gray']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('GRID', (0, 0), (-1, -1), 1, self.colors['gray']),
                ('BACKGROUND', (0, 1), (-1, -1), self.colors['light_gray']),
            ]))
            story.append(match_summary_table)
            story.append(Spacer(1, 20))
        
        # Duplicate Summary
        duplicates = results.get('duplicates', [])
        if duplicates:
            story.append(Paragraph("Duplicate Payments Detected", self.subsection_style))
            story.append(Spacer(1, 8))
            
            duplicate_text = f"Found <b>{len(duplicates)}</b> vendors with multiple payments that may represent duplicate or split payments."
            story.append(Paragraph(duplicate_text, self.styles['Normal']))
            story.append(Spacer(1, 10))
            
            duplicate_data = [["Vendor", "Payment Count", "Total Amount"]]
            for d in duplicates[:10]:
                duplicate_data.append([
                    d.get('display_name', d.get('vendor', 'Unknown'))[:50],
                    str(d.get('count', 0)),
                    f"R {d.get('total', 0):,.2f}"
                ])
            
            duplicate_table = Table(duplicate_data, colWidths=[3.5*inch, 1.2*inch, 1.5*inch])
            duplicate_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.colors['gray']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 1, self.colors['gray']),
            ]))
            story.append(duplicate_table)
            story.append(Spacer(1, 20))
        
        # Exceptions List with Match Strategy
        exceptions = results.get('exceptions', [])
        if exceptions:
            story.append(Paragraph("Exception Vendors", self.subsection_style))
            story.append(Spacer(1, 8))
            
            max_exceptions = self.config.get('max_exceptions_in_report', 20)
            top_exceptions = sorted(exceptions, key=lambda x: x.get('amount', 0), reverse=True)[:max_exceptions]
            
            exception_data = [["Vendor Name", "Amount", "First Seen", "Last Seen", "Payments", "Risk Level"]]
            for ex in top_exceptions:
                first_seen = ex.get('first_seen', '')[:10]
                last_seen = ex.get('last_seen', '')[:10]
                payment_count = ex.get('payment_count', 0)
                risk_level = ex.get('risk_level', 'Low')
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
                else:
                    tenure_text = ""
                
                exception_data.append([
                    ex.get('payee_name', 'Unknown')[:45],
                    f"R {ex.get('amount', 0):,.2f}",
                    first_seen or "N/A",
                    last_seen or "N/A",
                    f"{payment_count} ({tenure_text})" if payment_count > 0 else "N/A",
                    risk_level
                ])
            
            exception_table = Table(exception_data, colWidths=[2.5*inch, 1*inch, 0.8*inch, 0.8*inch, 1*inch, 0.7*inch])
            exception_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.colors['gray']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('GRID', (0, 0), (-1, -1), 1, self.colors['gray']),
                ('BACKGROUND', (0, 1), (-1, -1), self.colors['light_gray']),
            ]))
            story.append(exception_table)
            story.append(Spacer(1, 20))
            
            if len(exceptions) > max_exceptions:
                story.append(Paragraph(
                    f"\n... and {len(exceptions) - max_exceptions} additional exceptions. "
                    f"See the CSV export for complete details.",
                    self.styles['Italic']
                ))
                story.append(Spacer(1, 20))
            
            # Risk Summary Table
            story.append(Paragraph("Risk Summary", self.subsection_style))
            story.append(Spacer(1, 8))
            
            risk_data = [["Vendor", "Risk Level", "Risk Score", "Active Period", "Risk Factors"]]
            for ex in top_exceptions[:15]:
                first_seen = ex.get('first_seen', '')[:10]
                last_seen = ex.get('last_seen', '')[:10]
                tenure_days = ex.get('tenure_days', 0)
                
                if first_seen and last_seen:
                    active_period = f"{first_seen} to {last_seen}"
                elif tenure_days > 0:
                    if tenure_days > 365:
                        active_period = f"{tenure_days//365} years"
                    elif tenure_days > 30:
                        active_period = f"{tenure_days//30} months"
                    else:
                        active_period = f"{tenure_days} days"
                else:
                    active_period = "N/A"
                
                risk_data.append([
                    ex.get('payee_name', 'Unknown')[:40],
                    ex.get('risk_level', 'Low'),
                    f"{ex.get('risk_score', 0)}%",
                    active_period,
                    ", ".join(ex.get('risk_reasons', ['Review needed'])[:2])
                ])
            
            risk_table = Table(risk_data, colWidths=[2.5*inch, 0.8*inch, 0.7*inch, 1.2*inch, 2.2*inch])
            risk_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.colors['gray']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('GRID', (0, 0), (-1, -1), 1, self.colors['gray']),
                ('BACKGROUND', (0, 1), (-1, -1), self.colors['light_gray']),
            ]))
            story.append(risk_table)
            story.append(Spacer(1, 20))
            
        else:
            story.append(Paragraph(
                "<b>No exceptions found.</b> Your vendor payment controls appear to be operating effectively.",
                self.styles['Normal']
            ))
            story.append(Spacer(1, 20))
        
        # Recommendations
        if self.config.get('include_recommendations', True):
            story.append(Paragraph("Recommendations", self.section_style))
            story.append(Spacer(1, 12))
            
            recommendations = self._generate_recommendations(
                results['entropy_score'], 
                results.get('exception_count', 0), 
                results.get('master_vendor_count', 0),
                results.get('match_stats', {}),
                len(results.get('duplicates', [])),
                results.get('health_report')
            )
            
            for i, rec in enumerate(recommendations, 1):
                story.append(Paragraph(f"<b>{i}.</b> {rec}", self.styles['Normal']))
                story.append(Spacer(1, 6))
            
            story.append(Spacer(1, 20))
        
        # Methodology
        if self.config.get('include_methodology', True):
            story.append(Paragraph("Methodology", self.section_style))
            story.append(Spacer(1, 12))
            
            methodology_text = """
            PayReality performs independent control validation using the following approach:
            
            <b>1. Vendor Master Health Analysis:</b> The vendor master file is analyzed for data quality issues including completeness, duplicates, dormancy, and format quality.
            
            <b>2. 7-Pass Semantic Matching:</b> The actual payee name from each payment is compared against the approved vendor master 
            using seven progressive matching strategies:
            • <b>Exact Match:</b> Perfect character-for-character matching
            • <b>Normalized Match:</b> Cleaning of case, punctuation, and corporate suffixes
            • <b>Token Sort Ratio:</b> Handles word order variations
            • <b>Partial Ratio:</b> Handles extra words in vendor names
            • <b>Levenshtein Distance:</b> Catches typos and character errors
            • <b>Phonetic Matching:</b> Matches similar-sounding names
            • <b>Obfuscation Detection:</b> Identifies intentional hiding (dots, leetspeak, repeated characters)
            
            <b>3. Duplicate Detection:</b> Payments are analyzed to identify vendors that appear multiple times across different 
            payment methods, indicating potential duplicate or split payments.
            
            <b>4. Tenure Analysis:</b> For each unapproved vendor, PayReality tracks:
            • First appearance date
            • Most recent payment date
            • Total payment count
            • Active duration (tenure)
            
            <b>5. Risk Scoring:</b> Each exception vendor is assigned a risk score based on:
            • Unapproved vendor status
            • Total payment volume
            • Duplicate payment indicators
            • Payment tenure and frequency
            • Weekend payment patterns
            
            <b>6. Control Entropy Calculation:</b> The Control Entropy Score represents the percentage of total spend that bypassed approved controls.
            """
            story.append(Paragraph(methodology_text, self.styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Footer
        story.append(Spacer(1, 30))
        footer_text = f"""
        <font size=8 color='{self.colors['gray']}'>
        PayReality - Independent Control Validation<br/>
        Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
        This report is for internal use only.
        </font>
        """
        story.append(Paragraph(footer_text, self.styles['Normal']))
        
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
                                   master_count: int, match_stats: Dict = None,
                                   duplicate_count: int = 0,
                                   health_report: Dict = None) -> List[str]:
        recommendations = []
        
        if entropy > 30:
            recommendations.append("Escalate findings to audit committee immediately")
        
        if entropy > 10:
            recommendations.append("Review top exception vendors to determine if they should be formally onboarded")
        
        if exception_count > 0:
            recommendations.append("Implement a monthly exception review process to prevent control decay")
        
        if duplicate_count > 0:
            recommendations.append(f"Investigate {duplicate_count} potential duplicate payment(s) to recover lost funds")
        
        if master_count < 100:
            recommendations.append("Consider expanding vendor master to include frequently used but unapproved vendors")
        
        if entropy > 20:
            recommendations.append("Conduct root cause analysis to understand why controls are being bypassed")
        
        # Vendor Master Health recommendations
        if health_report:
            if health_report['metrics']['completeness_score'] < 70:
                recommendations.append(f"Improve vendor master completeness - {health_report['metrics']['completeness_issues']} vendors missing critical data")
            
            if health_report['metrics']['duplicate_rate'] > 5:
                recommendations.append(f"Clean up {health_report['metrics']['duplicate_count']} potential duplicate vendors")
            
            if health_report['metrics']['orphan_rate'] is not None and health_report['metrics']['orphan_rate'] > 30:
                recommendations.append(f"Review {health_report['metrics']['orphan_rate']:.0f}% of vendors with no transactions for possible removal")
        
        # Obfuscation detection recommendation
        if match_stats and match_stats.get('obfuscation', 0) > 0:
            obfuscation_count = match_stats.get('obfuscation', 0)
            recommendations.append(f"Investigate {obfuscation_count} payments with intentional obfuscation patterns - potential fraud indicators")
        
        recommendations.append("Establish a regular (monthly/quarterly) Control Entropy Score tracking")
        
        if exception_count > 10:
            recommendations.append("Consider implementing automated controls for one-time vendor creation")
        
        return recommendations[:7]