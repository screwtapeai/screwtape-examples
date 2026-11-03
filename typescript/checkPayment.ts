// Spend check in TypeScript (Node 18+, built-in fetch). Run: npx tsx checkPayment.ts
const API = process.env.SCREWTAPE_API_URL ?? "https://screwtape.ai";

export interface Invoice {
  invoice_id: string;
  vendor: string;
  date: string;
  currency: string;
  items: { desc: string; amount: number }[];
  tax: number;
  total: number;
}

export interface SpendResult {
  verdict: "pass" | "fail" | "retry";
  next_step: { action: "pass" | "retry" | "escalate"; error_type: string; hint: string };
  duplicate?: { status: "unique" | "duplicate" | "possible_duplicate" | "replay" | "not_checked" };
  receipt?: { receipt_id: string };
}

export async function checkPayment(invoice: Invoice, evidence: string[], idempotencyKey?: string): Promise<SpendResult> {
  const key = process.env.SCREWTAPE_API_KEY;
  if (!key) throw new Error("Set SCREWTAPE_API_KEY. Free key: https://screwtape.ai/signup/");
  const parts = [...invoice.items.map((_, i) => `items.${i}.amount`), "tax"];
  const headers: Record<string, string> = { authorization: `Bearer ${key}`, "content-type": "application/json" };
  if (idempotencyKey) headers["idempotency-key"] = idempotencyKey;
  const response = await fetch(`${API}/v1/duplicate`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      task: `Decide whether the agent may pay invoice ${invoice.invoice_id} from ${invoice.vendor}.`,
      agent_output: JSON.stringify(invoice),
      evidence,
      checks: [{ type: "sum", parts, total: "total", tolerance: 0.01 }],
      duplicate: { vendor_path: "vendor", invoice_id_path: "invoice_id", amount_path: "total", currency_path: "currency", date_path: "date", store: true },
    }),
  });
  if (!response.ok) throw new Error(`Screwtape HTTP ${response.status}: ${(await response.text()).slice(0, 400)}`);
  return (await response.json()) as SpendResult;
}

export const mayPay = (result: SpendResult): boolean => result.next_step.action === "pass";

async function main(): Promise<void> {
  const invoice: Invoice = {
    invoice_id: `INV-${Date.now().toString(36).toUpperCase()}`,
    vendor: "Acme Supplies",
    date: "2026-10-20",
    currency: "USD",
    items: [{ desc: "Widgets", amount: 400 }, { desc: "Shipping", amount: 100 }],
    tax: 95,
    total: 595,
  };
  const evidence = ["PO-77 for Acme Supplies: Widgets 400.00, Shipping 100.00, tax 95.00, total 595.00 USD."];
  for (const attempt of ["first", "second"]) {
    const result = await checkPayment(invoice, evidence);
    console.log(attempt, result.verdict, result.next_step.action, result.duplicate?.status, mayPay(result) ? "PAY" : "DO NOT PAY");
  }
}

if (process.argv[1]?.endsWith("checkPayment.ts") || process.argv[1]?.endsWith("checkPayment.js")) {
  main().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}
