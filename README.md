# Screwtape.ai examples

Small examples that check an agent's invoice decision before a payment goes out. They use the public [Screwtape.ai](https://screwtape.ai) judge API, `POST /v1/judge`. Each verdict comes with a signed receipt you can keep for your auditor.

- `crewai/`: a CrewAI AP-clerk agent proposes `approve_and_pay`, and Screwtape checks it.
- `langgraph/`: the same flow as a graph, `propose -> judge -> {pay | fix | human}`, with a conditional edge on `next_step.action`.
- `autogen/`: an AutoGen (`autogen-agentchat` 0.4+) AP agent that must call the `screwtape_invoice_check` tool before approving. `--stub` runs without an LLM.
- `audit_export.py`: export your signed receipts for an auditor (`GET /v1/receipts/export`).
- `mcp/`: an `mcp.json` that adds the Screwtape MCP server (`https://screwtape.ai/mcp`, tool `judge`) to Claude, Cursor or another MCP client.

Every call runs two deterministic checks:

- `required_fields`: `invoice_id, vendor, subtotal, tax, total, decision`
- `sum`: `items.0.amount + ... + items.N-1.amount + tax == total`, built from however many line items the invoice has (`common/screwtape_gate.py: invoice_checks`)

Optionally, a third check:

- `duplicate` (opt-in, needs an API key): compares the invoice with ones your key recorded earlier. Same vendor and invoice number returns `next_step.error_type: duplicate_invoice`; a normalised invoice number, or the same vendor, amount and date within `window_days` (default 3), returns `possible_duplicate`. Both escalate to a person. Screwtape stores only keyed HMAC fingerprints, never the invoice, and only when `store: true`; they're kept 180 days by default (`retain_days` 1 to 400). Delete them with `DELETE /v1/dedupe/fingerprints`. Fingerprints are recorded only when the overall verdict isn't `fail`, so send the invoice text as `evidence` (the examples do). See `common/screwtape_gate.py: duplicate_check`.

If a deterministic check fails, the call returns `verdict: fail` right away and makes no model call. The response's `next_step.action` tells the agent what to do:

| next_step.action | example does |
|---|---|
| `pass` | proceed and pay, keeping `receipt.receipt_id` |
| `retry` | block and send `next_step.hint` back to the agent |
| `escalate` | stop and hand off to a human approver (this includes `duplicate_invoice` and `possible_duplicate`) |

**Advisory mode.** Pass `advisory=True` (sends `mode: "advisory"`) when a person must make the call. The verdict, checks, `next_step` and receipt are the same, plus `decision_owner: "human"`, `recommended_action` (`approve`, `review` or `return`) and a notice. Screwtape never approves, holds or releases a payment, and the signed receipt records that the call was advisory.

**Retries.** If your agent may resend the same invoice, pass `idempotency_key=` (sent as the `Idempotency-Key` header). A retry then reports `duplicate.status: "replay"` instead of `duplicate`. A replay is billed like any other call.

## Ready-to-use steps

| Framework | File | Use |
|---|---|---|
| CrewAI | `crewai/screwtape_steps.py` | `Task(guardrail=make_guardrail(invoice_text, duplicate=True))`: pass returns the decision + receipt id, retry sends the hint back to the agent, escalate stops the crew. Also `ScrewtapeInvoiceCheckTool` for agents that call the check themselves. Full example: `crewai/guardrail_example.py` |
| LangGraph | `langgraph/screwtape_node.py` | `g.add_node("judge", make_judge_node(invoice_text, duplicate=True))` and `g.add_conditional_edges("judge", route, {"pass": ..., "retry": ..., "escalate": ...})` |
| AutoGen | `autogen/main.py` | `screwtape_invoice_check` is a plain async function you pass in `tools=[...]`; it also works as a tool in Microsoft Agent Framework |

> **The agent step is stubbed.** In `--mock` mode (CrewAI), `--stub` mode (AutoGen) and in the LangGraph `propose` node, the agent's reasoning and decision are canned JSON, not a model call. Swap in your own model or agent; only the Screwtape judge call is real.

Shared code lives in `common/` (`screwtape_gate.py` for the judge client, checks, `next_step` handling and export, `sample_invoices.py` for 2-item, 3-item and duplicate-check invoices). Run each example from its own folder.

> **MCP note:** whether `${SCREWTAPE_API_KEY}` in `mcp/mcp.json` gets expanded from your environment depends on your MCP client. If yours doesn't expand it, paste the key in directly and keep that file out of git.

## Setup

1. Get a free key (100 calls per UTC day) at https://screwtape.ai/signup/ or with `POST /v1/signup` (see the [docs](https://screwtape.ai/docs/)).
2. Set the key in your environment:

```bash
cp .env.example .env            # then put your key in it
export SCREWTAPE_API_KEY=sk_screw_...
```

## Run

```bash
cd crewai && pip install -r requirements.txt
python main.py --mock           # canned agent decision, no LLM key needed
python main.py --mock --bad     # canned decision with a wrong total
python main.py                  # real CrewAI agent (needs your LLM key, e.g. OPENAI_API_KEY)

cd ../langgraph && pip install -r requirements.txt
python main.py                  # stub agent node; swap propose() for your LLM
python main.py --bad
python main.py --three --bad    # 3-line-item invoice, wrong total
python main.py --dup            # add the duplicate check; a second run of the same invoice escalates
python main.py --dup --advisory # advisory mode

cd ../autogen && pip install -r requirements.txt
python main.py --stub           # canned decision + duplicate check, no LLM key needed
python main.py --stub --advisory
python main.py                  # real AssistantAgent (needs OPENAI_API_KEY)

cd .. && python audit_export.py 2026-10-01T00:00:00Z > receipts.jsonl
```

The receipt log only holds what your key's `retention_days` allows (default 1 day, max 90). For an audit trail, set it to 30 or 90 with `PATCH /v1/account/settings` and export at least monthly. Verify the exported rows offline with the Node or Python script at https://screwtape.ai/docs/#audit-export.

## Sample output

```
verdict=pass score=1 verification=verified engine=groq
next_step=pass error_type=none hint=The output passed. Use it.
receipt_id=6f14a17e-62e5-4e7e-8caa-deaddb8e6e8d
-> PROCEED: payment may go out (keep the receipt for your auditor)

verdict=fail score=0 verification=failed engine=deterministic
next_step=retry error_type=sum_mismatch hint=items.0.amount + items.1.amount + tax must add up to 'total'. Recalculate the parts or the total and resend.
receipt_id=f42dd625-e226-4de8-b60c-31f6f7550590
-> BLOCK: send the hint back to the agent and fix before paying
```

To check a receipt, call `POST /v1/receipts/verify`, or verify it yourself against https://screwtape.ai/.well-known/screwtape-receipt-keys.json.

## Docs

- API docs: https://screwtape.ai/docs/
- Checks: https://screwtape.ai/docs/checks/
- Audit export and verify scripts: https://screwtape.ai/docs/#audit-export
- OpenAPI spec: https://screwtape.ai/openapi.json
- LLM-readable summary: https://screwtape.ai/llms.txt

MIT licensed. Copyright (c) 2026 Screwtape.ai.
