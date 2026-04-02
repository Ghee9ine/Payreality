"""
PayReality Core Engine - Phase 2
7-Pass Semantic Matching + Control Mapping + Explainability + Confidence Scoring
"""

import pandas as pd
import os
import re
import json
import hashlib
import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from pathlib import Path

try:
    from rapidfuzz import fuzz, process
except ImportError:
    raise ImportError("rapidfuzz required: pip install rapidfuzz")


# ─── Control Taxonomy ────────────────────────────────────────────────────────

CONTROL_TAXONOMY = {
    "VDC": {
        "id": "VDC",
        "name": "Vendor Duplication Control",
        "description": "Ensures no duplicate vendor records receive payments",
        "severity": "High",
        "category": "Master Data Integrity",
    },
    "AVC": {
        "id": "AVC",
        "name": "Approved Vendor Control",
        "description": "Verifies payments go to vendors on the approved vendor list",
        "severity": "Critical",
        "category": "Payment Integrity",
    },
    "VNC": {
        "id": "VNC",
        "name": "Vendor Name Consistency Control",
        "description": "Detects name variations, typos, aliases, and obfuscation",
        "severity": "High",
        "category": "Payment Integrity",
    },
    "PAC": {
        "id": "PAC",
        "name": "Payment Authorization Control",
        "description": "Flags off-cycle, weekend, and unusual payment patterns",
        "severity": "Medium",
        "category": "Authorization",
    },
    "VTC": {
        "id": "VTC",
        "name": "Vendor Tenure Control",
        "description": "Identifies new vendors receiving high-value payments",
        "severity": "High",
        "category": "Onboarding Risk",
    },
    "VMH": {
        "id": "VMH",
        "name": "Vendor Master Health Control",
        "description": "Assesses completeness and integrity of vendor master data",
        "severity": "Medium",
        "category": "Master Data Integrity",
    },
    "OBC": {
        "id": "OBC",
        "name": "Obfuscation Detection Control",
        "description": "Detects deliberate name manipulation to bypass controls",
        "severity": "Critical",
        "category": "Fraud Detection",
    },
}


# ─── Exceptions ──────────────────────────────────────────────────────────────

class DataValidationError(Exception):
    pass


# ─── Engine ──────────────────────────────────────────────────────────────────

