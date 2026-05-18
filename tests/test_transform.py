"""
Unit tests for transform.py

Run with:  pytest tests/
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from transform import transform_records, _validate, _normalize


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_RECORD = {
    "SpatialDim": "RWA",
    "SpatialDimValueCode": "Rwanda",
    "TimeDim": "2020",
    "Dim1": "BTSX",
    "NumericValue": "1234.5",
    "Low": "1000.0",
    "High": "1500.0",
    "ParentLocation": "Africa",
}


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

def test_valid_record_passes():
    assert _validate(VALID_RECORD) is None


def test_missing_spatial_dim_is_rejected():
    bad = {**VALID_RECORD, "SpatialDim": None}
    assert "missing SpatialDim" in _validate(bad)


def test_missing_time_dim_is_rejected():
    bad = {**VALID_RECORD, "TimeDim": ""}
    assert "missing TimeDim" in _validate(bad)


def test_non_integer_year_is_rejected():
    bad = {**VALID_RECORD, "TimeDim": "twenty-twenty"}
    assert "non-integer" in _validate(bad)


def test_out_of_range_year_is_rejected():
    bad = {**VALID_RECORD, "TimeDim": "1800"}
    reason = _validate(bad)
    assert reason is not None and "year" in reason


def test_non_numeric_value_is_rejected():
    bad = {**VALID_RECORD, "NumericValue": "lots"}
    assert "non-numeric" in _validate(bad)


def test_null_numeric_value_is_allowed():
    """Suppressed values (None) are valid — we store them as NULL."""
    record = {**VALID_RECORD, "NumericValue": None}
    assert _validate(record) is None


def test_two_char_country_code_is_rejected():
    bad = {**VALID_RECORD, "SpatialDim": "RW"}
    assert _validate(bad) is not None


# ---------------------------------------------------------------------------
# Normalisation tests
# ---------------------------------------------------------------------------

def test_normalize_maps_fields_correctly():
    result = _normalize(VALID_RECORD, "MALARIA_CASES")
    assert result["indicator_code"] == "MALARIA_CASES"
    assert result["country_code"] == "RWA"
    assert result["year"] == 2020
    assert result["value"] == pytest.approx(1234.5)
    assert result["low_value"] == pytest.approx(1000.0)
    assert result["high_value"] == pytest.approx(1500.0)
    assert result["sex"] == "BTSX"


def test_normalize_country_code_uppercased():
    record = {**VALID_RECORD, "SpatialDim": "rwa"}
    result = _normalize(record, "MALARIA_CASES")
    assert result["country_code"] == "RWA"


def test_normalize_unknown_sex_defaults_to_btsx():
    record = {**VALID_RECORD, "Dim1": "UNKNOWN_CODE"}
    result = _normalize(record, "MALARIA_CASES")
    assert result["sex"] == "BTSX"


# ---------------------------------------------------------------------------
# Integration-style tests on transform_records()
# ---------------------------------------------------------------------------

def test_transform_drops_invalid_and_keeps_valid():
    records = [
        VALID_RECORD,
        {**VALID_RECORD, "SpatialDim": None},   # invalid
        {**VALID_RECORD, "TimeDim": "abc"},      # invalid
        {**VALID_RECORD, "country_code": "KEN"}, # valid (extra key ignored)
    ]
    result = transform_records(records, "MALARIA_CASES")
    # 2 valid records (first and last)
    assert len(result) == 2


def test_transform_empty_input():
    result = transform_records([], "MALARIA_CASES")
    assert result == []
