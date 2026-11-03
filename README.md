# Screwtape.ai examples

Copy-paste examples that stop an AI agent from paying the wrong invoice. Each one calls the public
[Screwtape.ai](https://screwtape.ai) API with an API key and does two things before money moves:

1. **Spend check:** the line items and tax must add up to the total, and the invoice must match your
   evidence (purchase order, contract, approval email). You get a verdict and a signed receipt.
2. **Duplicate-invoice check:** the same invoice, or the same vendor and amount within a few days, is
   flagged before the agent pays it twice.

The agent pays only when `next_step.action` is `pass`. Anything else (`retry` or `escalate`) means do not pay.

| Folder | Stack | Run |
|---|---|---|
| [`curl/`](curl/check_payment.sh) | curl + jq | `./curl/check_payment.sh` |
| [`python/`](python/check_payment.py) | Python 3.9+, standard library only | `python python/check_payment.py` |
| [`typescript/`](typescript/checkPayment.ts) | Node 18+, built-in fetch | `cd typescript && npm i && npm start` |
| [`langchain/`](langchain/spend_tool.py) | LangChain tool | `python langchain/spend_tool.py` |
| [`crewai/`](crewai/spend_tool.py) | CrewAI tool | `python crewai/spend_tool.py` |
| [`openai-agents/`](openai-agents/spend_guard.py) | OpenAI Agents SDK, guarded payment tool | `python openai-agents/spend_guard.py` |

## Start in one minute

```bash
export SCREWTAPE_API_KEY=...   # free key: https://screwtape.ai/signup/
python python/check_payment.py
```

Expected output (receipt ids differ per run):

```
first:  verdict=pass action=pass reason=none duplicate=unique receipt=...
  -> PAY
second: verdict=... action=escalate reason=duplicate_invoice duplicate=duplicate receipt=...
  -> DO NOT PAY
wrong total: verdict=fail action=... reason=sum_mismatch duplicate=... receipt=...
  -> DO NOT PAY
```

## The one rule your agent needs

```python
result = check_payment(invoice, evidence)        # POST https://screwtape.ai/v1/duplicate
if result["next_step"]["action"] != "pass":
    stop_and_escalate(result)                    # do not pay
```

Put the check inside the payment tool itself (see [`openai-agents/`](openai-agents/spend_guard.py)),
so the model cannot skip it.

## API in brief

- `POST /v1/duplicate`: spend check plus duplicate-invoice check (used by every example here).
- `POST /v1/judge`: verdict on any agent output, with deterministic checks (`sum`, `required_fields`,
  `json_schema`, `regex`, `equals`, ...). See [checks](https://screwtape.ai/docs/checks/).
- `POST /v1/consensus`: compare 2 to 16 agent answers before acting on them.
- `POST /v1/receipts/verify`: verify a signed receipt.
- Auth: `Authorization: Bearer $SCREWTAPE_API_KEY`. Add an `Idempotency-Key` header to make retries safe.
- Full spec: [openapi.json](https://screwtape.ai/openapi.json). Docs: [screwtape.ai/docs](https://screwtape.ai/docs/).

## MCP

Agents that speak MCP can connect directly: `https://screwtape.ai/mcp` (Streamable HTTP, Bearer key).
Tools: `judge`, `check_duplicate_invoice`, `consensus`.

## Pricing

- **Free:** 10 calls a day, no card.
- **Sandbox Evaluation Pack:** $100 for 2,000 checks.
- **Enterprise pilot:** support@screwtape.ai

Details: [screwtape.ai/pricing](https://screwtape.ai/pricing/).

## License

MIT
