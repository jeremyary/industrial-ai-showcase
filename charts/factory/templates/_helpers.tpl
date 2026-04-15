{{/*
Expand the name of the chart.
*/}}
{{- define "factory.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fullname: release-name truncated.
*/}}
{{- define "factory.fullname" -}}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Site name (factory-a, factory-b, etc.)
*/}}
{{- define "factory.siteName" -}}
{{ .Values.siteName }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "factory.labels" -}}
helm.sh/chart: {{ include "factory.name" . }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: industrial-ai-showcase
app.kubernetes.io/site: {{ include "factory.siteName" . }}
{{ include "factory.selectorLabels" . }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "factory.selectorLabels" -}}
app.kubernetes.io/name: {{ include "factory.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Image pull secrets.
*/}}
{{- define "factory.imagePullSecrets" -}}
{{- range .Values.imagePullSecrets }}
- name: {{ .name }}
{{- end }}
{{- end }}
