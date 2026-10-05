{{/*
Chart name.
*/}}
{{- define "kantyna.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name. If the release name already contains the chart
name it is used as-is (release "kantyna" -> "kantyna").
*/}}
{{- define "kantyna.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "kantyna.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Component resource name: <fullname>-<component>.
Usage: include "kantyna.componentName" (dict "ctx" $ "component" "orders-api")
*/}}
{{- define "kantyna.componentName" -}}
{{- printf "%s-%s" (include "kantyna.fullname" .ctx) .component | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Selector labels for a component.
*/}}
{{- define "kantyna.selectorLabels" -}}
app.kubernetes.io/name: {{ .component }}
app.kubernetes.io/instance: {{ .ctx.Release.Name }}
{{- end }}

{{/*
Common labels for a component.
*/}}
{{- define "kantyna.labels" -}}
helm.sh/chart: {{ include "kantyna.chart" .ctx }}
{{ include "kantyna.selectorLabels" . }}
app.kubernetes.io/component: {{ .component }}
app.kubernetes.io/part-of: kantyna
app.kubernetes.io/managed-by: {{ .ctx.Release.Service }}
{{- with .version }}
app.kubernetes.io/version: {{ . | quote }}
{{- end }}
{{- end }}

{{/*
Effective image tag: global.imageTag overrides the per-service tag unless pinTag is set.
*/}}
{{- define "kantyna.imageTag" -}}
{{- $tag := .image.tag -}}
{{- if not .image.pinTag -}}
{{- $tag = default .image.tag .ctx.Values.global.imageTag -}}
{{- end -}}
{{- toString $tag -}}
{{- end }}

{{/*
Full image reference.
Usage: include "kantyna.image" (dict "ctx" $ "image" .Values.ordersApi.image)
*/}}
{{- define "kantyna.image" -}}
{{- $registry := default .ctx.Values.global.imageRegistry .image.registry -}}
{{- $tag := include "kantyna.imageTag" . -}}
{{- if $registry -}}
{{- printf "%s/%s:%s" $registry .image.repository (toString $tag) -}}
{{- else -}}
{{- printf "%s:%s" .image.repository (toString $tag) -}}
{{- end -}}
{{- end }}

{{/*
Pod security context: global defaults overridden per service.
Usage: include "kantyna.podSecurityContext" (dict "ctx" $ "svc" .Values.ordersApi)
*/}}
{{- define "kantyna.podSecurityContext" -}}
{{- $base := deepCopy .ctx.Values.global.podSecurityContext -}}
{{- $override := default (dict) .svc.podSecurityContext -}}
{{- toYaml (mustMergeOverwrite $base (deepCopy $override)) -}}
{{- end }}

{{- define "kantyna.containerSecurityContext" -}}
{{- $base := deepCopy .ctx.Values.global.containerSecurityContext -}}
{{- $override := default (dict) .svc.containerSecurityContext -}}
{{- toYaml (mustMergeOverwrite $base (deepCopy $override)) -}}
{{- end }}

{{/*
Scheduling + pull secrets shared by all pods.
*/}}
{{- define "kantyna.podScheduling" -}}
{{- with .Values.global.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.global.nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.global.tolerations }}
tolerations:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.global.affinity }}
affinity:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end }}

{{/*
Environment shared by application containers.
Usage: include "kantyna.commonEnv" (dict "ctx" $ "component" "orders-api" "svc" .Values.ordersApi)
*/}}
{{- define "kantyna.commonEnv" -}}
{{- $g := .ctx.Values.global -}}
{{- $version := include "kantyna.imageTag" (dict "ctx" .ctx "image" .svc.image) -}}
{{- $attrs := printf "service.namespace=kantyna,service.version=%s,deployment.environment=%s,k8s.namespace.name=%s" $version $g.environment .ctx.Release.Namespace -}}
{{- if $g.appVariant -}}
{{- $attrs = printf "%s,app.variant=%s" $attrs $g.appVariant -}}
{{- end -}}
{{- if $g.otel.extraResourceAttributes -}}
{{- $attrs = printf "%s,%s" $attrs $g.otel.extraResourceAttributes -}}
{{- end -}}
- name: AWS_REGION
  value: {{ $g.awsRegion | quote }}
- name: QUEUE_URL
  value: {{ $g.queueUrl | quote }}
- name: RECEIPTS_BUCKET
  value: {{ $g.receiptsBucket | quote }}
- name: OTEL_EXPORTER_OTLP_ENDPOINT
  value: {{ $g.otel.exporterOtlpEndpoint | quote }}
- name: OTEL_SERVICE_NAME
  value: {{ .component | quote }}
- name: POD_NAME
  valueFrom:
    fieldRef:
      fieldPath: metadata.name
- name: OTEL_RESOURCE_ATTRIBUTES
  value: {{ printf "%s,k8s.pod.name=$(POD_NAME)" $attrs | quote }}
- name: APP_VERSION
  value: {{ $version | quote }}
{{- if $g.appVariant }}
- name: APP_VARIANT
  value: {{ $g.appVariant | quote }}
{{- end }}
- name: LOG_LEVEL
  value: {{ $g.logLevel | quote }}
- name: FLAGS_FILE
  value: /etc/kantyna/flags/flags.json
{{- end }}

{{/*
ServiceAccount name for a component.
*/}}
{{- define "kantyna.serviceAccountName" -}}
{{- include "kantyna.componentName" . }}
{{- end }}

{{/*
Name of the DB secret.
*/}}
{{- define "kantyna.dbSecretName" -}}
{{- include "kantyna.componentName" (dict "ctx" . "component" "db") }}
{{- end }}

{{/*
Name of the flags ConfigMap.
*/}}
{{- define "kantyna.flagsConfigMapName" -}}
{{- include "kantyna.componentName" (dict "ctx" . "component" "flags") }}
{{- end }}
