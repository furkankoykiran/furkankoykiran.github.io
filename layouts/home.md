{{- $isTR := eq site.Language.Lang "tr" -}}
---
title: {{ site.Title | jsonify }}
url: {{ .Permalink }}
lang: {{ .Language.Lang }}
author: {{ site.Params.author.name }}
---

# {{ site.Params.author.name }}

> {{ i18n "fk.hero_lead" }}

{{ i18n "fk.status" }}.

{{ i18n "fk.hero_body" }}

## {{ i18n "fk.build_title" }}

- **{{ i18n "fk.focus_mcp_title" }}**: {{ i18n "fk.focus_mcp_body" }}
- **{{ i18n "fk.focus_dev_title" }}**: {{ i18n "fk.focus_dev_body" }}
- **{{ i18n "fk.focus_py_title" }}**: {{ i18n "fk.focus_py_body" }}
- **{{ i18n "fk.focus_oss_title" }}**: {{ i18n "fk.focus_oss_body" }}

## {{ i18n "fk.featured_title" }}
{{ range sort (where hugo.Data.projects.projects "featured" true) "featured_rank" }}
{{- with site.GetPage (printf "/projeler/%s" .slug) }}
- [{{ .Title }}]({{ .Permalink }}): {{ .Params.description }}
{{- end }}
{{- end }}

## {{ i18n "fk.oss_title" }}
{{ range where hugo.Data.contributions.repos "highlight" true }}
- [{{ .repo }}]({{ .url }}) ({{ .stars }} ★): {{ range $i, $p := .prs }}{{ if $i }}; {{ end }}[{{ .title }}]({{ .url }}){{ end }}
{{- end }}

## {{ i18n "fk.contact_title" }}

- {{ i18n "fk.email_label" }}: {{ i18n "fk.email_fallback" }}
{{ range site.Params.social }}- [{{ .name }}]({{ .url }})
{{ end }}- Blog: {{ cond $isTR site.Params.blog.url site.Params.blog.urlEN }}
