#!/usr/bin/env bash

usage() {
  cat <<'USAGE'
Usage: hello.sh [NAME]

Print a greeting with today's date.

Arguments:
  NAME    Name to greet (default: World)

Options:
  -h, --help    Show this help message and exit
USAGE
}

case "${1:-}" in
  -h|--help)
    usage
    exit 0
    ;;
esac

name="${1:-World}"
echo "Hello, ${name}! Today is $(date +%Y-%m-%d)."
