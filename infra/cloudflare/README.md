# Cloudflare cache, headers and redirects

GitHub Pages cannot set custom HTTP response headers and cannot issue a real
HTTP 301. This directory keeps the edge configuration for the zone that serves
both sites:

- `furkankoykiran.com.tr` (portfolio, Hugo)
- `blog.furkankoykiran.com.tr` (blog, Hugo)

GitHub Pages is the origin. Cloudflare must be in **proxied** (orange-cloud)
mode for any of these rules to apply. If a hostname is DNS-only, Cloudflare
never sees the response and none of the rules below run.

There are three ways to apply the same policy:

1. the dashboard steps in this file,
2. the Terraform configuration in this directory,
3. the Rulesets API payloads in `api/` (create once, update by ruleset ID).

All three produce the same three rulesets:

| Phase | Purpose |
|---|---|
| `http_request_cache_settings` | Keep HTML fresh; cache fingerprinted assets for a year; images for 30 days; sitemap/llms/security files for 5 minutes. |
| `http_response_headers_transform` | Baseline security headers and an HTML revalidation header. |
| `http_request_dynamic_redirect` | True 301s from the old `ProspectForge` URLs to `Leadwalk`. |

The Hugo `aliases` in `data/projects.json` remain as a fallback: they render a
meta-refresh page for anyone who reaches the GitHub Pages origin directly. The
Cloudflare rule is what search engines and normal visitors see.

---

## 1. Check the proxy and the zone

1. Cloudflare dashboard → select the `furkankoykiran.com.tr` zone.
2. DNS → Records: the records for `furkankoykiran.com.tr` and
   `blog.furkankoykiran.com.tr` must be **Proxied**.
3. SSL/TLS → Overview: use **Full (strict)**. GitHub Pages serves a valid
   certificate for the custom domain.
4. SSL/TLS → Edge Certificates: enable **Always Use HTTPS**.

Both hostnames are in the same zone, so there is one zone ID and one set of
phase rules. The rules match both hosts explicitly; other subdomains in the
zone are untouched.

---

## 2. Cache Rules (dashboard)

Go to **Caching → Cache Rules → Create rule**. Create the four rules below in
this order. The order matters because the first matching rule wins.

| # | Rule name | When incoming requests match (expression) | Then |
|---|---|---|---|
| 1 | `html-bypass` | `(http.host eq "furkankoykiran.com.tr" or http.host eq "blog.furkankoykiran.com.tr") and http.request.method eq "GET" and not http.request.uri.path contains "."` | **Bypass cache** |
| 2 | `immutable-build-assets` | `(http.host eq "furkankoykiran.com.tr" or http.host eq "blog.furkankoykiran.com.tr") and http.request.method eq "GET" and http.request.uri.path matches "^/(css|js|fonts)/"` | **Eligible for cache**. Edge TTL: **Ignore cache-control header and use this TTL → 1 year**. Browser TTL: **Override origin → 1 year**. |
| 3 | `images` | `(http.host eq "furkankoykiran.com.tr" or http.host eq "blog.furkankoykiran.com.tr") and http.request.method eq "GET" and http.request.uri.path matches "\.(avif|webp|png|jpe?g|gif|svg|ico)$"` | **Eligible for cache**. Edge TTL: **1 month**. Browser TTL: **1 month**. |
| 4 | `machine-readable` | `(http.host eq "furkankoykiran.com.tr" or http.host eq "blog.furkankoykiran.com.tr") and http.request.method eq "GET" and http.request.uri.path matches "\.(xml|txt|json|webmanifest)$"` | **Eligible for cache**. Edge TTL: **5 minutes**. Browser TTL: **5 minutes**. |

Why this shape:

- HTML has no fingerprint in its URL, so it must bypass the edge cache. The
  origin (GitHub Pages) is fast, and a deploy is visible immediately.
- Hugo fingerprints CSS and JavaScript (`resources.Fingerprint`), and processed
  images get content-addressed names. A one-year browser TTL is safe for those
  URLs.
- `sitemap.xml`, `llms.txt`, `llms-full.txt`, `ai.txt`, `robots.txt`,
  `.well-known/security.txt` and `site.webmanifest` stay short-lived so
  IndexNow and AI crawlers see a new deploy within minutes.
- `cache=false` for HTML is a Cloudflare edge decision. The response header
  rule in step 3 also sets `Cache-Control: public, max-age=0, must-revalidate`
  on HTML so browsers revalidate too.

> If the dashboard shows a "Cache eligibility" toggle, choose
> **Eligible for cache** for rules 2–4 and **Bypass cache** for rule 1.

---

## 3. Response Header Transform Rule (dashboard)

Go to **Rules → Transform Rules → Modify Response Header → Create rule**.

