{{/*
Common labels
*/}}
{{- define "mlops.labels" -}}
app.kubernetes.io/managed-by: Helm
app.kubernetes.io/part-of: industrial-ai-showcase
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/*
GPU tolerations
*/}}
{{- define "mlops.gpuTolerations" -}}
{{- range .Values.gpu.tolerations }}
- key: {{ .key }}
  operator: {{ .operator }}
  effect: {{ .effect }}
{{- end }}
{{- end }}

{{/*
GPU node selector
*/}}
{{- define "mlops.gpuNodeSelector" -}}
nvidia.com/gpu.product: {{ .Values.gpu.product }}
{{- end }}
