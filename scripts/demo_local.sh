#!/usr/bin/env bash
set -euo pipefail

HOST="${AERORAGX_DEMO_HOST:-127.0.0.1}"
PORT="${AERORAGX_DEMO_PORT:-8001}"
MAX_WAIT_SECONDS="${AERORAGX_DEMO_MAX_WAIT_SECONDS:-120}"
PYTHON_BIN="${AERORAGX_PYTHON_BIN:-python3}"
BASE_URL="http://${HOST}:${PORT}"
LOG_FILE="$(mktemp "${TMPDIR:-/tmp}/aeroragx-demo.XXXXXX")"
SERVER_PID=""

cleanup() {
  if [ -n "${SERVER_PID}" ] && kill -0 "${SERVER_PID}" 2>/dev/null; then
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi

  rm -f "${LOG_FILE}"
}

trap cleanup EXIT INT TERM

if ! "${PYTHON_BIN}" -c "import uvicorn" >/dev/null 2>&1; then
  echo "${PYTHON_BIN} cannot import uvicorn. Install the project dependencies or set AERORAGX_PYTHON_BIN." >&2
  exit 2
fi

unset OPENAI_API_KEY
export AERORAGX_RUNTIME_MODE=local
export AERORAGX_CANDIDATE_TOP_K="${AERORAGX_CANDIDATE_TOP_K:-20}"
export AERORAGX_EVIDENCE_TOP_K="${AERORAGX_EVIDENCE_TOP_K:-5}"

echo "Starting AeroRAG-X local demo at ${BASE_URL}..."

"${PYTHON_BIN}" -m uvicorn aeroragx.api:app \
  --host "${HOST}" \
  --port "${PORT}" \
  >"${LOG_FILE}" 2>&1 &

SERVER_PID="$!"

ready=false

for ((attempt = 1; attempt <= MAX_WAIT_SECONDS; attempt++)); do
  if curl --silent --show-error --fail "${BASE_URL}/ready" >/dev/null 2>&1; then
    ready=true
    break
  fi

  sleep 1
done

if [ "${ready}" != "true" ]; then
  echo "The local API did not become ready within ${MAX_WAIT_SECONDS} seconds." >&2
  echo "Server log:" >&2
  sed -n '1,180p' "${LOG_FILE}" >&2
  exit 1
fi

echo
echo "Health check:"
curl --silent --show-error --fail "${BASE_URL}/health" | "${PYTHON_BIN}" -m json.tool

echo
echo "Readiness check:"
curl --silent --show-error --fail "${BASE_URL}/ready" | "${PYTHON_BIN}" -m json.tool

echo
echo "Grounded-query demonstration:"
RESPONSE_FILE="$(mktemp "${TMPDIR:-/tmp}/aeroragx-response.XXXXXX")"
curl --silent --show-error --fail \
  -X POST "${BASE_URL}/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query":"How can battery thermal runaway propagate in electric aircraft?"}' \
  >"${RESPONSE_FILE}"
"${PYTHON_BIN}" -m json.tool <"${RESPONSE_FILE}"

echo
echo "Response-contract check:"
"${PYTHON_BIN}" scripts/verify_demo_response.py --response "${RESPONSE_FILE}"
rm -f "${RESPONSE_FILE}"

echo
echo "Demo completed successfully."
