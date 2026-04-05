import pytest
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import PayRealityEngine, DataValidationError


class TestEngineInit:
    """Test engine initialization"""

    def test_engine_creates(self):
        engine = PayRealityEngine()
        assert engine is not None

    def test_engine_has_db_path(self):
        engine = PayRealityEngine()
        assert engine.db_path is not None
        assert "PayReality_Data" in engine.db_path


class TestNameCleaning:
    """Test clean_name function"""

    def test_clean_basic(self):
        engine = PayRealityEngine()
        result = engine.clean_name("Microsoft (Pty) Ltd")
        assert result == "microsoft"

    def test_clean_multiple_suffixes(self):
        engine = PayRealityEngine()
        result = engine.clean_name("Acme Corporation Limited")
        assert result == "acme"

    def test_clean_handles_empty(self):
        engine = PayRealityEngine()
        result = engine.clean_name("")
        assert result == ""

    def test_clean_handles_none(self):
        engine = PayRealityEngine()
        result = engine.clean_name(None)
        assert result == ""


class TestPhoneticKey:
    """Test phonetic_key function"""

    def test_phonetic_returns_string(self):
        engine = PayRealityEngine()
        result = engine.phonetic_key("microsoft")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_phonetic_similar_sounds(self):
        engine = PayRealityEngine()
        key1 = engine.phonetic_key("smith")
        key2 = engine.phonetic_key("smyth")
        assert key1 == key2 or key1 == key2  # Should be similar


class TestObfuscationDetection:
    """Test detect_obfuscation function"""

    def test_detect_dot_spacing(self):
        engine = PayRealityEngine()
        detected, cleaned, obf_type = engine.detect_obfuscation("M.i.c.r.o.s.o.f.t")
        assert detected is True
        assert obf_type == "dot_spacing"

    def test_detect_leetspeak(self):
        engine = PayRealityEngine()
        detected, cleaned, obf_type = engine.detect_obfuscation("M1cr0s0ft")
        assert detected is True
        assert obf_type == "leetspeak"

    def test_single_leet_not_detected(self):
        engine = PayRealityEngine()
        detected, cleaned, obf_type = engine.detect_obfuscation("Micr0soft")
        assert detected is False

    def test_normal_name_not_detected(self):
        engine = PayRealityEngine()
        detected, cleaned, obf_type = engine.detect_obfuscation("Microsoft")
        assert detected is False


class TestControlMapping:
    """Test map_controls function"""

    def test_avc_for_unapproved(self):
        engine = PayRealityEngine()
        controls = engine.map_controls(
            is_approved=False,
            strategy="none",
            is_duplicate=False,
            is_weekend=False,
            is_new_vendor=False,
            high_spend=False,
            obfuscation_detected=False
        )
        assert "AVC" in controls

    def test_approved_no_controls(self):
        engine = PayRealityEngine()
        controls = engine.map_controls(
            is_approved=True,
            strategy="exact",
            is_duplicate=False,
            is_weekend=False,
            is_new_vendor=False,
            high_spend=False,
            obfuscation_detected=False
        )
        assert controls == []

    def test_obc_for_obfuscation(self):
        engine = PayRealityEngine()
        controls = engine.map_controls(
            is_approved=True,
            strategy="obfuscation_leetspeak",
            is_duplicate=False,
            is_weekend=False,
            is_new_vendor=False,
            high_spend=False,
            obfuscation_detected=True
        )
        assert "OBC" in controls

    def test_vdc_for_duplicate(self):
        engine = PayRealityEngine()
        controls = engine.map_controls(
            is_approved=True,
            strategy="exact",
            is_duplicate=True,
            is_weekend=False,
            is_new_vendor=False,
            high_spend=False,
            obfuscation_detected=False
        )
        assert "VDC" in controls

    def test_pac_for_weekend(self):
        engine = PayRealityEngine()
        controls = engine.map_controls(
            is_approved=True,
            strategy="exact",
            is_duplicate=False,
            is_weekend=True,
            is_new_vendor=False,
            high_spend=False,
            obfuscation_detected=False
        )
        assert "PAC" in controls


class TestRiskScoring:
    """Test risk_score function"""

    def test_high_risk_large_amount(self):
        engine = PayRealityEngine()
        risk = engine.risk_score(
            is_approved=False,
            total_spend=1000000,
            duplicate_count=0,
            weekend_count=0,
            payment_count=1,
            tenure_days=0,
            confidence=95
        )
        assert risk["level"] == "High"
        assert risk["score"] >= 65

    def test_low_risk_small_amount(self):
        engine = PayRealityEngine()
        risk = engine.risk_score(
            is_approved=True,
            total_spend=5000,
            duplicate_count=0,
            weekend_count=0,
            payment_count=10,
            tenure_days=365,
            confidence=70
        )
        assert risk["level"] == "Low"
        assert risk["score"] < 35

    def test_risk_has_reasons(self):
        engine = PayRealityEngine()
        risk = engine.risk_score(
            is_approved=False,
            total_spend=100000,
            duplicate_count=0,
            weekend_count=0,
            payment_count=1,
            tenure_days=0,
            confidence=85
        )
        assert "reasons" in risk
        assert len(risk["reasons"]) > 0


class TestFileHashing:
    """Test hash_file static method"""

    def test_hash_returns_64_chars(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("test data")
        
        hash_value = PayRealityEngine.hash_file(str(test_file))
        assert len(hash_value) == 64
        assert all(c in '0123456789abcdef' for c in hash_value)

    def test_same_file_same_hash(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("test data")
        
        hash1 = PayRealityEngine.hash_file(str(test_file))
        hash2 = PayRealityEngine.hash_file(str(test_file))
        assert hash1 == hash2


class TestExplainability:
    """Test build_explanation function"""

    def test_phonetic_explanation(self):
        engine = PayRealityEngine()
        explanation = engine.build_explanation(
            payee="Micosoft",
            matched_vendor="Microsoft",
            score=94,
            strategy="phonetic",
            amount=50000,
            controls=[],
            is_new_vendor=False,
            weekend=False,
            duplicate=False
        )
        assert "phonetic" in explanation.lower()
        assert "micosoft" in explanation.lower()
        assert "microsoft" in explanation.lower()

    def test_no_match_explanation(self):
        engine = PayRealityEngine()
        explanation = engine.build_explanation(
            payee="Unknown Corp",
            matched_vendor=None,
            score=0,
            strategy="none",
            amount=10000,
            controls=["AVC"],
            is_new_vendor=True,
            weekend=False,
            duplicate=False
        )
        assert "not be matched" in explanation.lower() or "approved" in explanation.lower()


class TestDatabase:
    """Test database operations"""

    def test_save_and_load_email_config(self):
        engine = PayRealityEngine()
        
        # Save config
        engine.save_email_config(
            smtp="smtp.test.com",
            port=587,
            user="test@test.com",
            password="secret123",
            recipients="audit@test.com"
        )
        
        # Load config
        cfg = engine.load_email_config()
        
        assert cfg is not None
        assert cfg["smtp"] == "smtp.test.com"
        assert cfg["port"] == 587
        assert cfg["user"] == "test@test.com"
        # Password should be encrypted then decrypted
        assert cfg["password"] == "secret123"

    def test_get_history_empty(self):
        engine = PayRealityEngine()
        history = engine.get_history()
        assert isinstance(history, list)