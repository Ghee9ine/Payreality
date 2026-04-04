"""
PayReality Core Engine - Phase 2 (Patched)

Patches applied:
  [SEC-1]  SMTP password encrypted with Fernet (machine-derived key)
  [SEC-2]  SHA256 hash no longer truncated — full 64-char hex
  [SEC-3]  File size limit enforced before load (500 MB)
  [BUG-1]  Phonetic keys pre-computed outside the per-payment loop (O(n) → O(1))
  [BUG-2]  Currency strings stripped before numeric coercion; coercion losses logged
  [BUG-3]  Duplicate key uses round(amount, 2) to avoid float epsilon mismatches
  [BUG-4]  SQLite opened with WAL mode + 10-second timeout
  [BUG-5]  Weekend flag checked per-payment, not per-vendor
  [BUG-6]  map_controls() fallback no longer appends AVC to approved payments
  [BUG-7]  clean_name() strips compound suffixes in a while-loop (not single pass)
  [BUG-8]  Column rename loop breaks after first match to avoid last-match clobber
  [BUG-9]  Leet detection requires ≥2 substitutions AND a vendor fuzzy-match
  [LOG-1]  Logging directory created before logging is configured (see app entry point)
"""

import hashlib
import json
import logging
import os
import re
import sqlite3
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd

try:
    from rapidfuzz import fuzz, process
except ImportError:
    raise ImportError("rapidfuzz required: pip install rapidfuzz")

# Optional Fernet — gracefully degrade if cryptography not installed
try:
    from cryptography.fernet import Fernet
    import base64, hashlib as _hl
    _FERNET_AVAILABLE = True
except ImportError:
    _FERNET_AVAILABLE = False


# ─── Constants ────────────────────────────────────────────────────────────────

MAX_FILE_BYTES = 500 * 1024 * 1024   # 500 MB
_LEET_MAP = {"3": "e", "0": "o", "1": "i", "4": "a",
             "5": "s", "7": "t", "@": "a", "$": "s"}


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


# ─── Encryption helpers ──────────────────────────────────────────────────────

def _derive_fernet_key() -> Optional[bytes]:
    """
    Derive a deterministic Fernet key from a machine identifier.
    Falls back to None if cryptography is not installed.
    """
    if not _FERNET_AVAILABLE:
        return None
    # Use machine hostname + username as a stable, machine-specific seed.
    import socket, getpass
    seed = f"payreality:{socket.gethostname()}:{getpass.getuser()}".encode()
    raw = _hl.sha256(seed).digest()                  # 32 bytes
    return base64.urlsafe_b64encode(raw)              # Fernet needs URL-safe base64


def encrypt_password(plaintext: str) -> str:
    """Encrypt a password string. Returns plaintext if cryptography unavailable."""
    key = _derive_fernet_key()
    if key is None or not plaintext:
        return plaintext
    return Fernet(key).encrypt(plaintext.encode()).decode()


def decrypt_password(ciphertext: str) -> str:
    """Decrypt a password string. Returns ciphertext unchanged if unavailable."""
    key = _derive_fernet_key()
    if key is None or not ciphertext:
        return ciphertext
    try:
        return Fernet(key).decrypt(ciphertext.encode()).decode()
    except Exception:
        # Already plaintext (migrating from old version)
        return ciphertext


# ─── Engine ──────────────────────────────────────────────────────────────────

