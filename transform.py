import logging
from typing import Optional

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ["SpatialDim", "TimeDim"]
VALID_SEX_CODES = {"BTSX", "MLE", "FMLE"}
YEAR_MIN = 1900
YEAR_MAX = 2100


def transform_records(raw: list[dict], indicator_code: str) -> list[dict]:
    """
    Validate and normalize raw API records into a flat structure
    ready for loading into PostgreSQL.
    Invalid rows are logged and dropped rather than silently skipped.
    """
    valid: list[dict] = []
    dropped = 0

    for i, record in enumerate(raw):
        reason = _validate(record)
        if reason:
            logger.warning(
                f"[{indicator_code}] Row {i} dropped ({reason}) — "
                f"country={record.get('SpatialDim')} year={record.get('TimeDim')}"
            )
            dropped += 1
            continue
        valid.append(_normalize(record, indicator_code))

    logger.info(
        f"[{indicator_code}] Transform: {len(valid)} valid, {dropped} dropped "
        f"({dropped / max(len(raw), 1) * 100:.1f}% drop rate)"
    )
    return valid


def _validate(record: dict) -> Optional[str]:
    """Return a reason string if invalid, else None."""
    for field in REQUIRED_FIELDS:
        if not record.get(field):
            return f"missing {field}"

    try:
        year = int(record["TimeDim"])
    except (ValueError, TypeError):
        return f"non-integer TimeDim='{record['TimeDim']}'"

    if not (YEAR_MIN <= year <= YEAR_MAX):
        return f"year {year} outside expected range [{YEAR_MIN}, {YEAR_MAX}]"

    code = record["SpatialDim"]
    if not (isinstance(code, str) and len(code.strip()) == 3):
        return f"unexpected country code format: '{code}'"

    # NumericValue being None is valid — WHO suppresses some values
    raw_value = record.get("NumericValue")
    if raw_value is not None:
        try:
            float(raw_value)
        except (ValueError, TypeError):
            return f"non-numeric NumericValue='{raw_value}'"

    return None


def _normalize(record: dict, indicator_code: str) -> dict:
    sex = record.get("Dim1") or "BTSX"
    if sex not in VALID_SEX_CODES:
        sex = "BTSX"

    return {
        "indicator_code": indicator_code,
        "country_code":   record["SpatialDim"].strip().upper(),
        "region":         (record.get("ParentLocation") or "").strip() or None,
        "year":           int(record["TimeDim"]),
        "sex":            sex,
        "value":          _to_float(record.get("NumericValue")),
        "low_value":      _to_float(record.get("Low")),
        "high_value":     _to_float(record.get("High")),
    }


def _to_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None