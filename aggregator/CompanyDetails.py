"""Our own seller details, the HSN code and the Indian financial year.

Every challan carries a block describing *us* -- the consignor -- alongside the
block describing the client. None of it lives in a table: there is exactly one
seller, and a one-row table to hold it would be a settings file with extra
steps.

The values below are **placeholders** until the real registration details are
supplied; ``DEFAULT_HSN_CODE`` is likewise a stand-in for the per-product HSN
classification, which will move onto ``Product`` once the catalogue is
classified.
"""

from __future__ import annotations

from datetime import date

from common.models import indian_now

# Placeholders -- replace with the real registration details.
COMPANY_DETAILS = {
    "company_name": "Sai Seeds Private Limited",
    "company_address": "Plot 42, Industrial Area Phase II, Jalna, Maharashtra 431203",
    "gst_number": "27AABCS1429B1ZQ",
    "state_name": "Maharashtra",
}

# Stand-in until HSN is classified per product. 1209 91 00 is "vegetable seeds
# for sowing", which is the right family for a seed business.
DEFAULT_HSN_CODE = "12099100"

# The Indian financial year runs April -> March.
FINANCIAL_YEAR_START_MONTH = 4


def current_financial_year(on: date | None = None) -> str:
    """The Indian financial year containing ``on``, as ``"2026-2027"``.

    April to March, so 2026-09-15 and 2027-03-31 are both ``"2026-2027"`` while
    2027-04-01 is ``"2027-2028"``. Defaults to today in Asia/Kolkata -- the same
    clock every other dated field on a dispatch uses.
    """
    if on is None:
        on = indian_now().date()
    start_year = on.year if on.month >= FINANCIAL_YEAR_START_MONTH else on.year - 1
    return f"{start_year}-{start_year + 1}"
