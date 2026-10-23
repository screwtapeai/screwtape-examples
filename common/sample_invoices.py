INVOICE_TEXT = ("Invoice INV-1042 from Acme Supplies. Items: Widgets 400.00, Shipping 100.00. "
                "Subtotal 500.00. Tax 95.00. Total 595.00.")

GOOD = {"invoice_id": "INV-1042", "vendor": "Acme Supplies",
        "items": [{"desc": "Widgets", "amount": 400.00}, {"desc": "Shipping", "amount": 100.00}],
        "subtotal": 500.00, "tax": 95.00, "total": 595.00, "decision": "approve_and_pay"}

# Agent misread the total: 400 + 100 + 95 != 659
BAD = dict(GOOD, total=659.00)

INVOICE_TEXT_3 = ("Invoice INV-2077 from Northwind Parts. Items: Bolts 120.00, Nuts 80.00, "
                  "Freight 50.00. Subtotal 250.00. Tax 47.50. Total 297.50.")

GOOD_3 = {"invoice_id": "INV-2077", "vendor": "Northwind Parts",
          "items": [{"desc": "Bolts", "amount": 120.00}, {"desc": "Nuts", "amount": 80.00},
                    {"desc": "Freight", "amount": 50.00}],
          "subtotal": 250.00, "tax": 47.50, "total": 297.50, "decision": "approve_and_pay"}

# 120 + 80 + 50 + 47.50 != 279.50
BAD_3 = dict(GOOD_3, total=279.50)

# Fields used by the duplicate check (currency_path, date_path)
GOOD_DUP = dict(GOOD, currency="USD", invoice_date="2026-10-20")
INVOICE_TEXT_DUP = INVOICE_TEXT + " Currency USD. Invoice date 2026-10-20."
