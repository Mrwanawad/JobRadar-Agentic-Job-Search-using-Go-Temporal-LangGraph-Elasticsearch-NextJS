#!/usr/bin/env sh
# JobRadar daily run for Linux/macOS: fetch, score, draft, export the shortlist, then send what
# is allowed. Schedule with cron, e.g. `crontab -e`:
#   0 9 * * * /path/to/repo/scripts/daily.sh
# Logs to out/logs/YYYY-MM-DD.log.
cd "$(dirname "$0")/.." || exit 1
mkdir -p out/logs
log="out/logs/$(date +%F).log"
export PYTHONIOENCODING=utf-8 PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

step() {
  printf '\n=== %s %s ===\n' "$1" "$(date +%T)" >>"$log"
  shift
  "$@" >>"$log" 2>&1
}

step run uv run jobradar run
step shortlist uv run jobradar top --xlsx out/shortlist.xlsx
# Needs Claude Code with the jobradar plugin and an email MCP; skipped if claude is missing.
if command -v claude >/dev/null; then
  step send claude -p "/jobradar:send-outreach (scheduled run: send without asking)" \
    --permission-mode dontAsk
fi
