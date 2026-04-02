"""
PayReality Phase 2 — Sample Data Generator
Generates realistic test data covering all 7 matching passes and Phase 2 controls
"""

import pandas as pd
import random
from pathlib import Path
from datetime import datetime, timedelta

random.seed(42)

APPROVED = [
    "Microsoft South Africa (Pty) Ltd",
    "IBM South Africa",
    "Oracle Corporation",
    "SAP SE",
    "Deloitte & Touche",
    "PricewaterhouseCoopers",
    "KPMG Services",
    "Ernst & Young Advisory",
    "Accenture South Africa",
    "Vodacom Group",
    "MTN Group",
    "Standard Bank",
    "FirstRand Bank",
    "Absa Group",
    "Nedbank",
    "Old Mutual",
    "Discovery Health",
    "Shoprite Holdings",
    "Pick n Pay Stores",
    "Woolworths Holdings",
    "Sasol Limited",
    "Anglo American",
    "BHP Group",
    "Transnet SOC",
    "Eskom Holdings",
    "Telkom SA",
    "Bidvest Group",
    "Tiger Brands",
    "MultiChoice Group",
    "City Lodge Hotels",
]

def rand_date(start="2023-01-01", end="2024-06-30"):
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end,   "%Y-%m-%d")
    return (s + timedelta(days=random.randint(0, (e - s).days))).strftime("%Y-%m-%d")

def make_payments():
    rows = []

    # PASS 1 — Exact matches (clean payments, should NOT be exceptions)
    for vendor in random.sample(APPROVED, 10):
        rows.append({"payee_name": vendor, "amount": round(random.uniform(10000, 500000), 2),
                     "payment_date": rand_date()})

    # PASS 2 — Normalised variants (case / punctuation differences)
    rows += [
        {"payee_name": "microsoft south africa (pty) ltd", "amount": 125000.00, "payment_date": rand_date()},
        {"payee_name": "IBM SOUTH AFRICA", "amount": 88000.00, "payment_date": rand_date()},
        {"payee_name": "Deloitte and Touche", "amount": 210000.00, "payment_date": rand_date()},
        {"payee_name": "PricewaterhouseCoopers.", "amount": 175000.00, "payment_date": rand_date()},
    ]

    # PASS 3 — Token sort (word order swapped)
    rows += [
        {"payee_name": "Africa South Microsoft (Pty) Ltd", "amount": 95000.00, "payment_date": rand_date()},
        {"payee_name": "Advisory Ernst and Young", "amount": 230000.00, "payment_date": rand_date()},
        {"payee_name": "South Africa Accenture", "amount": 145000.00, "payment_date": rand_date()},
    ]

    # PASS 4 — Partial matches
    rows += [
        {"payee_name": "Microsoft", "amount": 55000.00, "payment_date": rand_date()},
        {"payee_name": "IBM", "amount": 72000.00, "payment_date": rand_date()},
        {"payee_name": "Deloitte", "amount": 185000.00, "payment_date": rand_date()},
        {"payee_name": "PwC", "amount": 95000.00, "payment_date": rand_date()},
    ]

    # PASS 5 — Levenshtein (typos / transpositions)
    rows += [
        {"payee_name": "Micosoft South Africa Pty Ltd", "amount": 300000.00, "payment_date": rand_date()},
        {"payee_name": "Microsft South Africa", "amount": 250000.00, "payment_date": rand_date()},
        {"payee_name": "SAP ES", "amount": 115000.00, "payment_date": rand_date()},
        {"payee_name": "KMPG Services", "amount": 180000.00, "payment_date": rand_date()},
        {"payee_name": "Vodaocm Group", "amount": 66000.00, "payment_date": rand_date()},
    ]

    # PASS 6 — Phonetic
    rows += [
        {"payee_name": "Phirstrand Bank", "amount": 420000.00, "payment_date": rand_date()},
        {"payee_name": "Nedbank Group", "amount": 180000.00, "payment_date": rand_date()},
        {"payee_name": "Olde Mutual", "amount": 310000.00, "payment_date": rand_date()},
        {"payee_name": "Vodacom Groop", "amount": 145000.00, "payment_date": rand_date()},
    ]

    # PASS 7 — Obfuscation
    rows += [
        {"payee_name": "M.i.c.r.o.s.o.f.t SA",      "amount": 750000.00, "payment_date": rand_date()},
        {"payee_name": "M1cr0s0ft South Africa",      "amount": 620000.00, "payment_date": rand_date()},
        {"payee_name": "Miiicrosoft SA",               "amount": 580000.00, "payment_date": rand_date()},
        {"payee_name": "0racle Corporation",           "amount": 490000.00, "payment_date": rand_date()},
        {"payee_name": "S4P SE",                       "amount": 320000.00, "payment_date": rand_date()},
    ]

    # TRUE EXCEPTIONS — not on vendor list at all
    rows += [
        {"payee_name": "Shell Company Holdings",       "amount": 1200000.00, "payment_date": rand_date()},
        {"payee_name": "Rapid Cash Solutions",         "amount": 850000.00,  "payment_date": rand_date()},
        {"payee_name": "Global Finance Trust",         "amount": 650000.00,  "payment_date": rand_date()},
        {"payee_name": "Premier Consulting Pty Ltd",   "amount": 430000.00,  "payment_date": rand_date()},
        {"payee_name": "Unknown Supplier 001",         "amount": 120000.00,  "payment_date": rand_date()},
        {"payee_name": "Cash Direct Transfer",         "amount": 2100000.00, "payment_date": rand_date()},
        {"payee_name": "Apex Trade Solutions",         "amount": 890000.00,  "payment_date": "2024-06-01"},  # weekend
        {"payee_name": "New Vendor Inc",               "amount": 1500000.00, "payment_date": rand_date()},
    ]

    # DUPLICATES — same vendor + amount, different dates
    rows.append({"payee_name": "Shell Company Holdings", "amount": 1200000.00, "payment_date": rand_date()})
    rows.append({"payee_name": "Microsoft South Africa (Pty) Ltd", "amount": 125000.00, "payment_date": rand_date()})

    # Weekend payments
    rows.append({"payee_name": "Rapid Cash Solutions", "amount": 340000.00, "payment_date": "2024-05-25"})  # Saturday
    rows.append({"payee_name": "Global Finance Trust",  "amount": 210000.00, "payment_date": "2024-03-31"})  # Sunday

    random.shuffle(rows)
    return pd.DataFrame(rows)


def make_vendor_master():
    df = pd.DataFrame({"vendor_name": APPROVED})
    # Introduce some health issues
    df = pd.concat([df, pd.DataFrame({"vendor_name": [
        "Microsoft South Africa (Pty) Ltd",  # duplicate
        "",                                   # blank
        "A",                                  # too short
    ]})], ignore_index=True)
    return df


if __name__ == "__main__":
    out = Path("data/sample")
    out.mkdir(parents=True, exist_ok=True)

    vm = make_vendor_master()
    vm.to_csv(out / "vendor_master.csv", index=False)
    print(f"Vendor master: {len(vm)} rows → {out / 'vendor_master.csv'}")

    pay = make_payments()
    pay.to_csv(out / "payments.csv", index=False)
    print(f"Payments:      {len(pay)} rows → {out / 'payments.csv'}")

    print("\nSample data ready. Run: python payreality_app.py")
