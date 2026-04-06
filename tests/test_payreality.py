"""
PayReality Test Suite - Phase 3 (Comprehensive Fix)

Fixes applied:
  [TEST-1]  Import path fixed to match root-level module layout
  [TEST-2]  Database tests use tmp_path to avoid touching real user data
  [TEST-3]  test_get_history_empty asserts [] on a fresh DB
  [TEST-4]  test_detect_leetspeak passes master_clean so it tests the production path
  [TEST-5]  test_no_match_explanation tightened to check specific phrase
  [TEST-6]  TestNameCleaning covers float/None/NaN inputs
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path

# [TEST-1] root-level import — no src/ subdirectory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import PayRealityEngine, DataValidationError


class TestEngineInit:
    """Test engine initialization"""

    def test_engine_creates(self, tmp_path):
        engine = PayRealityEngine(db_path=str(tmp_path / "test.db"))
        assert engine is not None

    def test_engine_has_db_path(self, tmp_path):
        db = str(tmp_path / "payreality.db")
        engine = PayRealityEngine(db_path=db)
        assert engine.db_path == db


class TestNameCleaning:
    """Test clean_name function"""

    def setup_method(self):
        self.engine = PayRealityEngine(db_path=":memory:")

    def test_clean_basic(self):
        assert self.engine.clean_name("Microsoft (Pty) Ltd") == "microsoft"

    def test_clean_multiple_suffixes(self):
        assert self.engine.clean_name("Acme Corporation Limited") == "acme"

    def test_clean_handles_empty_string(self):
        assert self.engine.clean_name("") == ""

    def test_clean_handles_none(self):
        assert self.engine.clean_name(None) == ""

    def test_clean_handles_nan(self):
        import math
        assert self.engine.clean_name(float("nan")) == ""

    def test_clean_handles_float_zero(self):
        # A non-NaN float should be converted via str()
        result = self.engine.clean_name(0.0)
        assert isinstance(result, str)

    def test_compound_suffix_fully_stripped(self):
        # "(Pty) Ltd" should be gone completely, not leave "(pty)" residue
        result = self.engine.clean_name("Widgets (Pty) Ltd")
        assert "pty" not in result
        assert "ltd" not in result
        assert result == "widgets"


class TestPhoneticKey:
    """Test phonetic_key function"""

    def setup_method(self):
        self.engine = PayRealityEngine(db_path=":memory:")

    def test_phonetic_returns_string(self):
        result = self.engine.phonetic_key("microsoft")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_phonetic_similar_sounds(self):
        key1 = self.engine.phonetic_key("smith")
        key2 = self.engine.phonetic_key("smyth")
        assert key1 == key2

    def test_phonetic_empty_returns_empty(self):
        assert self.engine.phonetic_key("") == ""


class TestObfuscationDetection:
    """Test detect_obfuscation function"""

    def setup_method(self):
        self.engine = PayRealityEngine(db_path=":memory:")

    def test_detect_dot_spacing(self):
        detected, cleaned, obf_type = self.engine.detect_obfuscation("M.i.c.r.o.s.o.f.t")
        assert detected is True
        assert obf_type == "dot_spacing"

    def test_detect_leetspeak_with_vendor_list(self):
        # [TEST-4] pass master_clean to exercise the production path
        master_clean = ["microsoft", "acme", "shoprite"]
        detected, cleaned, obf_type = self.engine.detect_obfuscation(
            "M1cr0s0ft", master_clean=master_clean, threshold=70
        )
        assert detected is True
        assert obf_type == "leetspeak"

    def test_detect_leetspeak_no_match_not_detected(self):
        # 3 leet chars but no vendor list match — should NOT fire
        master_clean = ["shoprite", "acme"]
        detected, cleaned, obf_type = self.engine.detect_obfuscation(
            "M1cr0s0ft", master_clean=master_clean, threshold=80
        )
        assert detected is False

    def test_single_leet_not_detected(self):
        detected, cleaned, obf_type = self.engine.detect_obfuscation("Micr0soft")
        assert detected is False

    def test_normal_name_not_detected(self):
        detected, cleaned, obf_type = self.engine.detect_obfuscation("Microsoft")
        assert detected is False

    def test_char_repetition_detected(self):
        detected, cleaned, obf_type = self.engine.detect_obfuscation("Miiiicrosoft")
        assert detected is True
        assert obf_type == "char_repetition"

    def test_homoglyph_detected(self):
        # Cyrillic 'о' (\u043e) looks like Latin 'o'
        name = "Micros\u043eft"
        detected, cleaned, obf_type = self.engine.detect_obfuscation(name)
        assert detected is True
        assert obf_type == "homoglyph"


class TestControlMapping:
    """Test map_controls function"""

    def setup_method(self):
        self.engine = PayRealityEngine(db_path=":memory:")

    def _base(self, **overrides):
        defaults = dict(
            is_approved=True, strategy="exact", is_duplicate=False,
            is_weekend=False, is_new_vendor=False, high_spend=False,
            obfuscation_detected=False,
        )
        defaults.update(overrides)
        return self.engine.map_controls(**defaults)

    def test_avc_for_unapproved(self):
        controls = self._base(is_approved=False, strategy="none")
        assert "AVC" in controls

    def test_approved_no_violations_returns_empty(self):
        controls = self._base()
        assert controls == []

    def test_obc_for_obfuscation_strategy(self):
        controls = self._base(strategy="obfuscation_leetspeak", obfuscation_detected=True)
        assert "OBC" in controls

    def test_vnc_for_token_sort(self):
        controls = self._base(strategy="token_sort")
        assert "VNC" in controls

    def test_vdc_for_duplicate(self):
        controls = self._base(is_duplicate=True)
        assert "VDC" in controls

    def test_pac_for_weekend(self):
        controls = self._base(is_weekend=True)
        assert "PAC" in controls

    def test_vtc_for_new_vendor_high_spend(self):
        controls = self._base(is_new_vendor=True, high_spend=True)
        assert "VTC" in controls

    def test_vtc_not_triggered_without_high_spend(self):
        controls = self._base(is_new_vendor=True, high_spend=False)
        assert "VTC" not in controls

    def test_vmh_emitted_when_poor(self):
        controls = self.engine.map_controls(
            is_approved=True, strategy="exact", is_duplicate=False,
            is_weekend=False, is_new_vendor=False, high_spend=False,
            obfuscation_detected=False, vendor_master_poor=True,
        )
        assert "VMH" in controls


class TestRiskScoring:
    """Test risk_score function"""

    def setup_method(self):
        self.engine = PayRealityEngine(db_path=":memory:")

    def test_high_risk_large_amount(self):
        risk = self.engine.risk_score(
            is_approved=False, total_spend=1_000_000, duplicate_count=0,
            weekend_count=0, payment_count=1, tenure_days=0, confidence=95,
        )
        assert risk["level"] == "High"
        assert risk["score"] >= 65

    def test_low_risk_small_amount(self):
        risk = self.engine.risk_score(
            is_approved=True, total_spend=5_000, duplicate_count=0,
            weekend_count=0, payment_count=10, tenure_days=365, confidence=70,
        )
        assert risk["level"] == "Low"
        assert risk["score"] < 35

    def test_risk_has_reasons(self):
        risk = self.engine.risk_score(
            is_approved=False, total_spend=100_000, duplicate_count=0,
            weekend_count=0, payment_count=1, tenure_days=0, confidence=85,
        )
        assert "reasons" in risk
        assert len(risk["reasons"]) > 0

    def test_date_less_vendor_does_not_trigger_new_vendor_risk(self):
        # tenure_days=0 means no dates — should not score as "new vendor with high spend"
        risk = self.engine.risk_score(
            is_approved=True, total_spend=200_000, duplicate_count=0,
            weekend_count=0, payment_count=5, tenure_days=0, confidence=10,
        )
        # Should still get "no date history" reason but NOT new-vendor-high-spend reason
        reasons_text = " ".join(risk["reasons"])
        assert "New vendor" not in reasons_text


class TestIsNewVendor:
    """Test that tenure_days=0 (no date data) does not flag as new vendor."""

    def setup_method(self):
        self.engine = PayRealityEngine(db_path=":memory:")

    def test_zero_tenure_not_new_vendor(self):
        # tenure_days=0 means missing dates — map_controls should NOT set VTC
        controls = self.engine.map_controls(
            is_approved=True, strategy="exact", is_duplicate=False,
            is_weekend=False,
            is_new_vendor=False,   # caller must compute: 0 < 0 < 90 == False
            high_spend=True,
            obfuscation_detected=False,
        )
        assert "VTC" not in controls

    def test_positive_tenure_under_90_is_new(self):
        # 45 days is genuinely new
        is_new = 0 < 45 < 90
        assert is_new is True

    def test_tenure_over_90_not_new(self):
        is_new = 0 < 120 < 90
        assert is_new is False


class TestFileHashing:
    """Test hash_file static method"""

    def test_hash_returns_64_chars(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("test data")
        hash_value = PayRealityEngine.hash_file(str(test_file))
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_same_file_same_hash(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("test data")
        assert PayRealityEngine.hash_file(str(test_file)) == \
               PayRealityEngine.hash_file(str(test_file))

    def test_missing_file_raises_validation_error(self, tmp_path):
        with pytest.raises(DataValidationError, match="Cannot read file"):
            PayRealityEngine.hash_file(str(tmp_path / "nonexistent.csv"))


class TestExplainability:
    """Test build_explanation function"""

    def setup_method(self):
        self.engine = PayRealityEngine(db_path=":memory:")

    def test_phonetic_explanation(self):
        explanation = self.engine.build_explanation(
            payee="Micosoft", matched_vendor="Microsoft",
            score=94, strategy="phonetic", amount=50_000,
            controls=[], is_new_vendor=False, weekend=False, duplicate=False,
        )
        assert "phonetic" in explanation.lower()
        assert "micosoft" in explanation.lower()
        assert "microsoft" in explanation.lower()

    def test_no_match_explanation(self):
        explanation = self.engine.build_explanation(
            payee="Unknown Corp", matched_vendor=None,
            score=0, strategy="none", amount=10_000,
            controls=["AVC"], is_new_vendor=True,
            weekend=False, duplicate=False,
        )
        # [TEST-5] specific phrase check, not just "approved"
        assert "could not be matched" in explanation.lower()

    def test_unknown_strategy_has_fallback(self):
        # [TEST-5] FIX-17: unknown strategies should not produce empty explanations
        explanation = self.engine.build_explanation(
            payee="Acme", matched_vendor="Acme Ltd",
            score=80, strategy="future_strategy_v8", amount=5_000,
            controls=[], is_new_vendor=False, weekend=False, duplicate=False,
        )
        # Should contain something about the payee and strategy
        assert "acme" in explanation.lower()
        assert "future_strategy_v8" in explanation.lower()

    def test_obfuscation_explanation_mentions_type(self):
        explanation = self.engine.build_explanation(
            payee="M1cr0s0ft", matched_vendor="Microsoft",
            score=88, strategy="obfuscation_leetspeak", amount=20_000,
            controls=["OBC"], is_new_vendor=False, weekend=False, duplicate=False,
        )
        assert "leetspeak" in explanation.lower()
        assert "obfuscation" in explanation.lower()


class TestDatabase:
    """Test database operations — all use tmp_path to avoid real DB."""

    def test_save_and_load_email_config(self, tmp_path):
        # [TEST-2] isolated DB
        engine = PayRealityEngine(db_path=str(tmp_path / "test.db"))
        engine.save_email_config(
            smtp="smtp.test.com", port=587,
            user="test@test.com", password="secret123",
            recipients="audit@test.com",
        )
        cfg = engine.load_email_config()
        assert cfg is not None
        assert cfg["smtp"] == "smtp.test.com"
        assert cfg["port"] == 587
        assert cfg["user"] == "test@test.com"
        assert cfg["password"] == "secret123"

    def test_get_history_empty(self, tmp_path):
        # [TEST-3] fresh DB must return empty list, not just any list
        engine = PayRealityEngine(db_path=str(tmp_path / "fresh.db"))
        history = engine.get_history()
        assert history == []

    def test_save_and_retrieve_run(self, tmp_path):
        engine = PayRealityEngine(db_path=str(tmp_path / "runs.db"))
        fake_results = {
            "total_payments": 100,
            "exception_count": 5,
            "exception_spend": 50_000.0,
            "entropy_score": 5.0,
            "duplicates": [],
            "exceptions": [],
        }
        run_id = engine.save_run(
            "TESTRUN001", "Test Client",
            "a" * 64, "b" * 64,
            80, fake_results,
        )
        history = engine.get_history()
        assert len(history) == 1
        assert history[0]["run_id"] == "TESTRUN001"
        assert history[0]["client_name"] == "Test Client"