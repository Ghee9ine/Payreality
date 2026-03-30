"""
PayReality Main Application
Orchestrates all modules into a complete product
"""

import sys
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
import traceback

from payreality_core import PayRealityEngine, DataValidationError, MatchingError
from payreality_reporting import PayRealityReport
from payreality_config import PayRealityConfig

def get_output_choice(payments_file: str, config: PayRealityConfig) -> str:
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
    print("4. Use default from configuration")
    default_dir = config.get_output_directory()
    print(f"   ({default_dir})")
    print()
    
    while True:
        choice = input("Choose (1/2/3/4): ").strip()
        
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
        
        elif choice == '4':
            output_dir = config.get_output_directory()
            print(f"\n✓ Reports will be saved to: {output_dir}")
            return output_dir
        
        else:
            print("\n✗ Invalid choice. Please enter 1, 2, 3, or 4.\n")

def validate_file_path(filepath: str, description: str) -> bool:
    """Validate that a file exists and is readable"""
    if not filepath:
        print(f"\n✗ Error: {description} path is empty")
        return False
    
    if not os.path.exists(filepath):
        print(f"\n✗ Error: {description} file not found: {filepath}")
        return False
    
    return True

def main():
    """Main application entry point"""
    print("=" * 60)
    print("PayReality - Independent Control Validation")
    print("Version 1.0.0")
    print("=" * 60)
    print()
    
    # Load configuration
    config = PayRealityConfig()
    
    # Get file paths from user with validation
    print("Please provide the following files:")
    master_file = input("Vendor Master file path: ").strip().strip('"')
    payments_file = input("Payments file path: ").strip().strip('"')
    
    if not validate_file_path(master_file, "Vendor Master"):
        return 1
    
    if not validate_file_path(payments_file, "Payments"):
        return 1
    
    # Optional client name
    client_name = input("\nClient name (optional, press Enter to skip): ").strip()
    if not client_name:
        client_name = "Client"
    
    # Get output location
    output_dir = get_output_choice(payments_file, config)
    
    print()
    print("Starting analysis...")
    print()
    
    # Initialize engine with config
    engine = PayRealityEngine(config=config.config)
    
    try:
        # Get threshold from config
        threshold = config.get('matching.threshold', 80)
        batch_size = config.get('processing.batch_size', 10000)
        
        # Run analysis
        results = engine.run_analysis(
            master_file, 
            payments_file,
            threshold=threshold,
            batch_size=batch_size
        )
        
        # Load actual payments for exception details
        if payments_file.endswith('.csv'):
            payments_df = pd.read_csv(payments_file)
        elif payments_file.endswith(('.xlsx', '.xls')):
            payments_df = pd.read_excel(payments_file)
        else:
            payments_df = pd.read_csv(payments_file)
        
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
        
        # Add match statistics
        results['match_stats'] = getattr(engine, 'match_stats', {})
        
        # Create report with config
        report_config = config.config.get('reporting', {})
        reporter = PayRealityReport(client_name=client_name, config=report_config)
        report_path = reporter.generate_report(results, output_dir)
        
        # Save exceptions to CSV
        if results['exceptions']:
            exceptions_df = pd.DataFrame(results['exceptions'])
            csv_path = os.path.join(output_dir, f"PayReality_Exceptions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            exceptions_df.to_csv(csv_path, index=False)
            print(f"\n✓ Exceptions saved to: {csv_path}")
        
        # Save full results if configured
        if config.get('output.save_full_results', False):
            results_df = pd.DataFrame(results['results'])
            full_path = os.path.join(output_dir, f"PayReality_FullResults_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            results_df.to_csv(full_path, index=False)
            print(f"✓ Full results saved to: {full_path}")
        
        # Print summary
        print()
        print("=" * 60)
        print("ANALYSIS COMPLETE")
        print("=" * 60)
        print(f"✓ PDF Report: {report_path}")
        print(f"✓ Control Entropy Score: {results['entropy_score']:.1f}%")
        print(f"✓ Exceptions Found: {results['exception_count']:,}")
        print(f"✓ Exception Spend: R {results['exception_spend']:,.2f}")
        print()
        
        # Print match statistics
        if results.get('match_stats'):
            print("Match Strategy Distribution:")
            total = results['total_payments']
            for strategy, count in sorted(results['match_stats'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total * 100) if total > 0 else 0
                print(f"  {strategy.replace('_', ' ').title()}: {count:,} ({percentage:.1f}%)")
        
        print()
        print("Recommendations:")
        recommendations = reporter._generate_recommendations(
            results['entropy_score'], 
            results['exception_count'], 
            results['master_vendor_count'],
            results.get('match_stats', {})
        )
        for i, rec in enumerate(recommendations[:5], 1):
            print(f"  {i}. {rec}")
        print()
        print("=" * 60)
        
        return 0
        
    except DataValidationError as e:
        print(f"\n✗ Data Validation Error: {e}")
        return 1
    except MatchingError as e:
        print(f"\n✗ Matching Error: {e}")
        return 1
    except FileNotFoundError as e:
        print(f"\n✗ File Error: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")
        if config.get('debug', False):
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())