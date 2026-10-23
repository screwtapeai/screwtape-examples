"""Export this key's signed receipts for an auditor (free, uses no calls).

python audit_export.py 2026-10-01T00:00:00Z > receipts.jsonl
Then verify offline with the Node or Python script at https://screwtape.ai/docs/#audit-export.
Coverage depends on the key's retention_days (default 1 day, max 90): for an audit
trail set it to 30 or 90 and export at least monthly. This prints one page (up to
1000 rows); follow next_cursor / X-Next-Cursor for more.
"""
import sys
from common.screwtape_gate import export_receipts
print(export_receipts("jsonl", since=sys.argv[1] if len(sys.argv) > 1 else None), end="")