- **Rule name:** `baseline-security-headers`
- **When incoming requests match:** `(http.host eq "furkankoykiran.com.tr" or http.host eq "blog.furkankoykiran.com.tr")`
- **Then** add these operations:

| Operation | Header name | Value |
|---|---|---|
| Set static | `X-Content-Type-Options` | `nosniff` |
| Set static | `Referrer-Policy` | `strict-origin-when-cross-origin` |
| Set static | `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=(), usb=()` |

Add a second rule in the same ruleset:

- **Rule name:** `html-revalidate`
- **When incoming requests match:** `(http.response.content_type.media_type eq "text/html")`
- **Then:** Set static `Cache-Control` to `public, max-age=0, must-revalidate`

Do **not** add a strict `Content-Security-Policy` by default. The sites use
inline JSON-LD, the Cloudflare beacon, GA4/Clarity and third-party giscus and
demo iframes; a policy copied from a static site will break them. If you want
CSP, start with `Content-Security-Policy-Report-Only`, collect reports for a
week, then enforce a policy that explicitly allows the analytics and embed
origins. HSTS is better configured in **SSL/TLS → Edge Certificates → HSTS**
(see step 5), not as a Transform Rule.

---

## 4. Redirect Rules (dashboard)

Go to **Rules → Redirect Rules → Create rule** and create two **Single
Redirects**:

| Rule name | When incoming requests match | Target | Status |
|---|---|---|---|
| `prospectforge-tr` | `(http.host eq "furkankoykiran.com.tr" and http.request.uri.path matches "^/projeler/prospectforge/?$")` | `https://furkankoykiran.com.tr/projeler/leadwalk/` | **301** |
| `prospectforge-en` | `(http.host eq "furkankoykiran.com.tr" and http.request.uri.path matches "^/en/projects/prospectforge/?$")` | `https://furkankoykiran.com.tr/en/projects/leadwalk/` | **301** |

Enable **Preserve query string**. The regex accepts both `/prospectforge/` and
`/prospectforge` so a missing trailing slash does not fall through.

Why both a Cloudflare rule and Hugo aliases:

- Cloudflare returns a real 301 before the request reaches GitHub Pages. This
  is what Google and Bing see.
- Hugo's `aliases` page is a meta-refresh fallback for a direct origin request
  (for example during local development, or if the Cloudflare rule is removed).

---

## 5. HSTS and TLS

1. **SSL/TLS → Edge Certificates → HTTP Strict Transport Security (HSTS)**:
   enable it with `max-age=15552000` (6 months), **Include subdomains** on.
   Leave **Preload** off at first.
2. After at least two weeks of confirmed HTTPS on every subdomain, consider
   preload. Preload is effectively permanent; do not enable it on the same day
   you change DNS.
3. Keep **Automatic HTTPS Rewrites** on and **Opportunistic Encryption** on.

HSTS is sent only over HTTPS, so always test with `https://`.

---

## 5b. Recommended zone settings

These are one-time toggles, not Terraform resources:

- **Caching → Tiered Cache:** enable Smart Tiered Cache. It reduces origin
  requests without changing the browser-facing TTLs above.
- **Speed → Optimization:** Brotli on, Early Hints on, Rocket Loader off, Auto
  Minify off. Hugo already minifies, and Rocket Loader reorders scripts in a
  way that can break GA4 Consent Mode and the theme's appearance toggle.
- **Security → Bots:** do not enable Bot Fight Mode or an AI crawler block for
  these hostnames. The sites intentionally allow search and AI agents.
- **Network:** HTTP/2 and HTTP/3 on; 0-RTT off unless you have tested replay
  behaviour with the contact form or analytics.

---

## 6. Purge and deploy

Because HTML bypasses the edge cache, normal GitHub Pages deploys need no
purge. The short TTLs on sitemap/llms files expire within five minutes.

Purge once after applying or changing rules:

- Dashboard → **Caching → Configuration → Purge Everything**, or
- API: `curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" -H "Authorization: Bearer $CF_API_TOKEN" -H "Content-Type: application/json" --data '{"purge_everything":true}'`

For an urgent single-page fix, purge by URL instead of everything:

```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"files":["https://furkankoykiran.com.tr/en/projects/leadwalk/"]}'
```

Do not enable **Bot Fight Mode** or an AI crawler block for these hostnames.
The sites intentionally allow search and AI agents; `robots.txt` declares the
Content Signals policy as comments because Google and Yandex reject unknown
directives.

---

## 7. Terraform

The Terraform configuration manages the three rulesets for the single zone.
It does not manage DNS, certificates or the HSTS toggle; those are account
decisions and are safer to set once in the dashboard.

### Prerequisites

- Terraform 1.6 or newer.
- A Cloudflare API token with:
  - **Zone → Cache Rules → Edit**
  - **Zone → Transform Rules → Edit**
  - **Zone → Dynamic Redirect → Edit**
  - **Zone → Zone Settings → Read** (for the zone lookup/verification)
