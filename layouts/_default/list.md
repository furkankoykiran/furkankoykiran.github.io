---
title: {{ .Title | jsonify }}
url: {{ .Permalink }}
lang: {{ .Language.Lang }}
author: {{ site.Params.author.name }}
---

# {{ .Title }}
{{ with .Params.lead }}
> {{ . }}
{{ end }}
{{ range .RegularPages.ByWeight -}}
{{ $p := .Params.project -}}
- [{{ .Title }}]({{ .Permalink }}index.md): {{ (index $p site.Language.Lang).summary }} ({{ partial "fk/cat-label.html" $p.category | htmlUnescape }}{{ if $p.early }}, {{ i18n "fk.early_title" }}{{ end }}; {{ $p.url }})
{{ end }}
