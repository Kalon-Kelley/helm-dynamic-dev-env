#!/bin/bash

POSITIONAL_ARGS=()
REBUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--rebuild)
            REBUILD=true
            shift
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

if [ ! -d "/helm-src" ]; then
    echo "Helm source not mounted or incorrect file mounted"
    exit 1
fi

original_dir="$(pwd)"
if [ "$REBUILD" = true ]; then
    cd /helm-src
    make clean && make
    if [ $? -ne 0 ]; then
        echo "Failed to build source"
        exit 1
    fi
    cd "$original_dir"
fi

k3s server --disable traefik > /log/k3s.log 2>&1 &
exec bash