- The zone ID from **Overview → Zone ID**.

### Apply

```bash
cd infra/cloudflare
export CLOUDFLARE_API_TOKEN="..."
terraform init
terraform plan -var="zone_id=$CF_ZONE_ID"
terraform apply -var="zone_id=$CF_ZONE_ID"
```

PowerShell:

```powershell
cd infra/cloudflare
$env:CLOUDFLARE_API_TOKEN = "..."
terraform init
terraform plan -var="zone_id=$env:CF_ZONE_ID"
terraform apply -var="zone_id=$env:CF_ZONE_ID"
```

Or copy `terraform.tfvars.example` to `terraform.tfvars`, fill in the zone ID,
and run `terraform plan` / `terraform apply` without `-var`.

The provider uses `CLOUDFLARE_API_TOKEN` from the environment. Never commit a
token or a `terraform.tfvars` file; both are ignored by `.gitignore`.

### Destroy

`terraform destroy` removes only the rulesets it created. It does not remove
DNS records, certificates or HSTS.

---

## 8. Rulesets API (JSON)

`api/` contains full create payloads for the three phase entrypoints. They are
useful when Terraform is not available. Replace `$ZONE_ID` and
`$CF_API_TOKEN`.

### Create the rulesets

```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/rulesets" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data @api/cache-rules.json

curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/rulesets" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data @api/response-headers.json

curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/rulesets" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data @api/redirects.json
```

A zone can have only one entrypoint ruleset per phase. If a phase already has
rules, `POST` fails; update the existing ruleset instead. The following reads
the entrypoint ID and replaces its rules with the payload from `api/` (requires
`jq`):

```bash
PHASE=http_request_cache_settings
RULESET_ID=$(curl -s "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/rulesets/phases/$PHASE/entrypoint" \
  -H "Authorization: Bearer $CF_API_TOKEN" | jq -r '.result.id')
jq '{rules}' api/cache-rules.json > /tmp/cache-rules.json
curl -X PUT "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/rulesets/$RULESET_ID" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data @/tmp/cache-rules.json
```

`PUT` replaces all rules in that phase. If the zone already has unrelated
cache or header rules, merge them first or use the dashboard/Terraform, which
show the complete list before applying.

---

## 9. Verify

Run these after applying the rules. Replace the fingerprinted asset URL with
one from `view-source:` if the build hash changed.

```bash
# 301, not a meta refresh
curl -sI "https://furkankoykiran.com.tr/en/projects/prospectforge/" | grep -Ei "^(HTTP|location|cache-control)"

# HTML revalidation and security headers
curl -sI "https://furkankoykiran.com.tr/en/projects/leadwalk/" | grep -Ei "^(HTTP|cache-control|x-content-type-options|referrer-policy|permissions-policy)"

# Fingerprinted CSS should be cached for a year
curl -sI "https://furkankoykiran.com.tr/css/main.bundle.<hash>.css" | grep -Ei "^(HTTP|cache-control|cf-cache-status)"

# Machine-readable files at the root
curl -s "https://furkankoykiran.com.tr/ai.txt"
curl -s "https://furkankoykiran.com.tr/.well-known/security.txt"
curl -s "https://furkankoykiran.com.tr/llms.txt"
curl -s "https://blog.furkankoykiran.com.tr/llms.txt"
```

PowerShell equivalents:

```powershell
curl.exe -sI "https://furkankoykiran.com.tr/en/projects/prospectforge/" | Select-String -Pattern "HTTP/|location:|cache-control:"
curl.exe -sI "https://furkankoykiran.com.tr/en/projects/leadwalk/" | Select-String -Pattern "HTTP/|cache-control:|x-content-type-options:|referrer-policy:"
```

Expected results:

- `HTTP/2 301` (or `HTTP/3 301`) and a `location:` pointing at
  `/en/projects/leadwalk/`.
- HTML: `cache-control: public, max-age=0, must-revalidate` and
  `cf-cache-status: BYPASS` (or `DYNAMIC`).
- Fingerprinted CSS/JS: `cf-cache-status: HIT` after the second request and a
  one-year `cache-control`.
- `ai.txt`, `llms.txt`, `llms-full.txt` and `.well-known/security.txt` return
  `200` and `text/plain`.
- No mixed-content or certificate warnings.

---

## 10. Rollback

- Dashboard: disable or delete the individual rule. Rules are independent;
  deleting the redirect rules brings back the Hugo alias fallback.
- Terraform: `terraform destroy` removes the managed rulesets.
- API: `DELETE /zones/$ZONE_ID/rulesets/$RULESET_ID` for a ruleset created by
  these payloads. Do not delete a ruleset that contains unrelated rules.

After a rollback, purge the cache once so browsers and edge nodes stop serving
the old header/redirect response.
