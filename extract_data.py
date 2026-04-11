# extract_data.py
import pandas as pd
import numpy as np
import os

# Path to your Excel file
excel_path = r"C:\Users\user\OneDrive\Documents\01112025.xlsx"
output_dir = r"C:\Users\user\OneDrive\Documents\GitHub\Payreality"

print("="*60)
print("PayReality - Data Extractor")
print("="*60)

# Load the Excel file
print(f"\n📂 Loading Excel file from: {excel_path}")
df = pd.read_excel(excel_path)

print(f"✓ Loaded {len(df):,} rows, {len(df.columns)} columns")

# Look for award data (supplier names)
# Clean the supplier name column
df['awards_suppliers_name'] = df['awards_suppliers_name'].astype(str).str.strip()

# Find rows that actually have supplier names (not empty, not 'nan')
award_rows = df[
    (df['awards_suppliers_name'].notna()) & 
    (df['awards_suppliers_name'] != '') & 
    (df['awards_suppliers_name'] != 'nan') &
    (df['awards_suppliers_name'] != ' ')
]

print(f"\n📊 Rows with supplier names: {len(award_rows):,}")

if len(award_rows) == 0:
    print("\n⚠️ No award/supplier data found in this file.")
    print("   This file appears to contain only tender advertisements.")
    print("\n📝 Generating synthetic test data instead...")
    
    # Extract buyer names to use as synthetic suppliers
    buyers = df['buyer_name'].dropna().unique()
    suppliers = []
    for b in buyers:
        name = str(b).replace('"', '').strip()
        if name and len(name) > 3 and name not in suppliers:
            suppliers.append(name)
    
    print(f"✓ Found {len(suppliers)} unique buyer names to use as suppliers")
    
    # Generate synthetic payments
    np.random.seed(42)
    payments_data = []
    num_payments = min(2000, len(suppliers) * 20)
    
    for i in range(num_payments):
        supplier = np.random.choice(suppliers)
        amount = np.random.uniform(10000, 5000000)
        payments_data.append({
            'payee_name': supplier,
            'amount': round(amount, 2),
            'payment_date': ''
        })
    
    # Create vendor master
    vendor_df = pd.DataFrame({'vendor_name': suppliers})
    vendor_path = os.path.join(output_dir, 'vendor_master.csv')
    vendor_df.to_csv(vendor_path, index=False)
    print(f"\n✅ Created vendor_master.csv with {len(suppliers):,} suppliers")
    
    # Create payments file
    payments_df = pd.DataFrame(payments_data)
    payments_path = os.path.join(output_dir, 'payments.csv')
    payments_df.to_csv(payments_path, index=False)
    print(f"✅ Created payments.csv with {len(payments_df):,} payment records")
    print(f"✅ Total synthetic value: R {payments_df['amount'].sum():,.2f}")
    
else:
    print(f"\n✅ Found {len(award_rows):,} award records!")
    
    # Extract unique suppliers
    suppliers = award_rows['awards_suppliers_name'].unique()
    print(f"✅ Found {len(suppliers):,} unique suppliers")
    
    # Create vendor master
    vendor_df = pd.DataFrame({'vendor_name': suppliers})
    vendor_path = os.path.join(output_dir, 'vendor_master.csv')
    vendor_df.to_csv(vendor_path, index=False)
    print("✅ Created vendor_master.csv")
    
    # Check for amount column
    amount_col = None
    for col in ['amount', 'value', 'award_amount', 'contract_value']:
        if col in df.columns:
            amount_col = col
            break
    
    # Create payments file
    if amount_col:
        amounts = award_rows[amount_col].fillna(0).values
        print(f"✓ Using real amounts from column: {amount_col}")
    else:
        amounts = np.random.uniform(10000, 5000000, len(award_rows)).round(2)
        print("⚠️ No amount column found - generated synthetic amounts")
    
    # Get dates if available
    dates = award_rows['awards_date'].fillna('').values if 'awards_date' in award_rows.columns else [''] * len(award_rows)
    
    payments_df = pd.DataFrame({
        'payee_name': award_rows['awards_suppliers_name'].values,
        'amount': amounts,
        'payment_date': dates
    })
    
    payments_path = os.path.join(output_dir, 'payments.csv')
    payments_df.to_csv(payments_path, index=False)
    print(f"✅ Created payments.csv with {len(payments_df):,} records")
    print(f"✅ Total value: R {payments_df['amount'].sum():,.2f}")
    
    # Show sample suppliers
    print("\n" + "="*60)
    print("SAMPLE SUPPLIERS (first 10):")
    print("="*60)
    for i, supplier in enumerate(suppliers[:10], 1):
        display_name = supplier[:60] + "..." if len(supplier) > 60 else supplier
        print(f"{i:3}. {display_name}")

print("\n" + "="*60)
print("✅ EXTRACTION COMPLETE!")
print("="*60)
print(f"\n📁 Files created in: {output_dir}")
print("   📄 vendor_master.csv - List of approved vendors")
print("   📄 payments.csv - Payment transactions to analyze")
print("\n🚀 Next steps:")
print("   1. Open PayReality application")
print("   2. Load vendor_master.csv as 'Vendor Master'")
print("   3. Load payments.csv as 'Payments File'")
print("   4. Click 'Run Analysis'")
print("\n" + "="*60)