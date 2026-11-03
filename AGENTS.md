# AGENTS.md

Instructions for coding agents working in this repository.

## What this repo is
Copy-paste examples that call the public Screwtape.ai API (`https://screwtape.ai`) to check an agent's
payment before it spends and to catch duplicate invoices. There is no server code here.

## Rules
- Call only the public API: `POST /v1/duplicate`, `POST /v1/judge`, `POST /v1/consensus`, `POST /v1/receipts/verify`.
- Read the key from `SCREWTAPE_API_KEY` and the host from `SCREWTAPE_API_URL` (default `https://screwtape.ai`). Never hard-code or log a key.
- Pay only when `next_step.action == "pass"`. Treat `retry` and `escalate` as do-not-pay.
- Keep each example short and runnable on its own. `python/` stays standard-library only.
- The free tier is 10 calls a day: do not add loops that call the API many times.

## Check your change
```bash
python -m py_compile python/*.py langchain/*.py crewai/*.py openai-agents/*.py
bash -n curl/check_payment.sh
cd typescript && npm i && npx tsc --noEmit
```

## Reference
- Spec: https://screwtape.ai/openapi.json
- Docs: https://screwtape.ai/docs/
- MCP: https://screwtape.ai/mcp
- Support: support@screwtape.ai
