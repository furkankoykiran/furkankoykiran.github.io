output "cache_ruleset_id" {
  description = "Ruleset ID for the http_request_cache_settings phase."
  value       = cloudflare_ruleset.cache.id
}

output "security_headers_ruleset_id" {
  description = "Ruleset ID for the http_response_headers_transform phase."
  value       = cloudflare_ruleset.security_headers.id
}

output "legacy_redirects_ruleset_id" {
  description = "Ruleset ID for the http_request_dynamic_redirect phase."
  value       = cloudflare_ruleset.legacy_project_redirects.id
}