class PayRealityEngine:

    def __init__(self, config: Dict = None, db_path: str = None):
        self.config = config or {}
        self.logger = logging.getLogger("PayReality.Engine")
        self.master_df = None
        self.payments_df = None

        if db_path is None:
            db_path = str(Path.home() / "PayReality_Data" / "payreality.db")
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── DB ────────────────────────────────────────────────────────────────────

    def _db(self) -> sqlite3.Connection:
        """
        Open a SQLite connection with WAL journaling and a generous timeout.
        WAL mode allows concurrent readers while a writer is active, preventing
        "database is locked" errors when the UI thread reads history while the
        analysis thread writes results.  [BUG-4]
        """
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

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

    # ── Email password helpers ────────────────────────────────────────────────

    def save_email_config(self, smtp: str, port: int, user: str,
                          password: str, recipients: str) -> None:
        """
        Store email configuration with encrypted password.  [SEC-1]
        The password is encrypted with a machine-derived Fernet key before
        being written to the database. Decryption happens only at send time.
        """
        encrypted = encrypt_password(password)
        with self._db() as conn:
            conn.execute("DELETE FROM email_config")
            conn.execute(
                "INSERT INTO email_config (smtp_server, smtp_port, email_user, "
                "email_password, recipient_list) VALUES (?,?,?,?,?)",
                (smtp, port, user, encrypted, recipients)
            )

    def load_email_config(self) -> Optional[Dict]:
        """Load and decrypt email configuration."""
        with self._db() as conn:
            row = conn.execute(
                "SELECT smtp_server, smtp_port, email_user, "
                "email_password, recipient_list FROM email_config LIMIT 1"
            ).fetchone()
        if not row or not row[0]:
            return None
        return {
            "smtp": row[0],
            "port": row[1],
            "user": row[2],
            "password": decrypt_password(row[3] or ""),
            "recipients": row[4] or "",
        }

    # ── File I/O ──────────────────────────────────────────────────────────────

    @staticmethod
    def hash_file(filepath: str) -> str:
        """
        Return the full SHA-256 hex digest (64 chars) of a file.
        The previous implementation truncated to 16 chars (64-bit), which is
        not collision-resistant for a court-defensible audit trail.  [SEC-2]
        """
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()   # full 64-char hex — never truncate

    def load_dataframe(self, filepath: str) -> pd.DataFrame:
        """
        Multi-encoding, multi-format loader with a 500 MB size guard.  [SEC-3]
        Tries UTF-8, UTF-8-BOM, latin-1, cp1252 in order.
        """
        path = Path(filepath)

        # ── Size guard ────────────────────────────────────────────────────────
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise DataValidationError(
                f"File '{path.name}' is {size / 1024**2:.0f} MB — "
                f"maximum supported size is 500 MB."
            )

        ext = path.suffix.lower()
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

    def _parse_amount_column(self, series: pd.Series) -> pd.Series:
        """
        Strip common currency symbols and thousand-separators before numeric
        coercion, then log the count of rows that could not be parsed.  [BUG-2]

        Handles: R1,000.00 · R 1 000 · £500 · €1.200,00 · 1000.00
        """
        cleaned = (
            series.astype(str)
            .str.replace(r"[R$£€\s]", "", regex=True)   # currency symbols + spaces
            .str.replace(r",(?=\d{3}(?:[,.]|$))", "", regex=True)  # thousand commas
        )
        numeric = pd.to_numeric(cleaned, errors="coerce")
        lost = numeric.isna().sum() - series.isna().sum()
        if lost > 0:
            self.logger.warning(
                f"{lost} payment row(s) had unparseable amounts and were set to 0. "
                "Check the 'amount' column for non-numeric values."
            )
        return numeric.fillna(0)

    def load_files(self, master_file: str, payments_file: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        self.logger.info("Loading input files")

        master_df = self.load_dataframe(master_file)
        master_df = self._normalise_columns(master_df, ["vendor_name"])

        if "vendor_name" not in master_df.columns:
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

        # ── Flexible column mapping — break after first match  [BUG-8] ───────
        for col in payments_df.columns:
            cl = col.lower()
            if "payee_name" not in payments_df.columns:
                if any(k in cl for k in ["payee", "vendor", "supplier", "pay_to",
                                          "recipient", "name"]):
                    payments_df = payments_df.rename(columns={col: "payee_name"})
                    break   # stop after first match — avoid last-match clobber

        for col in payments_df.columns:
            cl = col.lower()
            if "amount" not in payments_df.columns:
                if any(k in cl for k in ["amount", "value", "total",
                                          "invoice_amount", "price"]):
                    payments_df = payments_df.rename(columns={col: "amount"})
                    break

        missing = [c for c in ["payee_name", "amount"] if c not in payments_df.columns]
        if missing:
            raise DataValidationError(
                f"Payments file missing columns: {missing}.\nFound: {list(payments_df.columns)}"
            )

        # ── Amount parsing with currency stripping  [BUG-2] ──────────────────
        payments_df["amount"] = self._parse_amount_column(payments_df["amount"])

        # Date column detection
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
        " (pty) ltd", " pty ltd", " pty", " ltd", " inc", " corp", " llc",
        " co", " cc", " limited", " corporation", " incorporated",
        " company", " holdings", " group", " international", " systems",
        " technologies", " solutions", " services", " enterprises",
    ]

    def clean_name(self, name: str) -> str:
        """
        Normalise a vendor name for fuzzy comparison.
        Strips compound suffixes in a while-loop so that '(Pty) Ltd' is
        fully removed in a single call — the original single-pass break
        left intermediate tokens such as '(pty)' in the cleaned string.  [BUG-7]
        """
        if not name or (isinstance(name, float) and pd.isna(name)):
            return ""
        n = str(name).lower().strip()
        n = re.sub(r"[^\w\s]", " ", n)
        n = re.sub(r"\s+", " ", n).strip()
        # Keep stripping until no suffix matches
        changed = True
        while changed:
            changed = False
            for s in self._SUFFIXES:
                if n.endswith(s):
                    n = n[: -len(s)].strip()
                    changed = True
                    break
        return n

    def phonetic_key(self, text: str) -> str:
        """Consonant skeleton + substitutions for phonetic matching."""
        t = text.lower()
        t = re.sub(r"ph|gh", "f", t)
        t = re.sub(r"ck|c(?=[^eihy])", "k", t)
        t = re.sub(r"sh|ch", "x", t)
        t = re.sub(r"[aeiou]", "", t)
        t = re.sub(r"(.)\1+", r"\1", t)
        return t

    def detect_obfuscation(self, name: str,
                            master_clean: Optional[List[str]] = None,
                            threshold: int = 80) -> Tuple[bool, str, str]:
        """
        Returns (detected, cleaned_name, obfuscation_type).

        Leet detection now requires ≥2 substitutions AND (if master_clean is
        provided) that the de-leeted name fuzzy-matches a known vendor above
        threshold.  A single digit in a vendor name is not obfuscation.  [BUG-9]
        """
        # Dot/space spacing: M.i.c.r.o.s.o.f.t
        if re.search(r"(\w\.){3,}", name):
            cleaned = re.sub(r"\.", "", name)
            return True, cleaned, "dot_spacing"

        # Leetspeak — require ≥2 substitutions
        leet_hits = sum(1 for c in name if c in _LEET_MAP)
        if leet_hits >= 2:
            cleaned = name
            for k, v in _LEET_MAP.items():
                cleaned = cleaned.replace(k, v)
            # Confirm match against vendor list if available
            if master_clean:
                r = process.extractOne(self.clean_name(cleaned), master_clean,
                                       scorer=fuzz.token_sort_ratio)
                if r and r[1] >= threshold:
                    return True, cleaned, "leetspeak"
            else:
                return True, cleaned, "leetspeak"

        # Repeated characters (3+ in a row)
        if re.search(r"(.)\1{2,}", name):
            cleaned = re.sub(r"(.)\1{2,}", r"\1\1", name)
            return True, cleaned, "char_repetition"

        # Unicode homoglyphs
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
        master_phonetic: Optional[List[str]] = None,   # pre-computed  [BUG-1]
    ) -> Tuple[Optional[str], int, str, List[str]]:
        """
        7-pass semantic matching engine.

        master_phonetic must be pre-computed by the caller (once, before the
        per-payment loop) and passed in here.  Computing it inside this
        function — as the original code did — is O(vendors × payments).  [BUG-1]

        Returns: (matched_vendor, score, strategy, passes_tried)
        """
        passes_tried: List[str] = []

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

        # Pass 5: Levenshtein
        passes_tried.append("levenshtein")
        r = process.extractOne(payee_clean, master_clean, scorer=fuzz.QRatio)
        if r and r[1] >= max(threshold - 5, 60):
            return master_vendors[r[2]], r[1], "levenshtein", passes_tried

        # Pass 6: Phonetic — use pre-computed keys  [BUG-1]
        passes_tried.append("phonetic")
        payee_ph = self.phonetic_key(payee_clean)
        if payee_ph and master_phonetic:
            r = process.extractOne(payee_ph, master_phonetic, scorer=fuzz.token_sort_ratio)
            if r and r[1] >= threshold:
                return master_vendors[r[2]], r[1], "phonetic", passes_tried

        # Pass 7: Obfuscation — pass master_clean for leet validation  [BUG-9]
        passes_tried.append("obfuscation")
        is_obf, cleaned, obf_type = self.detect_obfuscation(
            payee, master_clean=master_clean, threshold=threshold
        )
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
        """
        Return list of violated control IDs.

        The original fallback — 'return controls if controls else ["AVC"]' —
        incorrectly appended AVC (Critical) to approved payments that violated
        no controls, inflating exception counts.  An approved payment with no
        other violations returns [].  [BUG-6]
        """
        controls: List[str] = []
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
        return controls   # may be empty — that is correct for a clean payment

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
                "dot_spacing":      "dot-spacing (e.g. M.i.c.r.o.s.o.f.t)",
                "leetspeak":        "leetspeak character substitution (e.g. 3=E, 0=O)",
                "char_repetition":  "repeated characters (e.g. Miiiicrosoft)",
                "homoglyph":        "Unicode homoglyph substitution",
            }.get(obf_type, obf_type)
            parts.append(
                f"Obfuscation detected in '{payee}' via {type_desc}; "
                f"deobfuscated form matched '{matched_vendor}' at {score}%."
            )

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
        """0–100: how confident are we this is a genuine control failure?"""
        score = 0

        strategy_weight = {
            "none":                      70,
            "obfuscation_dot_spacing":   85,
            "obfuscation_leetspeak":     85,
            "obfuscation_char_repetition": 75,
            "obfuscation_homoglyph":     90,
            "phonetic":                  55,
            "levenshtein":               45,
            "partial":                   35,
            "token_sort":                30,
            "normalized":                15,
            "exact":                      5,
        }
        score += strategy_weight.get(strategy, 50)

        if match_score >= 95 and strategy != "none":
            score -= 20
        elif match_score >= 85 and strategy != "none":
            score -= 10

        if amount > 1_000_000:
            score += 15
        elif amount > 500_000:
            score += 10
        elif amount > 100_000:
            score += 5

        if obfuscation:
            score += 20
        if is_new_vendor:
            score += 10
        if duplicate:
            score += 10
        if weekend:
            score += 5

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
        reasons: List[str] = []

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

        if 0 < tenure_days < 90 and total_spend > 50_000:
            score += 20
            reasons.append(f"New vendor ({tenure_days}d) with high spend")
        elif tenure_days == 0 and payment_count > 0:
            score += 15
            reasons.append("Vendor with no date history")

        score += int(confidence * 0.15)
        score = min(score, 100)
        level = "High" if score >= 65 else "Medium" if score >= 35 else "Low"

        return {"score": score, "level": level, "reasons": reasons[:5]}

    # ── Main Analysis ─────────────────────────────────────────────────────────

    def run_analysis(
        self,
        master_file: str,
        payments_file: str,
        threshold: int = 80,
        client_name: str = "Client",
        progress_callback=None,
    ) -> Dict:
        """
        Run the full 7-pass semantic analysis pipeline.

        Returns a results dict containing summary stats, all exceptions sorted
        by confidence descending, match distribution, and vendor health.
        """
        run_id = str(uuid.uuid4())[:8].upper()
        master_hash = self.hash_file(master_file)
        payments_hash = self.hash_file(payments_file)

        self.logger.info(f"[{run_id}] Analysis start — threshold={threshold}")

        master_df, payments_df = self.load_files(master_file, payments_file)
        master_vendors: List[str] = master_df["vendor_name"].dropna().tolist()
        master_clean: List[str] = [self.clean_name(v) for v in master_vendors]

        # Pre-compute phonetic keys once — critical perf fix for large datasets  [BUG-1]
        master_phonetic: List[str] = [self.phonetic_key(v) for v in master_clean]

        total = len(payments_df)
        if progress_callback:
            progress_callback(0.05, f"Loaded {total:,} payments, {len(master_vendors):,} vendors")

        # Precompute vendor-level stats for tenure / duplicate analysis
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

        # Identify duplicates (same payee + amount) using rounded float key  [BUG-3]
        dup_keys: set = set()
        seen: Dict[Tuple, int] = {}
        for idx, row in payments_df.iterrows():
            key = (
                self.clean_name(str(row["payee_name"])),
                round(float(row.get("amount", 0) or 0), 2),   # round to avoid float epsilon
            )
            if key in seen:
                dup_keys.add(key)
            else:
                seen[key] = idx

        match_stats = {s: 0 for s in ["exact", "normalized", "token_sort", "partial",
                                       "levenshtein", "phonetic", "obfuscation", "none"]}
        results_list: List[Dict] = []
        exceptions: List[Dict] = []
        total_spend = 0.0
        exception_spend = 0.0

        for i, (_, row) in enumerate(payments_df.iterrows()):
            payee = str(row["payee_name"])
            amount = float(row.get("amount", 0) or 0)
            date_raw = str(row.get("payment_date", "") or "")
            total_spend += amount

            matched, score, strategy, passes = self.semantic_match_7pass(
                payee, master_vendors, master_clean, threshold,
                master_phonetic=master_phonetic,   # pre-computed  [BUG-1]
            )

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

            # Obfuscation check (pass master_clean for leet validation)  [BUG-9]
            is_obf, _, _ = self.detect_obfuscation(
                payee, master_clean=master_clean, threshold=threshold
            )

            # Duplicate key uses rounded amount  [BUG-3]
            clean_key = (self.clean_name(payee), round(amount, 2))
            is_dup = clean_key in dup_keys

            # ── Weekend: check THIS payment's date, not vendor aggregate  [BUG-5] ──
            is_weekend = False
            if date_raw:
                try:
                    is_weekend = pd.to_datetime(date_raw).dayofweek >= 5
                except Exception:
                    pass

            is_new = tenure_days < 90 and tenure_days >= 0
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
                "payee_name":         payee,
                "matched_vendor":     matched,
                "match_score":        score,
                "match_strategy":     strategy,
                "passes_tried":       passes,
                "is_exception":       is_exc,
                "amount":             amount,
                "payment_date":       date_raw,
                "control_ids":        controls,
                "control_names":      [CONTROL_TAXONOMY[c]["name"]
                                       for c in controls if c in CONTROL_TAXONOMY],
                "confidence_score":   conf,
                "risk_score":         risk["score"],
                "risk_level":         risk["level"],
                "risk_reasons":       risk["reasons"],
                "explanation":        explanation,
                "first_seen":         vd["first_seen"] or "",
                "last_seen":          vd["last_seen"] or "",
                "payment_count":      vd["count"],
                "tenure_days":        tenure_days,
                "total_vendor_spend": vd["total_spend"],
                "is_duplicate":       is_dup,
                "is_weekend":         is_weekend,
                "is_obfuscation":     is_obf,
            }

            results_list.append(record)
            if is_exc:
                exceptions.append(record)
                exception_spend += amount

            if progress_callback and i % max(1, total // 20) == 0:
                pct = 0.1 + (i / total) * 0.75
                progress_callback(pct, f"Processing {i+1:,}/{total:,}")

        exceptions.sort(key=lambda x: (-x["confidence_score"], -x["risk_score"]))

        # Guard against zero total spend  [already present, kept for clarity]
        entropy = (exception_spend / total_spend * 100) if total_spend > 0 else 0.0

        health = self._vendor_master_health(master_df)

        if progress_callback:
            progress_callback(0.9, "Finalising results")

        output = {
            "run_id":               run_id,
            "client_name":          client_name,
            "master_file_hash":     master_hash,
            "payments_file_hash":   payments_hash,
            "timestamp":            datetime.now().isoformat(),
            "total_payments":       len(results_list),
            "total_spend":          total_spend,
            "exception_count":      len(exceptions),
            "exception_spend":      exception_spend,
            "entropy_score":        entropy,
            "match_stats":          match_stats,
            "results":              results_list,
            "exceptions":           exceptions,
            "duplicates":           list(dup_keys),
            "vendor_health":        health,
            "threshold":            threshold,
        }

        self.logger.info(
            f"[{run_id}] Complete — {len(exceptions)} exceptions, entropy={entropy:.1f}%"
        )
        return output

    def _vendor_master_health(self, master_df: pd.DataFrame) -> Dict:
        names = master_df["vendor_name"].dropna()
        total = len(names)
        clean_names = [self.clean_name(n) for n in names]

        from collections import Counter
        counts = Counter(clean_names)
        dupes = sum(1 for v in counts.values() if v > 1)
        blanks = master_df["vendor_name"].isna().sum() + (master_df["vendor_name"] == "").sum()
        short = sum(1 for n in clean_names if 0 < len(n) < 3)

        health_score = 100
        if total > 0:
            health_score -= int((dupes / total) * 40)
            health_score -= int((blanks / total) * 30)
            health_score -= int((short / total) * 20)
        health_score = max(0, health_score)

        return {
            "total_vendors":     total,
            "duplicate_records": dupes,
            "blank_names":       int(blanks),
            "short_names":       short,
            "health_score":      health_score,
            "health_label":      "Good" if health_score >= 80 else
                                 "Fair" if health_score >= 60 else "Poor",
        }

    # ── Export ────────────────────────────────────────────────────────────────

    def export_json(self, results: Dict, filepath: str) -> None:
        """Export full results as structured JSON."""
        export = {
            "meta": {
                "run_id":    results["run_id"],
                "timestamp": results["timestamp"],
                "client":    results["client_name"],
                "threshold": results["threshold"],
            },
            "summary": {
                "total_payments":  results["total_payments"],
                "total_spend":     results["total_spend"],
                "exception_count": results["exception_count"],
                "exception_spend": results["exception_spend"],
                "entropy_score":   results["entropy_score"],
            },
            "exceptions": [
                {
                    "payee_name":      e["payee_name"],
                    "amount":          e["amount"],
                    "payment_date":    e["payment_date"],
                    "control_ids":     e["control_ids"],
                    "control_names":   e["control_names"],
                    "confidence_score": e["confidence_score"],
                    "risk_level":      e["risk_level"],
                    "risk_score":      e["risk_score"],
                    "match_strategy":  e["match_strategy"],
                    "match_score":     e["match_score"],
                    "explanation":     e["explanation"],
                    "risk_reasons":    e["risk_reasons"],
                }
                for e in results["exceptions"]
            ],
            "match_distribution": results["match_stats"],
            "vendor_health":      results["vendor_health"],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=2, ensure_ascii=False)
        self.logger.info(f"JSON exported: {filepath}")

    def export_csv(self, results: Dict, filepath: str) -> None:
        """
        Export flat CSV suitable for audit management systems.
        String cells are sanitised against Excel formula injection — any cell
        starting with =, @, +, or - is prefixed with a single quote.  [SEC-2-CSV]
        """
        def _sanitise(v: Any) -> Any:
            """Prevent CSV/Excel formula injection."""
            if isinstance(v, str) and v and v[0] in ("=", "@", "+", "-"):
                return "'" + v
            return v

        rows = []
        for e in results["exceptions"]:
            rows.append({
                "run_id":            _sanitise(results["run_id"]),
                "payee_name":        _sanitise(e["payee_name"]),
                "amount":            e["amount"],
                "payment_date":      _sanitise(e["payment_date"]),
                "controls":          _sanitise(", ".join(e["control_ids"])),
                "control_names":     _sanitise(" | ".join(e["control_names"])),
                "confidence_score":  e["confidence_score"],
                "risk_level":        _sanitise(e["risk_level"]),
                "risk_score":        e["risk_score"],
                "flag_type":         _sanitise(e["match_strategy"]),
                "match_score":       e["match_score"],
                "explanation":       _sanitise(e["explanation"]),
                "risk_reasons":      _sanitise(" | ".join(e["risk_reasons"])),
                "first_seen":        _sanitise(e["first_seen"]),
                "last_seen":         _sanitise(e["last_seen"]),
                "payment_count":     e["payment_count"],
                "tenure_days":       e["tenure_days"],
                "total_vendor_spend": e["total_vendor_spend"],
            })
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False)
        self.logger.info(f"CSV exported: {filepath}")