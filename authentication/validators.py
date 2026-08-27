import re

from django.core.exceptions import ValidationError

# Indian mobile number without any country code: exactly 10 digits.
PHONE_NUMBER_RE = re.compile(r"^\d{10}$")


def validate_phone_number(value):
    """Ensure ``value`` is a plain 10-digit numeric phone number.

    No country codes (like +91) or separators are allowed.
    """
    if not value:
        raise ValidationError("Phone number is required.")

    value = str(value).strip()

    if PHONE_NUMBER_RE.fullmatch(value) is None:
        raise ValidationError(
            "Phone number must be exactly 10 digits, numeric only "
            "(no country code like +91, spaces, or dashes)."
        )
