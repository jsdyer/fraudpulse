# Shared CoolCode collector registration

FraudPulse's public charts and downloads run entirely on GitHub Pages. The shared
`coolcode-visitor-api` Cloudflare Worker separately accepts tool IDs for aggregate
page-open counts and private issue submissions.

Cloudflare is intentionally left unchanged for this launch. Its current allowlist
was inspected and does not yet contain `fraudpulse`.

1. In the Cloudflare dashboard, open **Workers & Pages → coolcode-visitor-api → Edit code**.
2. Find the existing `toolList` array and add one entry: `"fraudpulse",`.
3. Click **Deploy**. Keep the existing D1 `DB` binding, secrets, routes and all other
   code/settings unchanged.
4. Open FraudPulse normally and inspect its `POST /event` request for a successful
   response. The owner dashboard's Tool traffic section will then accept its usage.

No new Worker, database migration, DNS record, token or billing change is needed.
The dashboard, filters, public datasets and GitHub Actions refreshes work before
this change; aggregate visit counting and private issue submissions for FraudPulse
need the allowlist entry. Do not submit a fake issue just to test registration.

The existing CoolCode hub documentation also explains collector registration:
[adding tools](https://github.com/jsdyer/jsdyer.github.io/blob/main/docs/adding-tools.md#enable-usage-counts-and-private-issue-reports).
