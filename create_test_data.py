import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

os.chdir(r"C:\Users\user\OneDrive\Documents\GitHub\Payreality")

print("="*60)
print("PayReality - Creating Test Data")
print("="*60)

# Real South African company names as approved vendors
approved_vendors = [
    "Eskom Holdings SOC Ltd", "Transnet SOC Ltd", "South African Airways",
    "MTN Group Ltd", "Vodacom Group Ltd", "Telkom SA SOC Ltd",
    "Standard Bank Group Ltd", "FirstRand Bank Ltd", "Absa Group Ltd",
    "Nedbank Group Ltd", "Capitec Bank Holdings Ltd", "Shoprite Holdings Ltd",
    "Pick n Pay Stores Ltd", "Woolworths Holdings Ltd", "Sasol Ltd",
    "Anglo American Platinum Ltd", "Bidvest Group Ltd", "Discovery Ltd",
    "Sanlam Ltd", "Old Mutual Ltd", "Naspers Ltd", "MultiChoice Group Ltd",
    "Mr Price Group Ltd", "Clicks Group Ltd", "Truworths International Ltd",
    "Foschini Group Ltd", "Cell C Ltd", "Rain SA (Pty) Ltd",
    "South African Post Office", "Prasa"
]

# Fake vendors not in approved list (will cause exceptions)
fake_vendors = [
    "New Dawn Trading 147 CC", "Bright Star Consulting Pty Ltd",
    "Falcon Business Solutions", "Phoenix Global Trading",
    "Apex Logistics SA", "Zenith Procurement Services",
    "Nexus Supply Chain Solutions", "Vertex Technologies",
    "Synergy Business Solutions", "Titan Industrial Services",
    "Orion Consulting Group", "Pegasus Trading Enterprise",
    "Mercury Business Solutions", "Atlas Procurement Services",
    "Helix Industrial Supply", "Nova Tech Solutions"
]

print(f"Approved vendors: {len(approved_vendors)}")
print(f"Fake vendors: {len(fake_vendors)}")

# Generate 5000 payment records
np.random.seed(42)
num_payments = 5000

payee_names = []
amounts = []
payment_dates = []

for i in range(num_payments):
    # 70% to approved, 30% to fake vendors
    if random.random() < 0.7:
        payee = random.choice(approved_vendors)
    else:
        payee = random.choice(fake_vendors)
    payee_names.append(payee)
    
    # Random amount between R1,000 and R10,000,000
    amount = round(random.uniform(1000, 10000000), 2)
    amounts.append(amount)
    
    # Random date in 2024-2025
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 12, 31)
    random_days = random.randint(0, (end_date - start_date).days)
    payment_date = start_date + timedelta(days=random_days)
    payment_dates.append(payment_date.strftime('%Y-%m-%d'))

# Create DataFrames
payments_df = pd.DataFrame({
    'payee_name': payee_names,
    'amount': amounts,
    'payment_date': payment_dates
})

vendor_master_df = pd.DataFrame({
    'vendor_name': approved_vendors
})

# Save to CSV
vendor_master_df.to_csv('vendor_master.csv', index=False)
payments_df.to_csv('payments.csv', index=False)

# Calculate statistics
total_value = payments_df['amount'].sum()
exception_mask = ~payments_df['payee_name'].isin(approved_vendors)
exception_count = exception_mask.sum()
exception_value = payments_df[exception_mask]['amount'].sum()

print(f"\nTest Data Created:")
print(f"   Total payments: {num_payments:,}")
print(f"   Total value: R {total_value:,.2f}")
print(f"   Approved payments: {num_payments - exception_count:,}")
print(f"   Exception payments: {exception_count:,} ({exception_count/num_payments*100:.1f}%)")
print(f"   Exception value: R {exception_value:,.2f} ({exception_value/total_value*100:.1f}%)")

print("\nFiles created:")
print("   vendor_master.csv")
print("   payments.csv")
print("\nReady to run PayReality analysis!")