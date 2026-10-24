---
title: {{ .Title | jsonify }}
url: {{ .Permalink }}
lang: {{ .Language.Lang }}
{{ if not .Lastmod.IsZero }}lastmod: {{ .Lastmod.Format "2006-01-02" }}{{ end }}
author: {{ site.Params.author.name }}
---

# {{ .Title }}
{{ with .Params.lead }}
> {{ . }}
{{ end }}
{{ with .Params.project -}}
{{ partial "fk/md-project.html" . | htmlUnescape }}
{{- else -}}
{{ partial "fk/md-clean.html" . | htmlUnescape }}
{{- end }}
{{ if eq .Layout "contributions" }}
{{ partial "fk/md-contributions.html" . | htmlUnescape }}
{{ end }}
