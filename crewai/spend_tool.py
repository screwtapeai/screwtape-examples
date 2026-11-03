"""CrewAI: a tool the paying agent calls before it spends.

    pip install -r requirements.txt
    export SCREWTAPE_API_KEY=...
    python crewai/spend_tool.py
"""
import json
import os
import sys

from crewai.tools import tool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
from screwtape import check_payment, may_pay, summary  # noqa: E402


@tool("Screwtape payment check")
def screwtape_check_payment(invoice_json: str, evidence: str) -> str:
    """Call before paying any invoice. invoice_json is the invoice as JSON (invoice_id, vendor, date,
    currency, items[].amount, tax, total). evidence is the purchase order or contract text.
    Returns PAY or DO_NOT_PAY with the reason and the signed receipt id."""
    result = check_payment(json.loads(invoice_json), [evidence])
    return ("PAY " if may_pay(result) else "DO_NOT_PAY ") + summary(result)


# In a crew: Agent(role="Accounts payable", tools=[screwtape_check_payment], ...)
# and tell it in the task: "Pay only when Screwtape payment check returns PAY."

if __name__ == "__main__":
    invoice = {"invoice_id": "INV-1042", "vendor": "Acme Supplies", "date": "2026-10-20", "currency": "USD",
               "items": [{"desc": "Widgets", "amount": 400.0}, {"desc": "Shipping", "amount": 100.0}], "tax": 95.0, "total": 595.0}
    print(screwtape_check_payment.run(invoice_json=json.dumps(invoice),
                                      evidence="PO-77 for Acme Supplies: Widgets 400.00, Shipping 100.00, tax 95.00, total 595.00 USD."))
