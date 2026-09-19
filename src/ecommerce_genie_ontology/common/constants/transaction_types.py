"""Funds-movement type codes and account products. Shared by provision, OLTP, and ETL."""

from __future__ import annotations

ACCOUNT_PRODUCTS: tuple[str, ...] = ("checking", "cd", "credit_card", "brokerage")

# type_code, class, direction, same_bank, same_account
TRANSACTION_TYPES: tuple[tuple[str, str, str, bool, bool], ...] = (
    ("wire_transfer", "transfer", "out", False, False),
    ("cash_deposit", "cash", "in", True, True),
    ("cash_withdrawal", "cash", "out", True, True),
    ("bank_transfer_other", "transfer", "out", False, False),
    ("bank_transfer_same_acct", "transfer", "book", True, True),
    ("intra_bank_same_accts", "transfer", "book", True, False),
    ("cd_withdraw", "term", "out", True, False),
    ("cd_deposit", "term", "in", True, False),
    ("brokerage_in", "securities", "in", False, False),
    ("brokerage_out", "securities", "out", False, False),
    ("demand_draft_request", "instrument", "out", True, False),
    ("demand_draft_issue", "instrument", "out", True, False),
    ("card_purchase", "card", "out", False, False),
    ("card_payment", "card", "in", True, False),
    ("card_due", "card", "obligation", True, False),
)

COUNTERPARTY_KINDS: tuple[tuple[str, str], ...] = (
    ("CP001", "same_bank"),
    ("CP002", "other_bank"),
    ("CP003", "brokerage"),
    ("CP004", "card_issuer"),
    ("CP005", "other_bank"),
    ("CP006", "same_bank"),
    ("CP007", "brokerage"),
    ("CP008", "card_issuer"),
)

# Lab generate only. 30 billion postings is capacity, not a GitHub Action.
LAB_POSTINGS_PER_YEAR = 500
MAX_GENERATED_ORDERS = 20_000_000
MAX_GENERATED_POSTINGS = 2_000_000
