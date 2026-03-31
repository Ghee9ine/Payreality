"""
Generate Test Data for PayReality
Creates realistic vendor master and payment datasets for testing
"""

import pandas as pd
import random
import numpy as np
from datetime import datetime, timedelta
import os

def generate_vendor_master():
    """Generate a realistic vendor master file with 100 vendors"""
    
    vendors = []
    
    # Base vendor names
    base_vendors = [
        "Microsoft Corporation", "Dell Technologies Inc", "Amazon Web Services", "Google Cloud Platform", "IBM Corporation",
        "Oracle America Inc", "SAP SE", "Salesforce.com Inc", "Adobe Systems", "Cisco Systems Inc",
        "HP Inc", "Lenovo Group", "Apple Inc", "VMware Inc", "Intel Corporation",
        "NVIDIA Corporation", "Advanced Micro Devices", "Qualcomm Inc", "Texas Instruments", "Broadcom Inc",
        "Accenture PLC", "Deloitte LLP", "PricewaterhouseCoopers", "Ernst & Young", "KPMG International",
        "McKinsey & Company", "Boston Consulting Group", "Bain & Company", "Capgemini SE", "Infosys Limited",
        "Tata Consultancy Services", "Wipro Limited", "Cognizant Technology", "HCL Technologies", "Tech Mahindra",
        "FedEx Corporation", "DHL International", "United Parcel Service", "USPS", "Amazon Logistics",
        "McDonald's Corporation", "Starbucks Corporation", "Coca-Cola Company", "PepsiCo Inc", "Nestle SA",
        "Johnson & Johnson", "Pfizer Inc", "Merck & Co", "Novartis AG", "Roche Holding",
        "Toyota Motor Corp", "Ford Motor Company", "General Motors", "Tesla Inc", "BMW Group",
        "ExxonMobil Corp", "Royal Dutch Shell", "Chevron Corporation", "BP PLC", "TotalEnergies",
        "Walmart Inc", "Target Corporation", "Costco Wholesale", "Home Depot Inc", "Lowe's Companies",
        "Bank of America", "JPMorgan Chase", "Wells Fargo", "Citigroup Inc", "Goldman Sachs",
        "Visa Inc", "Mastercard Inc", "American Express", "PayPal Holdings", "Block Inc",
        "AT&T Inc", "Verizon Communications", "T-Mobile US", "Sprint Corporation", "Comcast Corporation",
        "Netflix Inc", "Walt Disney Company", "Warner Bros Discovery", "Universal Pictures", "Sony Group",
        "Marriott International", "Hilton Worldwide", "Hyatt Hotels", "Airbnb Inc", "Expedia Group",
        "United Airlines", "Delta Air Lines", "American Airlines", "Emirates Group", "Qatar Airways"
    ]
    
    for i, vendor in enumerate(base_vendors[:100], 1):
        vendors.append({
            'vendor_id': f"V{i:04d}",
            'vendor_name': vendor,
            'tax_id': f"TAX{random.randint(100000, 999999)}",
            'country': random.choice(['USA', 'Canada', 'UK', 'Germany', 'France', 'Japan', 'Australia', 'South Africa']),
            'risk_score': random.randint(1, 100),
            'onboard_date': (datetime.now() - timedelta(days=random.randint(0, 3650))).strftime('%Y-%m-%d')
        })
    
    return pd.DataFrame(vendors)

