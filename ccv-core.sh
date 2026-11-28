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

command -v docker >/dev/null 2>&1 \
    || fail "Docker is not available."

# Use only the existing local appliance Docker daemon.
unset DOCKER_CONTEXT
export DOCKER_HOST="unix:///var/run/docker.sock"

[[ -S /var/run/docker.sock ]] \
    || fail "Standard local Docker socket is unavailable."

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

docker image inspect "$CCV_CORE_IMAGE" >/dev/null 2>&1 \
    || fail "Required image is not loaded: $CCV_CORE_IMAGE"

# Prevent ambiguous Docker bind-mount specifications.
case "$DATA_DIR" in
    *','*|*'"'*)
        fail "Unsupported characters in runtime directory path."
        ;;
esac

DOCKER_RUN=(
    docker run
    --rm
    --pull=never
    --network none
    --read-only
    --user 10001:10001
    --cap-drop ALL
    --security-opt no-new-privileges:true
    --tmpfs /tmp:rw,noexec,nosuid,size=16m,mode=1777
    --workdir /data
    --mount "type=bind,source=$DATA_DIR,target=/data"
    --env CCV_ALLOW_INSECURE_TLS_EXCEPTION
    --env CCV_TRUSTED_CA
)

if [[ "$#" -eq 1 ]]; then
    exec "${DOCKER_RUN[@]}" "$CCV_CORE_IMAGE" "$@"
fi

[[ -t 0 && -t 1 ]] \
    || fail "An interactive terminal is required."

exec "${DOCKER_RUN[@]}" -it "$CCV_CORE_IMAGE"
