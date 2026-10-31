# Takeover Checks

Subdomain takeover happens when a DNS record (usually a CNAME) still points at
a third-party service, but nobody owns that resource on the service. An
attacker who claims it can serve content under **your** domain.

Recon flags hosts whose CNAME targets one of these services and whose page looks
like an unclaimed resource.

## How it works

1. **Collect CNAMEs** — from the httpx `-cname` field and from a dedicated
   `dnsx -cname -resp` pass over every discovered host.
2. **Match services** — the CNAME is compared against `TAKEOVER_SERVICES` in
   [`recon/fingerprints.py`](../recon/fingerprints.py), longest suffix first.
3. **Fetch and fingerprint** — for each candidate, `https://host` then
   `http://host` is fetched (8 s timeout, certificate errors ignored). The body
   is searched for service-specific markers.

## Verdicts

| Verdict | Meaning | Evidence |
|---|---|---|
| `LIKELY` | The service is serving its "resource not found" page. | A fingerprint marker was found in the response body. |
| `POSSIBLE` | The service did not respond over HTTPS or HTTP, but the CNAME still points at it. | Both fetches failed (DNS/connection). |
| (blank) | CNAME matches a service but the app is live — not dangling. | A page was returned without a marker, or the CNAME is unrelated. |

Rows with a verdict are shown in red and appear in `takeovers` in the JSON
output.

## Covered services

GitHub Pages, AWS S3, Heroku, CloudFront, Fastly, Azure (App Service, VM,
Traffic Manager, Blob), Netlify, Surge, Bitbucket, Read the Docs, WordPress.com,
Shopify, Zendesk, Statuspage, Pantheon, Tumblr, Ghost, Webflow, UserVoice,
Help Scout, Teamtailor, LaunchRock, DigitalOcean Spaces, Google Cloud Storage,
Firebase, Vercel, Cloudflare Pages, Fly.io.

## Limits and false positives

- Fingerprints change. A service may return a generic 404 that matches nothing.
- `POSSIBLE` can be a firewall/VPN blocking the probe rather than a real issue.
- This is **not** a substitute for manual verification. Before reporting,
  confirm the resource is claimable in the provider's dashboard/API.
- Only the first-level CNAME chain is inspected.

## Extending the list

Add an entry keyed by the CNAME suffix:

```python
"example-saas.com": {
    "service": "Example SaaS",
    "markers": ["this instance is not configured"],
},
```

Markers are matched case-insensitively against the first 200 KB of the body.
Prefer unique phrases; avoid generic text like `404 not found`.
