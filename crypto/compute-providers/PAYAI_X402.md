# PayAI / x402 — Machine Payment Rail

## What It Does
HTTP 402 → agent pays in stablecoins → gets result. 35M+ transactions.

## QDW Role
Native payment interface for QDW APIs and Moltwork.

## Strategy
- HTTP request → 402 quote → autonomous payment → result
- Much cleaner than subscription/API-key infrastructure
- QDW APIs become payable via x402