class PayRealityEngine:

    def __init__(self, config: Dict = None, db_path: str = None):
        self.config = config or {}
        self.logger = logging.getLogger("PayReality.Engine")
        self.master_df = None
        self.payments_df = None

        # Audit DB
        if db_path is None:
            db_path = str(Path.home() / "PayReality_Data" / "payreality.db")
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── DB ────────────────────────────────────────────────────────────────────

    def _init_db(self):
        with self._db() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    run_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    client_name TEXT,
                    master_file_hash TEXT,
                    payments_file_hash TEXT,
                    threshold INTEGER,
                    config_version TEXT,
                    total_payments INTEGER,
                    exception_count INTEGER,
                    exception_spend REAL,
                    entropy_score REAL,
                    duplicate_count INTEGER,
                    report_path TEXT,
                    status TEXT DEFAULT 'complete',
                    params_json TEXT
                );

                CREATE TABLE IF NOT EXISTS run_exceptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    payee_name TEXT,
                    amount REAL,
                    payment_date TEXT,
                    control_ids TEXT,
                    confidence_score INTEGER,
                    risk_level TEXT,
                    risk_score INTEGER,
                    match_strategy TEXT,
                    match_score INTEGER,
                    explanation TEXT,
                    reasons_json TEXT,
                    FOREIGN KEY(run_id) REFERENCES analysis_runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS email_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    smtp_server TEXT,
                    smtp_port INTEGER,
                    email_user TEXT,
                    email_password TEXT,
                    recipient_list TEXT
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)

    def _db(self):
        return sqlite3.connect(self.db_path)

    def save_run(self, run_id: str, client_name: str,
                 master_hash: str, payments_hash: str,
                 threshold: int, results: Dict,
                 report_path: str = None) -> str:
        params = {
            "threshold": threshold,
            "config_version": self.config.get("version", "1.0.0"),
        }
        with self._db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO analysis_runs
                (run_id, timestamp, client_name, master_file_hash, payments_file_hash,
                 threshold, config_version, total_payments, exception_count, exception_spend,
                 entropy_score, duplicate_count, report_path, params_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                run_id,
                datetime.now().isoformat(),
                client_name,
                master_hash,
                payments_hash,
                threshold,
                self.config.get("version", "1.0.0"),
                results["total_payments"],
                results["exception_count"],
                results["exception_spend"],
                results["entropy_score"],
                len(results.get("duplicates", [])),
                report_path,
                json.dumps(params),
            ))
            # Save individual exceptions
            for ex in results.get("exceptions", []):
                conn.execute("""
                    INSERT INTO run_exceptions
                    (run_id, payee_name, amount, payment_date, control_ids, confidence_score,
                     risk_level, risk_score, match_strategy, match_score, explanation, reasons_json)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    run_id,
                    ex.get("payee_name", ""),
                    ex.get("amount", 0),
                    ex.get("payment_date", ""),
                    ",".join(ex.get("control_ids", [])),
                    ex.get("confidence_score", 0),
                    ex.get("risk_level", "Low"),
                    ex.get("risk_score", 0),
                    ex.get("match_strategy", "none"),
                    ex.get("match_score", 0),
                    ex.get("explanation", ""),
                    json.dumps(ex.get("risk_reasons", [])),
                ))
        return run_id

    def get_history(self, limit: int = 50) -> List[Dict]:
        with self._db() as conn:
            rows = conn.execute("""
                SELECT run_id, timestamp, client_name, total_payments, exception_count,
                       exception_spend, entropy_score, duplicate_count, report_path
                FROM analysis_runs ORDER BY timestamp DESC LIMIT ?
            """, (limit,)).fetchall()
        return [
            {
                "run_id": r[0], "timestamp": r[1], "client_name": r[2],
                "total_payments": r[3], "exception_count": r[4],
                "exception_spend": r[5], "entropy_score": r[6],
                "duplicate_count": r[7], "report_path": r[8],
            }
            for r in rows
        ]

    def get_entropy_trend(self) -> List[Dict]:
        with self._db() as conn:
            rows = conn.execute(
                "SELECT timestamp, entropy_score, client_name FROM analysis_runs ORDER BY timestamp ASC"
            ).fetchall()
        return [{"timestamp": r[0], "entropy_score": r[1], "client_name": r[2]} for r in rows]

    # ── File I/O ──────────────────────────────────────────────────────────────

    @staticmethod
    def hash_file(filepath: str) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()[:16]

    def load_dataframe(self, filepath: str) -> pd.DataFrame:
        """Multi-encoding, multi-format loader."""
        ext = Path(filepath).suffix.lower()
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

        if ext in (".xlsx", ".xls"):
            try:
                return pd.read_excel(filepath)
            except Exception as e:
                raise DataValidationError(f"Cannot read Excel file: {e}")

        for enc in encodings:
            try:
                df = pd.read_csv(filepath, encoding=enc)
                self.logger.debug(f"Read {filepath} with {enc}")
                return df
            except UnicodeDecodeError:
                continue
            except Exception as e:
                raise DataValidationError(f"Cannot read file: {e}")

        raise DataValidationError(f"Could not read {filepath} with any encoding")

    def _normalise_columns(self, df: pd.DataFrame, expected: List[str]) -> pd.DataFrame:
        """Case-insensitive column mapping."""
        col_map = {c.lower().strip(): c for c in df.columns}
        rename = {}
        for exp in expected:
            if exp not in df.columns:
                for variant in [exp, exp.replace("_", " "), exp.replace(" ", "_")]:
                    if variant.lower() in col_map:
                        rename[col_map[variant.lower()]] = exp
                        break
        if rename:
            df = df.rename(columns=rename)
            self.logger.info(f"Renamed columns: {rename}")
        return df

    def load_files(self, master_file: str, payments_file: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        self.logger.info("Loading input files")

        master_df = self.load_dataframe(master_file)
        master_df = self._normalise_columns(master_df, ["vendor_name"])

        if "vendor_name" not in master_df.columns:
            # Try name-like columns
            for col in master_df.columns:
                if any(k in col.lower() for k in ["vendor", "supplier", "name"]):
                    master_df = master_df.rename(columns={col: "vendor_name"})
                    break

        if "vendor_name" not in master_df.columns:
            raise DataValidationError(
                f"Vendor Master missing 'vendor_name' column.\nFound: {list(master_df.columns)}"
            )

        payments_df = self.load_dataframe(payments_file)
        payments_df = self._normalise_columns(payments_df, ["payee_name", "amount"])

        # Flexible column mapping for payments
        for col in payments_df.columns:
            cl = col.lower()
            if "payee_name" not in payments_df.columns and any(k in cl for k in ["payee", "vendor", "supplier", "pay_to", "recipient", "name"]):
                payments_df = payments_df.rename(columns={col: "payee_name"})
            if "amount" not in payments_df.columns and any(k in cl for k in ["amount", "value", "total", "invoice_amount", "price"]):
                payments_df = payments_df.rename(columns={col: "amount"})

        missing = [c for c in ["payee_name", "amount"] if c not in payments_df.columns]
        if missing:
            raise DataValidationError(
                f"Payments file missing columns: {missing}.\nFound: {list(payments_df.columns)}"
            )

        # Coerce amount to numeric
        payments_df["amount"] = pd.to_numeric(payments_df["amount"], errors="coerce").fillna(0)

        # Parse date if present
        for col in payments_df.columns:
            if "date" in col.lower() and "payment_date" not in payments_df.columns:
                payments_df = payments_df.rename(columns={col: "payment_date"})
                break

        if "payment_date" not in payments_df.columns:
            payments_df["payment_date"] = ""

        self.master_df = master_df
        self.payments_df = payments_df

        self.logger.info(f"Loaded {len(master_df)} vendors, {len(payments_df)} payments")
        return master_df, payments_df

    # ── Name Cleaning ─────────────────────────────────────────────────────────

    _SUFFIXES = [
        " pty ltd", " (pty) ltd", " pty", " ltd", " inc", " corp", " llc",
        " co", " cc", " limited", " corporation", " incorporated",
        " company", " holdings", " group", " international", " systems",
        " technologies", " solutions", " services", " enterprises",
    ]

    def clean_name(self, name: str) -> str:
        if not name or (isinstance(name, float) and pd.isna(name)):
            return ""
        n = str(name).lower().strip()
        n = re.sub(r"[^\w\s]", " ", n)
        n = re.sub(r"\s+", " ", n).strip()
        for s in self._SUFFIXES:
            if n.endswith(s):
                n = n[: -len(s)].strip()
                break
        return n

    def phonetic_key(self, text: str) -> str:
        """Consonant skeleton + substitutions for phonetic matching."""
        t = text.lower()
        t = re.sub(r"ph|gh", "f", t)
        t = re.sub(r"ck|c(?=[^eihy])", "k", t)
        t = re.sub(r"sh|ch", "x", t)
        t = re.sub(r"[aeiou]", "", t)
        t = re.sub(r"(.)\1+", r"\1", t)  # de-duplicate consecutive consonants
        return t

    def detect_obfuscation(self, name: str) -> Tuple[bool, str, str]:
        """
        Returns (detected, cleaned_name, obfuscation_type)
        Types: dot_spacing, leetspeak, char_repetition, homoglyph
        """
        # Dot/space spacing: M.i.c.r.o.s.o.f.t
        if re.search(r"(\w\.){3,}", name):
            cleaned = re.sub(r"\.", "", name)
            return True, cleaned, "dot_spacing"

        # Leetspeak
        leet = {"3": "e", "0": "o", "1": "i", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
        has_leet = any(c in name for c in leet)
        if has_leet:
            cleaned = name
            for k, v in leet.items():
                cleaned = cleaned.replace(k, v)
            return True, cleaned, "leetspeak"

        # Repeated characters
        if re.search(r"(.)\1{2,}", name):
            cleaned = re.sub(r"(.)\1{2,}", r"\1\1", name)
            return True, cleaned, "char_repetition"

        # Unicode homoglyphs (basic Latin lookalikes)
        homoglyph_map = {
            "\u0430": "a", "\u04cf": "l", "\u043e": "o",
            "\u0435": "e", "\u0441": "c", "\u0440": "p",
        }
        if any(c in name for c in homoglyph_map):
            cleaned = "".join(homoglyph_map.get(c, c) for c in name)
            return True, cleaned, "homoglyph"

        return False, name, "none"

    # ── 7-Pass Matching ───────────────────────────────────────────────────────

    def semantic_match_7pass(
        self,
        payee: str,
        master_vendors: List[str],
        master_clean: List[str],
        threshold: int = 80,
    ) -> Tuple[Optional[str], int, str, List[str]]:
        """
        Returns (matched_vendor, score, strategy, passes_tried)
        """
        passes_tried = []

        # Pass 1: Exact
        passes_tried.append("exact")
        if payee in master_vendors:
            return payee, 100, "exact", passes_tried

        # Pass 2: Normalised
        passes_tried.append("normalized")
        payee_clean = self.clean_name(payee)
        for i, vc in enumerate(master_clean):
            if payee_clean == vc and payee_clean:
                return master_vendors[i], 100, "normalized", passes_tried

        if not payee_clean:
            return None, 0, "none", passes_tried

        # Pass 3: Token Sort
        passes_tried.append("token_sort")
        r = process.extractOne(payee_clean, master_clean, scorer=fuzz.token_sort_ratio)
        if r and r[1] >= threshold:
            return master_vendors[r[2]], r[1], "token_sort", passes_tried

        # Pass 4: Partial
        passes_tried.append("partial")
        r = process.extractOne(payee_clean, master_clean, scorer=fuzz.partial_ratio)
        if r and r[1] >= threshold:
            return master_vendors[r[2]], r[1], "partial", passes_tried

        # Pass 5: Levenshtein (QRatio)
        passes_tried.append("levenshtein")
        r = process.extractOne(payee_clean, master_clean, scorer=fuzz.QRatio)
        if r and r[1] >= max(threshold - 5, 60):
            return master_vendors[r[2]], r[1], "levenshtein", passes_tried

        # Pass 6: Phonetic
        passes_tried.append("phonetic")
        payee_ph = self.phonetic_key(payee_clean)
        if payee_ph:
            master_ph = [self.phonetic_key(v) for v in master_clean]
            r = process.extractOne(payee_ph, master_ph, scorer=fuzz.token_sort_ratio)
            if r and r[1] >= threshold:
                return master_vendors[r[2]], r[1], "phonetic", passes_tried

        # Pass 7: Obfuscation
        passes_tried.append("obfuscation")
        is_obf, cleaned, obf_type = self.detect_obfuscation(payee)
        if is_obf:
            cleaned_n = self.clean_name(cleaned)
            r = process.extractOne(cleaned_n, master_clean, scorer=fuzz.token_sort_ratio)
            if r and r[1] >= threshold:
                return master_vendors[r[2]], r[1], f"obfuscation_{obf_type}", passes_tried

        return None, 0, "none", passes_tried

    # ── Control Mapping ───────────────────────────────────────────────────────

    def map_controls(
        self,
        is_approved: bool,
        strategy: str,
        is_duplicate: bool,
        is_weekend: bool,
        is_new_vendor: bool,
        high_spend: bool,
        obfuscation_detected: bool,
    ) -> List[str]:
        """Return list of violated control IDs."""
        controls = []
        if not is_approved:
            controls.append("AVC")
        if strategy.startswith("obfuscation") or obfuscation_detected:
            controls.append("OBC")
        elif strategy in ("token_sort", "partial", "levenshtein", "phonetic", "normalized"):
            controls.append("VNC")
        if is_duplicate:
            controls.append("VDC")
        if is_weekend:
            controls.append("PAC")
        if is_new_vendor and high_spend:
            controls.append("VTC")
        return controls if controls else ["AVC"]

    # ── Explainability ────────────────────────────────────────────────────────

    def build_explanation(
        self,
        payee: str,
        matched_vendor: Optional[str],
        score: int,
        strategy: str,
        amount: float,
        controls: List[str],
        is_new_vendor: bool,
        weekend: bool,
        duplicate: bool,
    ) -> str:
        """Generate a single human-readable explanation string."""
        parts = []

        if strategy == "none":
            parts.append(
                f"'{payee}' could not be matched to any approved vendor "
                f"after all 7 matching passes."
            )
        elif strategy == "exact":
            parts.append(f"'{payee}' matched exactly to approved vendor '{matched_vendor}'.")
        elif strategy == "normalized":
            parts.append(
                f"'{payee}' matched '{matched_vendor}' after normalisation "
                f"(case and punctuation removed)."
            )
        elif strategy == "token_sort":
            parts.append(
                f"'{payee}' matched '{matched_vendor}' with {score}% similarity "
                f"after word-order sorting."
            )
        elif strategy == "partial":
            parts.append(
                f"'{payee}' partially matched '{matched_vendor}' ({score}% similarity); "
                f"one name appears to be a substring of the other."
            )
        elif strategy == "levenshtein":
            parts.append(
                f"'{payee}' matched '{matched_vendor}' with {score}% edit-distance similarity "
                f"— possible typo or transposition."
            )
        elif strategy == "phonetic":
            parts.append(
                f"Phonetic match between '{payee}' and '{matched_vendor}' ({score}% similarity) "
                f"— names sound similar but are spelled differently."
            )
        elif strategy.startswith("obfuscation"):
            obf_type = strategy.split("_", 1)[1] if "_" in strategy else "unknown"
            type_desc = {
                "dot_spacing": "dot-spacing (e.g. M.i.c.r.o.s.o.f.t)",
                "leetspeak": "leetspeak character substitution (e.g. 3=E, 0=O)",
                "char_repetition": "repeated characters (e.g. Miiiicrosoft)",
                "homoglyph": "Unicode homoglyph substitution",
            }.get(obf_type, obf_type)
            parts.append(
                f"Obfuscation detected in '{payee}' via {type_desc}; "
                f"deobfuscated form matched '{matched_vendor}' at {score}%."
            )

        # Supplementary facts
        fmt = f"R {amount:,.0f}" if amount >= 0 else f"-R {abs(amount):,.0f}"
        parts.append(f"Payment amount: {fmt}.")

        if "AVC" in controls and strategy == "none":
            parts.append("Vendor is not on the approved vendor list.")
        if "VTC" in controls:
            parts.append("New vendor receiving high-value payment — elevated onboarding risk.")
        if "PAC" in controls and weekend:
            parts.append("Payment processed on a weekend or public holiday.")
        if "VDC" in controls and duplicate:
            parts.append("Potential duplicate payment detected.")
        if "OBC" in controls:
            parts.append("Deliberate name obfuscation is a strong indicator of fraud risk.")

        return " ".join(parts)

    # ── Confidence Scoring ────────────────────────────────────────────────────

    def confidence_score(
        self,
        strategy: str,
        match_score: int,
        passes_tried: List[str],
        amount: float,
        is_new_vendor: bool,
        obfuscation: bool,
        duplicate: bool,
        weekend: bool,
    ) -> int:
        """
        0-100 score: how confident are we this is a genuine control failure?
        Higher = more likely real problem.
        """
        score = 0

        # Base from strategy
        strategy_weight = {
            "none": 70,           # Totally unmatched = very suspicious
            "obfuscation_dot_spacing": 85,
            "obfuscation_leetspeak": 85,
            "obfuscation_char_repetition": 75,
            "obfuscation_homoglyph": 90,
            "phonetic": 55,
            "levenshtein": 45,
            "partial": 35,
            "token_sort": 30,
            "normalized": 15,
            "exact": 5,
        }
        score += strategy_weight.get(strategy, 50)

        # Penalty if match score is high (less certain)
        if match_score >= 95 and strategy != "none":
            score -= 20
        elif match_score >= 85 and strategy != "none":
            score -= 10

        # High spend amplifies concern
        if amount > 1_000_000:
            score += 15
        elif amount > 500_000:
            score += 10
        elif amount > 100_000:
            score += 5

        # Obfuscation = very high confidence it's intentional
        if obfuscation:
            score += 20

        # New vendor with no history
        if is_new_vendor:
            score += 10

        # Duplicate payment
        if duplicate:
            score += 10

        # Weekend payment
        if weekend:
            score += 5

        # More passes tried without match = more suspicious
        if strategy == "none":
            score += len(passes_tried) * 2

        return min(max(score, 0), 100)

    # ── Risk Scoring ──────────────────────────────────────────────────────────

    def risk_score(
        self,
        is_approved: bool,
        total_spend: float,
        duplicate_count: int,
        weekend_count: int,
        payment_count: int,
        tenure_days: int,
        confidence: int,
    ) -> Dict:
        score = 0
        reasons = []

        if not is_approved:
            score += 25
            reasons.append("Not on approved vendor list")

        if total_spend > 2_000_000:
            score += 40; reasons.append(f"Very high spend: R {total_spend:,.0f}")
        elif total_spend > 1_000_000:
            score += 30; reasons.append(f"High spend: R {total_spend:,.0f}")
        elif total_spend > 500_000:
            score += 20; reasons.append(f"Elevated spend: R {total_spend:,.0f}")
        elif total_spend > 100_000:
            score += 10; reasons.append(f"Notable spend: R {total_spend:,.0f}")

        if duplicate_count > 0:
            score += min(20, duplicate_count * 8)
            reasons.append(f"{duplicate_count} duplicate payment(s)")

        if weekend_count > 0:
            score += min(15, weekend_count * 5)
            reasons.append(f"{weekend_count} off-cycle payment(s)")

        # New vendor (< 90 days)
        if 0 < tenure_days < 90 and total_spend > 50_000:
            score += 20
            reasons.append(f"New vendor ({tenure_days}d) with high spend")
        elif tenure_days == 0 and payment_count > 0:
            score += 15
            reasons.append("Vendor with no date history")

        # High confidence amplifies risk
        score += int(confidence * 0.15)

        score = min(score, 100)
        level = "High" if score >= 65 else "Medium" if score >= 35 else "Low"

        return {
            "score": score,
            "level": level,
            "reasons": reasons[:5],
        }

    # ── Main Analysis ─────────────────────────────────────────────────────────

    def run_analysis(
        self,
        master_file: str,
        payments_file: str,
        threshold: int = 80,
        client_name: str = "Client",
        progress_callback=None,
    ) -> Dict:

        run_id = str(uuid.uuid4())[:8].upper()
        master_hash = self.hash_file(master_file)
        payments_hash = self.hash_file(payments_file)

        self.logger.info(f"[{run_id}] Analysis start — threshold={threshold}")

        master_df, payments_df = self.load_files(master_file, payments_file)
        master_vendors = master_df["vendor_name"].dropna().tolist()
        master_clean = [self.clean_name(v) for v in master_vendors]

        total = len(payments_df)
        if progress_callback:
            progress_callback(0.05, f"Loaded {total:,} payments, {len(master_vendors):,} vendors")

        # Precompute vendor stats for tenure/duplicate analysis
        vendor_stats: Dict[str, Dict] = defaultdict(lambda: {
            "payments": [], "total_spend": 0.0,
            "first_seen": None, "last_seen": None,
            "count": 0, "weekend_count": 0,
        })

        for _, row in payments_df.iterrows():
            pn = str(row["payee_name"])
            amt = float(row.get("amount", 0) or 0)
            dt_raw = str(row.get("payment_date", "") or "")
            vd = vendor_stats[pn]
            vd["payments"].append(amt)
            vd["total_spend"] += amt
            vd["count"] += 1
            if dt_raw:
                try:
                    dt = pd.to_datetime(dt_raw)
                    dt_s = dt.strftime("%Y-%m-%d")
                    if vd["first_seen"] is None or dt_s < vd["first_seen"]:
                        vd["first_seen"] = dt_s
                    if vd["last_seen"] is None or dt_s > vd["last_seen"]:
                        vd["last_seen"] = dt_s
                    if dt.dayofweek >= 5:
                        vd["weekend_count"] += 1
                except Exception:
                    pass

        # Identify duplicates (same payee, same amount on different rows)
        dup_keys: set = set()
        seen: Dict[Tuple, int] = {}
        for idx, row in payments_df.iterrows():
            key = (self.clean_name(str(row["payee_name"])), float(row.get("amount", 0) or 0))
            if key in seen:
                dup_keys.add(key)
            else:
                seen[key] = idx

        match_stats = {s: 0 for s in ["exact", "normalized", "token_sort", "partial",
                                       "levenshtein", "phonetic", "obfuscation", "none"]}
        results_list = []
        exceptions = []
        total_spend = 0.0
        exception_spend = 0.0

        for i, (_, row) in enumerate(payments_df.iterrows()):
            payee = str(row["payee_name"])
            amount = float(row.get("amount", 0) or 0)
            date_raw = str(row.get("payment_date", "") or "")
            total_spend += amount

            matched, score, strategy, passes = self.semantic_match_7pass(
                payee, master_vendors, master_clean, threshold
            )

            # Stats key
            stat_key = "obfuscation" if strategy.startswith("obfuscation") else strategy
            match_stats[stat_key] = match_stats.get(stat_key, 0) + 1

            is_exc = matched is None
            vd = vendor_stats[payee]

            # Tenure
            if vd["first_seen"] and vd["last_seen"]:
                try:
                    fd = datetime.strptime(vd["first_seen"], "%Y-%m-%d")
                    ld = datetime.strptime(vd["last_seen"], "%Y-%m-%d")
                    tenure_days = max(0, (ld - fd).days)
                except Exception:
                    tenure_days = 0
            else:
                tenure_days = 0

            # Obfuscation check
            is_obf, _, _ = self.detect_obfuscation(payee)

            # Duplicate
            clean_key = (self.clean_name(payee), amount)
            is_dup = clean_key in dup_keys

            # Weekend
            is_weekend = vd["weekend_count"] > 0

            # New vendor
            is_new = tenure_days < 90 and tenure_days >= 0

            # High spend
            is_high = vd["total_spend"] > 100_000

            controls = self.map_controls(
                is_approved=not is_exc,
                strategy=strategy,
                is_duplicate=is_dup,
                is_weekend=is_weekend,
                is_new_vendor=is_new,
                high_spend=is_high,
                obfuscation_detected=is_obf,
            )

            conf = self.confidence_score(
                strategy, score, passes, amount, is_new, is_obf, is_dup, is_weekend
            )

            risk = self.risk_score(
                is_approved=not is_exc,
                total_spend=vd["total_spend"],
                duplicate_count=int(is_dup),
                weekend_count=vd["weekend_count"],
                payment_count=vd["count"],
                tenure_days=tenure_days,
                confidence=conf,
            )

            explanation = self.build_explanation(
                payee, matched, score, strategy, amount,
                controls, is_new, is_weekend, is_dup
            )

            record = {
                "payee_name": payee,
                "matched_vendor": matched,
                "match_score": score,
                "match_strategy": strategy,
                "passes_tried": passes,
                "is_exception": is_exc,
                "amount": amount,
                "payment_date": date_raw,
                "control_ids": controls,
                "control_names": [CONTROL_TAXONOMY[c]["name"] for c in controls if c in CONTROL_TAXONOMY],
                "confidence_score": conf,
                "risk_score": risk["score"],
                "risk_level": risk["level"],
                "risk_reasons": risk["reasons"],
                "explanation": explanation,
                "first_seen": vd["first_seen"] or "",
                "last_seen": vd["last_seen"] or "",
                "payment_count": vd["count"],
                "tenure_days": tenure_days,
                "total_vendor_spend": vd["total_spend"],
                "is_duplicate": is_dup,
                "is_weekend": is_weekend,
                "is_obfuscation": is_obf,
            }

            results_list.append(record)
            if is_exc:
                exceptions.append(record)
                exception_spend += amount

            if progress_callback and i % max(1, total // 20) == 0:
                pct = 0.1 + (i / total) * 0.75
                progress_callback(pct, f"Processing {i+1:,}/{total:,}")

        # Sort exceptions by confidence desc, then risk score desc
        exceptions.sort(key=lambda x: (-x["confidence_score"], -x["risk_score"]))

        entropy = (exception_spend / total_spend * 100) if total_spend > 0 else 0

        # Vendor health analysis
        health = self._vendor_master_health(master_df)

        if progress_callback:
            progress_callback(0.9, "Finalising results")

        output = {
            "run_id": run_id,
            "client_name": client_name,
            "master_file_hash": master_hash,
            "payments_file_hash": payments_hash,
            "timestamp": datetime.now().isoformat(),
            "total_payments": len(results_list),
            "total_spend": total_spend,
            "exception_count": len(exceptions),
            "exception_spend": exception_spend,
            "entropy_score": entropy,
            "match_stats": match_stats,
            "results": results_list,
            "exceptions": exceptions,
            "duplicates": [k for k in dup_keys],
            "vendor_health": health,
            "threshold": threshold,
        }

        self.logger.info(
            f"[{run_id}] Complete — {len(exceptions)} exceptions, entropy={entropy:.1f}%"
        )
        return output

    def _vendor_master_health(self, master_df: pd.DataFrame) -> Dict:
        names = master_df["vendor_name"].dropna()
        total = len(names)
        clean_names = [self.clean_name(n) for n in names]

        # Duplicates
        from collections import Counter
        counts = Counter(clean_names)
        dupes = sum(1 for v in counts.values() if v > 1)

        # Blanks
        blanks = master_df["vendor_name"].isna().sum() + (master_df["vendor_name"] == "").sum()

        # Short names (possible junk)
        short = sum(1 for n in clean_names if 0 < len(n) < 3)

        health_score = 100
        if total > 0:
            health_score -= int((dupes / total) * 40)
            health_score -= int((blanks / total) * 30)
            health_score -= int((short / total) * 20)
        health_score = max(0, health_score)

        return {
            "total_vendors": total,
            "duplicate_records": dupes,
            "blank_names": int(blanks),
            "short_names": short,
            "health_score": health_score,
            "health_label": "Good" if health_score >= 80 else "Fair" if health_score >= 60 else "Poor",
        }

    # ── Export ────────────────────────────────────────────────────────────────

    def export_json(self, results: Dict, filepath: str):
        """Export full results as structured JSON."""
        export = {
            "meta": {
                "run_id": results["run_id"],
                "timestamp": results["timestamp"],
                "client": results["client_name"],
                "threshold": results["threshold"],
            },
            "summary": {
                "total_payments": results["total_payments"],
                "total_spend": results["total_spend"],
                "exception_count": results["exception_count"],
                "exception_spend": results["exception_spend"],
                "entropy_score": results["entropy_score"],
            },
            "exceptions": [
                {
                    "payee_name": e["payee_name"],
                    "amount": e["amount"],
                    "payment_date": e["payment_date"],
                    "control_ids": e["control_ids"],
                    "control_names": e["control_names"],
                    "confidence_score": e["confidence_score"],
                    "risk_level": e["risk_level"],
                    "risk_score": e["risk_score"],
                    "match_strategy": e["match_strategy"],
                    "match_score": e["match_score"],
                    "explanation": e["explanation"],
                    "risk_reasons": e["risk_reasons"],
                }
                for e in results["exceptions"]
            ],
            "match_distribution": results["match_stats"],
            "vendor_health": results["vendor_health"],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=2, ensure_ascii=False)
        self.logger.info(f"JSON exported: {filepath}")

    def export_csv(self, results: Dict, filepath: str):
        """Export flat CSV suitable for audit management systems."""
        rows = []
        for e in results["exceptions"]:
            rows.append({
                "run_id": results["run_id"],
                "payee_name": e["payee_name"],
                "amount": e["amount"],
                "payment_date": e["payment_date"],
                "controls": ", ".join(e["control_ids"]),
                "control_names": " | ".join(e["control_names"]),
                "confidence_score": e["confidence_score"],
                "risk_level": e["risk_level"],
                "risk_score": e["risk_score"],
                "flag_type": e["match_strategy"],
                "match_score": e["match_score"],
                "explanation": e["explanation"],
                "risk_reasons": " | ".join(e["risk_reasons"]),
                "first_seen": e["first_seen"],
                "last_seen": e["last_seen"],
                "payment_count": e["payment_count"],
                "tenure_days": e["tenure_days"],
                "total_vendor_spend": e["total_vendor_spend"],
            })
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False)
        self.logger.info(f"CSV exported: {filepath}")
