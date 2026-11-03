#!/usr/bin/env bash
# Spend check with curl. Needs SCREWTAPE_API_KEY (free: https://screwtape.ai/signup/) and jq.
set -euo pipefail
API="${SCREWTAPE_API_URL:-https://screwtape.ai}"
: "${SCREWTAPE_API_KEY:?Set SCREWTAPE_API_KEY}"

INVOICE='{"invoice_id":"INV-1042","vendor":"Acme Supplies","date":"2026-10-20","currency":"USD","items":[{"desc":"Widgets","amount":400},{"desc":"Shipping","amount":100}],"tax":95,"total":595}'

BODY=$(jq -n --arg inv "$INVOICE" '{
  task: "Decide whether the agent may pay invoice INV-1042 from Acme Supplies.",
  agent_output: $inv,
  evidence: ["PO-77 for Acme Supplies: Widgets 400.00, Shipping 100.00, tax 95.00, total 595.00 USD."],
  checks: [{type: "sum", parts: ["items.0.amount", "items.1.amount", "tax"], total: "total", tolerance: 0.01}],
  duplicate: {vendor_path: "vendor", invoice_id_path: "invoice_id", amount_path: "total", currency_path: "currency", date_path: "date", store: true}
}')

RESULT=$(curl -sS --fail-with-body "$API/v1/duplicate" \
  -H "Authorization: Bearer $SCREWTAPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$BODY")

echo "$RESULT" | jq '{verdict, action: .next_step.action, reason: .next_step.error_type, duplicate: .duplicate.status, receipt: .receipt.receipt_id}'

if [ "$(echo "$RESULT" | jq -r '.next_step.action')" = "pass" ]; then
  echo "PAY"
else
  echo "DO NOT PAY"
  exit 1
fi
