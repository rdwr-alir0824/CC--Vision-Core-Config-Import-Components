#!/usr/bin/env bash

set -euo pipefail
umask 077

fail() {
    printf 'CCV Core: %s\n' "$*" >&2
    exit 1
}

# Initial offline qualification supports only menu startup and help.
case "$#" in
    0)
        ;;
    1)
        case "$1" in
            --help|-h)
                ;;
            --allow-live)
                fail "Live execution is not enabled in this deployment."
                ;;
            *)
                fail "Unsupported argument: $1"
                ;;
        esac
        ;;
    *)
        fail "Unsupported arguments."
        ;;
esac

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

cd -- "$APP_DIR"

[[ -f "$APP_DIR/compose.yaml" ]] \
    || fail "compose.yaml not found."

command -v docker >/dev/null 2>&1 \
    || fail "Docker is not available."

docker compose version >/dev/null 2>&1 \
    || fail "Docker Compose is not available."

docker info >/dev/null 2>&1 \
    || fail "Cannot access the Docker daemon."

export CCV_CORE_IMAGE="${CCV_CORE_IMAGE:-ccv-core:0.1.0}"

DATA_DIR="${CCV_CORE_DATA_DIR:-../ccv-runtime/core}"

[[ -d "$DATA_DIR" ]] \
    || fail "Runtime data directory does not exist: $DATA_DIR"

DATA_DIR="$(cd -- "$DATA_DIR" && pwd -P)"

case "$DATA_DIR" in
    "$APP_DIR"|"$APP_DIR"/*)
        fail "Runtime data must be stored outside the application directory."
        ;;
esac

DATA_ATTRIBUTES="$(stat -c '%u:%g:%a' -- "$DATA_DIR")"

[[ "$DATA_ATTRIBUTES" == "10001:10001:700" ]] \
    || fail "Runtime directory requires ownership 10001:10001 and mode 700."

export CCV_CORE_DATA_DIR="$DATA_DIR"
export CCV_ALLOW_INSECURE_TLS_EXCEPTION="${CCV_ALLOW_INSECURE_TLS_EXCEPTION:-false}"
export CCV_TRUSTED_CA="${CCV_TRUSTED_CA:-}"
export COMPOSE_PROFILES=core

docker image inspect "$CCV_CORE_IMAGE" >/dev/null 2>&1 \
    || fail "Required image is not loaded: $CCV_CORE_IMAGE"

COMPOSE=(
    docker compose
    --project-directory "$APP_DIR"
    --env-file /dev/null
    --project-name ccv-core
    --file "$APP_DIR/compose.yaml"
    --profile core
)

if [[ "$#" -eq 1 ]]; then
    exec "${COMPOSE[@]}" run --rm --no-deps -T ccv-core "$@"
fi

[[ -t 0 && -t 1 ]] \
    || fail "An interactive terminal is required."

exec "${COMPOSE[@]}" run --rm --no-deps ccv-core
