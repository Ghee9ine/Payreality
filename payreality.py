import pandas as pd
from rapidfuzz import fuzz, process

print("=" * 50)
print("PAYREALITY - Independent Control Validation")
print("=" * 50)

# Load files
print("\n1. Loading files...")
master_df = pd.read_csv('vendor_master.csv')
payments_df = pd.read_csv('payments.csv')

print(f"   Loaded {len(master_df)} vendors")
print(f"   Loaded {len(payments_df)} payments")

# Get vendor names
master_vendors = master_df['vendor_name'].tolist()

print("\n2. Running fuzzy matching...")

# Simple matching for each payment
exceptions = []
total_spend = 0
exception_spend = 0

for idx, row in payments_df.iterrows():
    payee = row['payee_name']
    amount = row['amount']
    total_spend += amount
    
    # Check if payee is in master (simple check first)
    if payee in master_vendors:
        status = "APPROVED"
        matched = payee
    else:
        # Try fuzzy matching
        result = process.extractOne(payee, master_vendors, scorer=fuzz.token_sort_ratio)
        if result and result[1] >= 80:
            status = "MATCHED (fuzzy)"
            matched = result[0]
        else:
            status = "EXCEPTION"
            matched = "None"
            exceptions.append(payee)
            exception_spend += amount
    
    print(f"   {payee[:20]:20} → {status}")

# Calculate Control Entropy Score
entropy_score = (exception_spend / total_spend * 100) if total_spend > 0 else 0

print("\n" + "=" * 50)
print("PAYREALITY REPORT SUMMARY")
print("=" * 50)
print(f"Total Payments: {len(payments_df)}")
print(f"Total Spend: R {total_spend:,.2f}")
print(f"Exceptions Found: {len(exceptions)}")
print(f"Exception Spend: R {exception_spend:,.2f}")
print(f"Control Entropy Score: {entropy_score:.2f}%")
print("=" * 50)

if exceptions:
    print("\nEXCEPTIONS (payments to unapproved vendors):")
    for e in exceptions:
        print(f"  - {e}")

# Create Excel report
print("\n3. Creating Excel report...")
output_file = 'payreality_report.xlsx'

# Create summary dataframe
summary_df = pd.DataFrame({
    'Metric': ['Total Payments', 'Total Spend (R)', 'Exceptions Found', 'Exception Spend (R)', 'Control Entropy Score (%)'],
    'Value': [len(payments_df), total_spend, len(exceptions), exception_spend, f'{entropy_score:.2f}%']
})

# Create exceptions dataframe
exceptions_df = payments_df[payments_df['payee_name'].isin(exceptions)]

# Save to Excel
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    summary_df.to_excel(writer, sheet_name='Summary', index=False)
    exceptions_df.to_excel(writer, sheet_name='Exceptions', index=False)
    payments_df.to_excel(writer, sheet_name='All Payments', index=False)

print(f"   Report saved: {output_file}")
print("\nDone!")