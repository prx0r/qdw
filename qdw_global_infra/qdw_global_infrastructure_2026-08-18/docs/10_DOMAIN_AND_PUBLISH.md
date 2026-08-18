# Domain + Publishing Infrastructure

## Domain flow

```text
generate names
  ↓
registrar search
  ↓
authoritative availability + price check
  ↓
DomainQuote
  ↓
HumanAction(domain_purchase_approval)
  ↓
approved
  ↓
registration adapter
  ↓
DNS/custom domain
  ↓
external smoke
```

Cloudflare's current Registrar API supports search and authoritative check endpoints and can register
supported domains programmatically. QDW intentionally gates the purchase step because it is a billable,
irreversible external side effect.

Cloudflare Workers Custom Domains can automate DNS/certificate provisioning for Worker-hosted products.

## Distribution Registry

Publishing targets are data:

- website
- GitHub
- PyPI
- npm
- MCP Registry
- browser store
- Shopify
- Etsy
- eBay
- Amazon

Each target declares product types, account requirements and an independent verification method.
