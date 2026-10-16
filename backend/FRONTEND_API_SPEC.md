# LeakLens frontend connection

Base URL in local development:

```js
const API_BASE = "http://localhost:8000";
```

## Read dashboard data

```js
export async function getOverview() {
  const r = await fetch(`${API_BASE}/overview`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getRiskProducts() {
  const r = await fetch(`${API_BASE}/products/risk`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getCategories() {
  const r = await fetch(`${API_BASE}/categories`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getCampaignQuality() {
  const r = await fetch(`${API_BASE}/quality/campaigns`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getInventoryQuality() {
  const r = await fetch(`${API_BASE}/quality/inventory`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
```

## Upload and retrain

```js
export async function analyzeFiles(files) {
  const form = new FormData();

  form.append("customers", files.customers);
  form.append("products", files.products);
  form.append("transactions", files.transactions);
  form.append("inventory", files.inventory);
  form.append("campaigns", files.campaigns);

  const r = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    body: form,
  });

  if (!r.ok) {
    throw new Error(await r.text());
  }

  return r.json();
}
```

After `/analyze` succeeds, refetch all dashboard endpoints.

Do NOT manually set `Content-Type` for FormData. The browser adds the multipart boundary automatically.
