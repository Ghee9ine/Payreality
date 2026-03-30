"""
PayReality Main Application
Orchestrates all modules into a complete product
"""

import sys
import os
from datetime import datetime
from pathlib import Path
import pandas as pd

from payreality_core import PayRealityEngine, DataValidationError
from payreality_reporting import PayRealityReport
from payreality_config import PayRealityConfig

def get_output_choice(payments_file):
    """Ask user where to save reports"""
    print("\n" + "=" * 60)
    print("Report Output Location")
    print("=" * 60)
    print("Where would you like to save the reports?")
    print()
    print("1. Same folder as payments file")
    print(f"   ({os.path.dirname(payments_file) or os.getcwd()})")
    print()
    print("2. Desktop (creates 'PayReality_Reports' folder)")
    desktop = Path.home() / 'Desktop' / 'PayReality_Reports'
    print(f"   ({desktop})")
    print()
    print("3. Custom location")
    print()
    
    while True:
        choice = input("Choose (1/2/3): ").strip()
        
        if choice == '1':
            output_dir = os.path.dirname(payments_file) or os.getcwd()
            print(f"\n✓ Reports will be saved to: {output_dir}")
            return output_dir
            
        elif choice == '2':
            desktop = Path.home() / 'Desktop' / 'PayReality_Reports'
            desktop.mkdir(exist_ok=True)
            print(f"\n✓ Reports will be saved to: {desktop}")
            return str(desktop)
            
        elif choice == '3':
            custom_path = input("\nEnter full folder path: ").strip().strip('"')
            try:
                os.makedirs(custom_path, exist_ok=True)
                print(f"\n✓ Reports will be saved to: {custom_path}")
                return custom_path
            except Exception as e:
                print(f"\n✗ Error creating folder: {e}")
                print("Please try again.\n")
        
        else:
            print("\n✗ Invalid choice. Please enter 1, 2, or 3.\n")

def main():
    """Main application entry point"""
    print("=" * 60)
    print("PayReality - Independent Control Validation")
    print("=" * 60)
    print()
    
    # Load configuration
    config = PayRealityConfig()
    
    # Get file paths from user
    print("Please provide the following files:")
    master_file = input("Vendor Master file path: ").strip().strip('"')
    payments_file = input("Payments file path: ").strip().strip('"')
    
    if not master_file or not payments_file:
        print("\n✗ Error: Both files are required")
        return 1
    
    # Verify files exist
    if not os.path.exists(master_file):
        print(f"\n✗ Error: Vendor Master file not found: {master_file}")
        return 1
    
    if not os.path.exists(payments_file):
        print(f"\n✗ Error: Payments file not found: {payments_file}")
        return 1
    
    # Optional client name
    client_name = input("\nClient name (optional, press Enter to skip): ").strip()
    if not client_name:
        client_name = "Client"
    
    # Get output location
    output_dir = get_output_choice(payments_file)
    
    print()
    print("Starting analysis...")
    print()
    
    # Initialize engine
    engine = PayRealityEngine()
    
    try:
        # Run analysis
        results = engine.run_analysis(
            master_file, 
            payments_file,
            threshold=config.get('matching.threshold', 80)
        )
        
        # Load actual payments for exception details
        if payments_file.endswith('.csv'):
            payments_df = pd.read_csv(payments_file)
        elif payments_file.endswith(('.xlsx', '.xls')):
            payments_df = pd.read_excel(payments_file)
        else:
            payments_df = pd.read_csv(payments_file)  # try csv as default
        
        # Attach exception details to results
        exception_details = []
        for i, row in payments_df.iterrows():
            if row['payee_name'] in [e['payee_name'] for e in results['exceptions']]:
                exception_details.append({
                    'payee_name': row['payee_name'],
                    'amount': row['amount'],
                    'match_score': next((e['match_score'] for e in results['exceptions'] if e['payee_name'] == row['payee_name']), 0)
                })
        
        results['exceptions'] = sorted(exception_details, key=lambda x: x['amount'], reverse=True)
        
        # Add analysis period if date column exists
        if 'payment_date' in payments_df.columns:
            try:
                min_date = pd.to_datetime(payments_df['payment_date']).min()
                max_date = pd.to_datetime(payments_df['payment_date']).max()
                results['analysis_period'] = f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
            except:
                results['analysis_period'] = "Full history"
        else:
            results['analysis_period'] = "Full history"
        
        # Create report
        reporter = PayRealityReport(client_name=client_name)
        report_path = reporter.generate_report(results, output_dir)
        
        # Save exceptions to CSV
        if results['exceptions']:
            exceptions_df = pd.DataFrame(results['exceptions'])
            csv_path = os.path.join(output_dir, f"exceptions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            exceptions_df.to_csv(csv_path, index=False)
            print(f"\n✓ Exceptions saved to: {csv_path}")
        
        print()
        print("=" * 60)
        print("ANALYSIS COMPLETE")
        print("=" * 60)
        print(f"✓ PDF Report: {report_path}")
        print(f"✓ Control Entropy Score: {results['entropy_score']:.1f}%")
        print(f"✓ Exceptions Found: {results['exception_count']:,}")
        print(f"✓ Exception Spend: R {results['exception_spend']:,.2f}")
        print()
        print("Recommendations:")
        recommendations = reporter._generate_recommendations(
            results['entropy_score'], 
            results['exception_count'], 
            results['master_vendor_count']
        )
        for i, rec in enumerate(recommendations[:5], 1):
            print(f"  {i}. {rec}")
        print()
        print("=" * 60)
        
        return 0
        
    except DataValidationError as e:
        print(f"\n✗ Data Validation Error: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())