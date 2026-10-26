#!/usr/bin/env bash
# Sobe o VagaCerta num cluster kind: cria o cluster, constrói as imagens, carrega no nó e instala o
# chart. Rodar de novo atualiza tudo. Com WITH_ASSISTANT=1, inclui o assistente.
set -euo pipefail
cd "$(dirname "$0")/../.."

images="catalog booking waitlist notification analytics audit mcp-server web keycloak gateway lgtm"
options=()
if [ -n "${WITH_ASSISTANT:-}" ]; then
  images="$images assistant"
  options=(--set workloads.assistant.enabled=true)
fi

kind get clusters | grep -qx vagacerta || kind create cluster --config deploy/kind/cluster.yaml
docker compose build $images
kind load docker-image --name vagacerta $(printf 'vagacerta-%s:latest ' $images)

# As imagens locais mantêm a tag latest: numa atualização, os pods são recriados para usá-las.
installed=$(helm status vagacerta > /dev/null 2>&1 && echo yes || true)
helm upgrade --install vagacerta deploy/helm/vagacerta "${options[@]}" --wait --timeout 15m
if [ -n "$installed" ]; then
  kubectl rollout restart deployment -l app.kubernetes.io/part-of=vagacerta
  kubectl rollout status deployment -l app.kubernetes.io/part-of=vagacerta --timeout 10m
fi
