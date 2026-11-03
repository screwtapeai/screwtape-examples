"""OpenAI Agents SDK: the payment tool itself refuses to pay unless Screwtape returns pass.

The check runs in code, not in the prompt, so the model cannot skip it.

    pip install -r requirements.txt
    export SCREWTAPE_API_KEY=...  OPENAI_API_KEY=...
    python openai-agents/spend_guard.py
"""
import asyncio
import json
import os
import sys

from agents import Agent, Runner, function_tool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
from screwtape import check_payment, may_pay, summary  # noqa: E402

PURCHASE_ORDER = "PO-77 for Acme Supplies: Widgets 400.00, Shipping 100.00, tax 95.00, total 595.00 USD."


def guarded_pay(invoice: dict) -> str:
    result = check_payment(invoice, [PURCHASE_ORDER])
    if not may_pay(result):
        return f"BLOCKED: {summary(result)}. Do not pay; hand this to a person."
    # Your real payment call goes here (ERP, bank API, payables system).
    return f"PAID {invoice['invoice_id']} ({summary(result)})"


@function_tool
def pay_invoice(invoice_json: str) -> str:
    """Pay an invoice. invoice_json: invoice_id, vendor, date, currency, items[].amount, tax, total."""
    return guarded_pay(json.loads(invoice_json))


agent = Agent(
    name="Payables agent",
    instructions="You pay supplier invoices with pay_invoice. If it returns BLOCKED, stop and report why.",
    tools=[pay_invoice],
)


async def main() -> None:
    invoice = {"invoice_id": "INV-1042", "vendor": "Acme Supplies", "date": "2026-10-20", "currency": "USD",
               "items": [{"desc": "Widgets", "amount": 400.0}, {"desc": "Shipping", "amount": 100.0}], "tax": 95.0, "total": 595.0}
    if not os.environ.get("OPENAI_API_KEY"):
        print(guarded_pay(invoice))  # no model key: run the guarded tool directly
        return
    result = await Runner.run(agent, f"Pay this invoice: {json.dumps(invoice)}")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