def generate_payments(vendor_master, num_payments=50000):
    """Generate realistic payment transactions with various scenarios"""
    
    payments = []
    
    # Scenarios to test different aspects
    scenarios = [
        {'name': 'exact_match', 'probability': 0.60},
        {'name': 'typo_match', 'probability': 0.15},
        {'name': 'abbreviation_match', 'probability': 0.10},
        {'name': 'phonetic_match', 'probability': 0.05},
        {'name': 'exception_unapproved', 'probability': 0.08},
        {'name': 'exception_fake', 'probability': 0.02}
    ]
    
    # Common typos and variations
    def apply_typo(name):
        if len(name) < 5:
            return name
        # Simple typo: swap two adjacent letters
        pos = random.randint(0, len(name)-2)
        return name[:pos] + name[pos+1] + name[pos] + name[pos+2:]
    
    # Common abbreviations
    abbreviations = {
        'Corporation': 'Corp',
        'Incorporated': 'Inc',
        'Limited': 'Ltd',
        'Company': 'Co',
        'Technologies': 'Tech',
        'Solutions': 'Sol',
        'International': 'Intl'
    }
    
    # Fake vendors
    fake_vendors = [
        "Sneaky Consulting LLC", "Fake Services Inc", "Phantom Solutions",
        "Shell Company Ltd", "Hidden Partners", "Mystery Suppliers",
        "Questionable Services", "Unauthorized Consulting", "Ghost Vendors",
        "No Name Enterprise", "Unknown Services", "Suspicious Payments",
        "Unauthorized Access", "Fraudulent Services", "Illegitimate Business",
        "Fake Corp", "Shell LLC", "Ghost Company", "Phantom Services"
    ]
    
    # Get list of vendor names for reference
    vendor_names = vendor_master['vendor_name'].tolist()
    
    for i in range(num_payments):
        # Determine scenario based on probability
        rand = random.random()
        cum_prob = 0
        scenario = None
        for s in scenarios:
            cum_prob += s['probability']
            if rand <= cum_prob:
                scenario = s['name']
                break
        
        if scenario in ['exact_match', 'typo_match', 'abbreviation_match', 'phonetic_match']:
            # Select a random vendor
            vendor = random.choice(vendor_names)
            vendor_name = vendor
            
            # Apply transformations based on scenario
            if scenario == 'typo_match':
                if len(vendor_name) > 4:
                    vendor_name = apply_typo(vendor_name)
            
            elif scenario == 'abbreviation_match':
                for full, short in abbreviations.items():
                    if full in vendor_name:
                        vendor_name = vendor_name.replace(full, short)
                        break
                # Also sometimes shorten
                if random.random() < 0.3 and len(vendor_name) > 10:
                    vendor_name = vendor_name[:random.randint(8, len(vendor_name))]
            
            elif scenario == 'phonetic_match':
                # Simulate phonetic variations
                vendor_name = vendor_name.replace('C', 'K').replace('S', 'Z').replace('Ph', 'F').replace('tion', 'shun')
            
            amount = round(random.uniform(100, 50000), 2)
            
        elif scenario == 'exception_unapproved':
            # Realistic unapproved vendor (not in master)
            vendor_name = random.choice([
                "Local Office Supply", "Small IT Solutions", "Regional Consulting",
                "Quick Services", "Express Logistics", "City Maintenance",
                "Neighborhood Printers", "Independent Consultant", "Freelance Designer",
                "Temporary Staffing", "Event Planners", "Catering Services"
            ])
            amount = round(random.uniform(500, 25000), 2)
            
        else:  # exception_fake
            vendor_name = random.choice(fake_vendors)
            amount = round(random.uniform(5000, 100000), 2)
        
        # Create payment record
        payment = {
            'payment_id': f"P{i+1:06d}",
            'payee_name': vendor_name,
            'amount': amount,
            'payment_date': (datetime.now() - timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d'),
            'payment_method': random.choice(['ACH', 'Wire', 'Check', 'Credit Card', 'P-Card']),
            'department': random.choice(['IT', 'Finance', 'Marketing', 'Sales', 'HR', 'Operations', 'Legal', 'R&D']),
            'approver': random.choice(['John Smith', 'Jane Doe', 'Bob Johnson', 'Alice Brown', 'Charlie Wilson']),
            'invoice_number': f"INV-{random.randint(10000, 99999)}",
            'description': random.choice(['Software license', 'Hardware purchase', 'Consulting services', 'Cloud services', 'Maintenance', 'Subscription', 'Training'])
        }
        
        payments.append(payment)
        
        # Progress indicator
        if (i + 1) % 10000 == 0:
            print(f"   Generated {i+1} payments...")
    
    return pd.DataFrame(payments)

def generate_pcard_transactions(num_transactions=10000):
    """Generate P-Card transaction data"""
    
    pcard_data = []
    merchants = [
        "Staples", "Office Depot", "Amazon", "Best Buy", "Walmart",
        "Target", "Home Depot", "Lowe's", "Costco", "Sam's Club",
        "Uber", "Lyft", "Delta Air", "United Airlines", "Marriott",
        "Hilton", "Starbucks", "Dunkin", "McDonald's", "Chipotle"
    ]
    
    for i in range(num_transactions):
        pcard_data.append({
            'transaction_id': f"PC{i+1:06d}",
            'merchant_name': random.choice(merchants),
            'amount': round(random.uniform(5, 5000), 2),
            'transaction_date': (datetime.now() - timedelta(days=random.randint(0, 90))).strftime('%Y-%m-%d'),
            'cardholder': random.choice(['EMP001', 'EMP002', 'EMP003', 'EMP004', 'EMP005']),
            'department': random.choice(['IT', 'Marketing', 'Sales', 'Admin']),
            'approval_status': random.choice(['Approved', 'Pending', 'Flagged'])
        })
        
        if (i + 1) % 5000 == 0:
            print(f"   Generated {i+1} P-Card transactions...")
    
    return pd.DataFrame(pcard_data)

def generate_expense_reports(num_reports=5000):
    """Generate employee expense report data"""
    
    expenses = []
    categories = ['Travel', 'Meals', 'Office Supplies', 'Equipment', 'Training', 'Software']
    
    for i in range(num_reports):
        expenses.append({
            'expense_id': f"E{i+1:06d}",
            'employee_name': random.choice(['John Doe', 'Jane Smith', 'Bob Wilson', 'Alice Johnson', 'Charlie Brown']),
            'payee_name': random.choice(['Uber', 'Lyft', 'Airbnb', 'Marriott', 'Starbucks', 'Amazon', 'Office Depot']),
            'amount': round(random.uniform(10, 5000), 2),
            'expense_date': (datetime.now() - timedelta(days=random.randint(0, 180))).strftime('%Y-%m-%d'),
            'category': random.choice(categories),
            'status': random.choice(['Approved', 'Pending', 'Rejected']),
            'receipt_uploaded': random.choice([True, False])
        })
        
        if (i + 1) % 2500 == 0:
            print(f"   Generated {i+1} expense reports...")
    
    return pd.DataFrame(expenses)

def generate_bank_statements(num_transactions=20000):
    """Generate bank statement data"""
    
    banks = ['ABSA', 'FNB', 'Standard Bank', 'Nedbank', 'Capitec']
    transactions = []
    
    # Common payees from various sources
    payees = [
        "Microsoft Corp", "Amazon Web Services", "Google LLC", "Salesforce Inc",
        "Dell Technologies", "IBM Corporation", "Oracle America", "Adobe Systems",
        "Uber B.V.", "Airbnb Payments", "Marriott International", "Starbucks",
        "Sneaky Consulting", "Fake Services Ltd", "Shell Company Inc", "Questionable LLC"
    ]
    
    for i in range(num_transactions):
        transactions.append({
            'bank_account': random.choice(banks),
            'transaction_date': (datetime.now() - timedelta(days=random.randint(0, 90))).strftime('%Y-%m-%d'),
            'payee_name': random.choice(payees),
            'amount': round(random.uniform(10, 50000), 2),
            'reference': f"REF{random.randint(10000, 99999)}",
            'transaction_type': random.choice(['Debit', 'Credit']),
            'status': random.choice(['Cleared', 'Pending'])
        })
        
        if (i + 1) % 5000 == 0:
            print(f"   Generated {i+1} bank transactions...")
    
    return pd.DataFrame(transactions)

def create_test_data():
    """Create all test datasets"""
    
    print("=" * 60)
    print("Generating Test Data for PayReality")
    print("=" * 60)
    
    # Create test data directory
    os.makedirs('test_data', exist_ok=True)
    
    # Generate vendor master
    print("\n1. Generating Vendor Master (100 vendors)...")
    vendor_master = generate_vendor_master()
    vendor_master.to_csv('test_data/vendor_master.csv', index=False)
    print(f"   ✓ Saved: test_data/vendor_master.csv ({len(vendor_master)} records)")
    
    # Generate main payments (50,000 records)
    print("\n2. Generating Main Payment Data (50,000 records)...")
    payments = generate_payments(vendor_master, 50000)
    payments.to_csv('test_data/payments.csv', index=False)
    print(f"   ✓ Saved: test_data/payments.csv ({len(payments)} records)")
    
    # Generate P-Card transactions (10,000 records)
    print("\n3. Generating P-Card Transactions (10,000 records)...")
    pcard = generate_pcard_transactions(10000)
    pcard.to_csv('test_data/pcard_transactions.csv', index=False)
    print(f"   ✓ Saved: test_data/pcard_transactions.csv ({len(pcard)} records)")
    
    # Generate expense reports (5,000 records)
    print("\n4. Generating Expense Reports (5,000 records)...")
    expenses = generate_expense_reports(5000)
    expenses.to_csv('test_data/expense_reports.csv', index=False)
    print(f"   ✓ Saved: test_data/expense_reports.csv ({len(expenses)} records)")
    
    # Generate bank statements (20,000 records)
    print("\n5. Generating Bank Statement Data (20,000 records)...")
    bank_statements = generate_bank_statements(20000)
    bank_statements.to_csv('test_data/bank_statements.csv', index=False)
    print(f"   ✓ Saved: test_data/bank_statements.csv ({len(bank_statements)} records)")
    
    # Generate sample data for different file formats
    print("\n6. Generating Sample Data for Different Formats...")
    
    # Excel version
    payments.head(1000).to_excel('test_data/sample_payments.xlsx', index=False)
    print("   ✓ Created: test_data/sample_payments.xlsx (Excel format)")
    
    # Sample PDF invoice text (create a text file with sample invoice data)
    with open('test_data/sample_invoices.txt', 'w') as f:
        f.write("INVOICE #: INV-001\n")
        f.write("DATE: 2025-03-31\n")
        f.write("VENDOR: Microsoft Corp\n")
        f.write("AMOUNT: 15,000.00\n\n")
        f.write("INVOICE #: INV-002\n")
        f.write("DATE: 2025-03-30\n")
        f.write("VENDOR: Dell Technologies\n")
        f.write("AMOUNT: 12,500.00\n\n")
        f.write("INVOICE #: INV-003\n")
        f.write("DATE: 2025-03-29\n")
        f.write("VENDOR: Amazon Web Services\n")
        f.write("AMOUNT: 8,750.00\n\n")
        f.write("INVOICE #: INV-004\n")
        f.write("DATE: 2025-03-28\n")
        f.write("VENDOR: Fake Consulting LLC\n")
        f.write("AMOUNT: 25,000.00\n")
    
    print("   ✓ Created: test_data/sample_invoices.txt (sample invoice data)")
    
    # Generate statistics
    print("\n" + "=" * 60)
    print("DATA SUMMARY")
    print("=" * 60)
    print(f"Vendor Master:        {len(vendor_master):,} records")
    print(f"Main Payments:        {len(payments):,} records")
    print(f"P-Card Transactions:  {len(pcard):,} records")
    print(f"Expense Reports:      {len(expenses):,} records")
    print(f"Bank Statements:      {len(bank_statements):,} records")
    print(f"Total Test Records:   {len(vendor_master) + len(payments) + len(pcard) + len(expenses) + len(bank_statements):,}")
    
    # Calculate expected exceptions
    exceptions_count = len([p for p in payments.to_dict('records') if 'Fake' in p['payee_name'] or 'Sneaky' in p['payee_name'] or 'Shell' in p['payee_name'] or 'Ghost' in p['payee_name']])
    print(f"\nExpected Exceptions in Main Payments: ~{exceptions_count:,} (approx {exceptions_count/len(payments)*100:.1f}%)")
    
    print("\n" + "=" * 60)
    print("Test Data Generation Complete!")
    print("=" * 60)
    print("\nFiles are in the 'test_data' folder.")
    print("\nTo test PayReality, run:")
    print("  python main.py")
    print("  - Vendor Master: test_data/vendor_master.csv")
    print("  - Payments File: test_data/payments.csv")
    print("  - Client name: Test Client")
    print("  - Output: Choose option 2 (Desktop)")

if __name__ == "__main__":
    create_test_data()