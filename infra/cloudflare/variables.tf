variable "zone_id" {
  description = "Cloudflare zone ID for furkankoykiran.com.tr (the blog is a subdomain of the same zone)."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{32}$", var.zone_id))
    error_message = "zone_id must be the 32-character hexadecimal zone ID from the Cloudflare dashboard."
  }
}

variable "portfolio_host" {
  description = "Apex hostname of the portfolio site."
  type        = string
  default     = "furkankoykiran.com.tr"

  validation {
    condition     = can(regex("^[a-z0-9.-]+$", var.portfolio_host))
    error_message = "portfolio_host must be a lowercase hostname without a scheme or path."
  }
}

variable "blog_host" {
  description = "Hostname of the blog."
  type        = string
  default     = "blog.furkankoykiran.com.tr"

  validation {
    condition     = can(regex("^[a-z0-9.-]+$", var.blog_host))
    error_message = "blog_host must be a lowercase hostname without a scheme or path."
  }
}
