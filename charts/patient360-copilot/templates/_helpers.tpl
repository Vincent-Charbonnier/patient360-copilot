{{/*
Expand the name of the chart.
*/}}
{{- define "patient360-copilot.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "patient360-copilot.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "patient360-copilot.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "patient360-copilot.labels" -}}
helm.sh/chart: {{ include "patient360-copilot.chart" . }}
{{ include "patient360-copilot.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "patient360-copilot.selectorLabels" -}}
app.kubernetes.io/name: {{ include "patient360-copilot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name.
*/}}
{{- define "patient360-copilot.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "patient360-copilot.fullname" .) .Values.serviceAccount.name }}
{{- else -}}
{{- default "default" .Values.serviceAccount.name }}
{{- end -}}
{{- end }}

{{/*
Generated app secret name.
*/}}
{{- define "patient360-copilot.generatedSecretName" -}}
{{- printf "%s-llm" (include "patient360-copilot.fullname" .) -}}
{{- end }}

{{/*
LLM secret name.
*/}}
{{- define "patient360-copilot.secretName" -}}
{{- if .Values.llm.existingSecret -}}
{{- .Values.llm.existingSecret -}}
{{- else -}}
{{- include "patient360-copilot.generatedSecretName" . -}}
{{- end -}}
{{- end }}

{{/*
Embedding secret name.
*/}}
{{- define "patient360-copilot.embeddingSecretName" -}}
{{- if .Values.embedding.existingSecret -}}
{{- .Values.embedding.existingSecret -}}
{{- else -}}
{{- include "patient360-copilot.generatedSecretName" . -}}
{{- end -}}
{{- end }}
