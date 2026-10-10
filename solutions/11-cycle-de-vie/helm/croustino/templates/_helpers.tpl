{{/* Labels communs à tous les objets */}}
{{- define "croustino.labels" -}}
app.kubernetes.io/part-of: croustino
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
croustino/ville: {{ .Values.ville | lower | quote }}
{{- end }}

{{/* Image complète <registre>/<nom>:<tag>. Appel : include "croustino.image" (list $ .Values.back.image) */}}
{{- define "croustino.image" -}}
{{- $racine := index . 0 -}}
{{- $image := index . 1 -}}
{{ $racine.Values.imageRegistry }}/{{ $image.nom }}:{{ $image.tag }}
{{- end }}

{{/* Secrets de pull du registre, s'il y en a */}}
{{- define "croustino.imagePullSecrets" -}}
{{- with .Values.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end }}
