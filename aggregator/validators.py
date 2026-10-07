import re

from django.core.exceptions import ValidationError

# 15-character GSTIN: 2-digit state code, 5 letters (PAN), 4 digits, 1 letter,
# 1 entity digit/letter, the literal 'Z', and 1 checksum digit/letter.
GST_NUMBER_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")


def validate_gst_number(value):
    """Ensure ``value`` is empty or a syntactically valid 15-character GSTIN.

    GST is optional, so an empty value passes. A non-empty value is matched
    case-sensitively against the standard GSTIN layout; callers should
    upper-case it first (``Client.clean`` does).
    """
    value = str(value or "").strip()
    if not value:
        return

    if GST_NUMBER_RE.fullmatch(value) is None:
        raise ValidationError(
            "GST number must be a valid 15-character GSTIN "
            "(e.g. '27AAPFU0939F1ZV')."
        )
