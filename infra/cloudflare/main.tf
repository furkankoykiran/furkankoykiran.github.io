locals {
  # Both sites share one Cloudflare zone. Match both hosts explicitly so
  # other subdomains in the zone keep their own cache policy.
  site_hosts = "(http.host eq \"${var.portfolio_host}\" or http.host eq \"${var.blog_host}\")"
}

# ------------------------------------------------------------------- cache ---
# HTML bypasses the edge so a GitHub Pages deploy is visible immediately.
# Fingerprinted CSS/JS/fonts are immutable for a year. Processed images are
# content-addressed, so a month is safe. Sitemap/llms/security files stay
# short-lived for IndexNow and AI crawlers.
resource "cloudflare_ruleset" "cache" {
  zone_id     = var.zone_id
  name        = "Static site cache policy"
  description = "Cache rules for the Hugo portfolio and blog on GitHub Pages"
  kind        = "zone"
  phase       = "http_request_cache_settings"

  rules = [
    {
      ref         = "html_bypass"
      description = "HTML is never edge-cached, so deploys are visible immediately"
      expression  = "(${local.site_hosts} and http.request.method eq \"GET\" and not http.request.uri.path contains \".\")"
      action      = "set_cache_settings"
      action_parameters = {
        cache = false
      }
    },
    {
      ref         = "immutable_build_assets"
      description = "Fingerprinted CSS, JavaScript and fonts: one year at the edge and in the browser"
      expression  = "(${local.site_hosts} and http.request.method eq \"GET\" and http.request.uri.path matches \"^/(css|js|fonts)/\")"
      action      = "set_cache_settings"
      action_parameters = {
        cache = true
        edge_ttl = {
          mode    = "override_origin"
          default = 31536000
        }
        browser_ttl = {
          mode    = "override_origin"
          default = 31536000
        }
      }
    },
    {
      ref         = "images"
      description = "Content-addressed images: one month at the edge and in the browser"
      expression  = "(${local.site_hosts} and http.request.method eq \"GET\" and http.request.uri.path matches \"\\.(avif|webp|png|jpe?g|gif|svg|ico)$\")"
      action      = "set_cache_settings"
      action_parameters = {
        cache = true
        edge_ttl = {
          mode    = "override_origin"
          default = 2592000
        }
        browser_ttl = {
          mode    = "override_origin"
          default = 2592000
        }
      }
    },
    {
      ref         = "machine_readable"
      description = "Sitemap, llms.txt, ai.txt, security.txt and manifest: five minutes"
      expression  = "(${local.site_hosts} and http.request.method eq \"GET\" and http.request.uri.path matches \"\\.(xml|txt|json|webmanifest)$\")"
      action      = "set_cache_settings"
      action_parameters = {
        cache = true
        edge_ttl = {
          mode    = "override_origin"
          default = 300
        }
        browser_ttl = {
          mode    = "override_origin"
          default = 300
        }
      }
    },
  ]
}

# ---------------------------------------------------------------- headers ---
resource "cloudflare_ruleset" "security_headers" {
  zone_id     = var.zone_id
  name        = "Baseline security and freshness headers"
  description = "Headers GitHub Pages cannot set on its own"
  kind        = "zone"
  phase       = "http_response_headers_transform"

  rules = [
    {
      ref         = "baseline_security_headers"
      description = "Baseline headers for both sites"
      expression  = local.site_hosts
      action      = "rewrite"
      action_parameters = {
        headers = {
          "X-Content-Type-Options" = {
            operation = "set"
            value     = "nosniff"
          }
          "Referrer-Policy" = {
            operation = "set"
            value     = "strict-origin-when-cross-origin"
          }
          "Permissions-Policy" = {
            operation = "set"
            value     = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
          }
        }
      }
    },
    {
      ref         = "html_revalidate"
      description = "Browsers revalidate HTML instead of keeping a stale deploy for ten minutes"
      expression  = "(http.response.content_type.media_type eq \"text/html\")"
      action      = "rewrite"
      action_parameters = {
        headers = {
          "Cache-Control" = {
            operation = "set"
            value     = "public, max-age=0, must-revalidate"
          }
        }
      }
    },
  ]
}

# --------------------------------------------------------------- redirects ---
# The Hugo aliases are a meta-refresh fallback. These rules are the real 301
# that search engines see.
resource "cloudflare_ruleset" "legacy_project_redirects" {
  zone_id     = var.zone_id
  name        = "Legacy project redirects"
  description = "ProspectForge was renamed to Leadwalk"
  kind        = "zone"
  phase       = "http_request_dynamic_redirect"

  rules = [
    {
      ref         = "prospectforge_tr"
      description = "Old Turkish ProspectForge URL to Leadwalk"
      expression  = "(http.host eq \"${var.portfolio_host}\" and http.request.uri.path matches \"^/projeler/prospectforge/?$\")"
      action      = "redirect"
      action_parameters = {
        from_value = {
          status_code = 301
          target_url = {
            value = "https://${var.portfolio_host}/projeler/leadwalk/"
          }
          preserve_query_string = true
        }
      }
    },
    {
      ref         = "prospectforge_en"
      description = "Old English ProspectForge URL to Leadwalk"
      expression  = "(http.host eq \"${var.portfolio_host}\" and http.request.uri.path matches \"^/en/projects/prospectforge/?$\")"
      action      = "redirect"
      action_parameters = {
        from_value = {
          status_code = 301
          target_url = {
            value = "https://${var.portfolio_host}/en/projects/leadwalk/"
          }
          preserve_query_string = true
        }
      }
    },
  ]
}
