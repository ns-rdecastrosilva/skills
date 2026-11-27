#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

pattern='netskope|boomskope|nsscloud|stork-|ngweb|webui2|ms-webui|ueba|balkan|atlassian\.net|ENG-[0-9]|rdecastrosilva'

if grep -rInE "$pattern" \
  --exclude-dir=.git \
  --exclude-dir=node_modules \
  --exclude=.git \
  --exclude=denylist.sh \
  .; then
  echo "sanitization gate failed: remove the terms above" >&2
  exit 1
fi

echo "sanitization gate passed"
