"""Server-side validation of profile values (never trust the client). None = 'unknown' and is always allowed."""
from .extract import kind as field_kind

MAX_ACRES = 10000

def validate_value(field, value):
    """Return the cleaned value, or raise ValueError with a short reason."""
    if value is None: return None
    k = field_kind(field)
    if k == "bool":
        if isinstance(value, bool): return value
        raise ValueError("yes/no value expected")
    if k == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)): raise ValueError("number expected")
        if value != value or value in (float("inf"), float("-inf")): raise ValueError("number expected")
        if value < 0 or value > MAX_ACRES: raise ValueError(f"value must be between 0 and {MAX_ACRES}")
        return float(value)
    if not isinstance(value, str): raise ValueError("text expected")
    v = value.strip()
    if not v or len(v) > 80: raise ValueError("text must be 1-80 characters")
    return v
