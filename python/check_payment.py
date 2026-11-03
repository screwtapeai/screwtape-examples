"""Check an agent's payment before it spends: plain Python, no framework.

    export SCREWTAPE_API_KEY=...   # free: https://screwtape.ai/signup/
    python python/check_payment.py
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))
from screwtape import check_payment, may_pay, summary  # noqa: E402

# A unique invoice number per run, so the first call is "unique" and the second is "duplicate".
invoice_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
invoice = {
    "invoice_id": invoice_id,
    "vendor": "Acme Supplies",
    "date": "2026-10-20",
    "currency": "USD",
    "items": [{"desc": "Widgets", "amount": 400.00}, {"desc": "Shipping", "amount": 100.00}],
    "tax": 95.00,
    "total": 595.00,
}
evidence = [
    f"Purchase order PO-77 for Acme Supplies: Widgets 400.00, Shipping 100.00, tax 95.00, total 595.00 USD. Invoice {invoice_id} dated 2026-10-20 matches PO-77.",
]

first = check_payment(invoice, evidence)
print("first: ", summary(first))
print("  ->", "PAY" if may_pay(first) else "DO NOT PAY")

# The agent tries to pay the same invoice again (a retry loop, a resent email, a second agent).
second = check_payment(invoice, evidence)
print("second:", summary(second))
print("  ->", "PAY" if may_pay(second) else "DO NOT PAY")

# An invoice whose total does not add up (400 + 100 + 95 != 659).
wrong_total = dict(invoice, invoice_id=f"{invoice_id}-B", total=659.00)
third = check_payment(wrong_total, evidence)
print("wrong total:", summary(third))
print("  ->", "PAY" if may_pay(third) else "DO NOT PAY")
