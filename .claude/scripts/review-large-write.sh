#!/usr/bin/env bash
# PostToolUse hook (Write|Edit): launches a sub-claude code review for
# "large" writes and feeds the review back to the parent session.
#
# Trigger criteria ("large"):
#   - Write tool: ALWAYS counts as large (whole-file write)
#   - Edit tool:  new_string has > 30 lines OR > 1500 characters
#   - Anything else: silently exit 0
#
# Behavior:
#   - Reviewer (claude -p, Haiku) returns "OK" or a bullet list of issues
#   - "OK" / empty → exit 0 (silent)
#   - Issues       → printed to stderr, exit 2 (parent Claude sees feedback)
#
# Hook input is read as JSON from stdin (see settings.json schema).

set -u

LINE_THRESHOLD=30
CHAR_THRESHOLD=1500
PROMPT_TRUNCATE=4000

input=$(cat)
tool=$(printf '%s' "$input" | jq -r '.tool_name // ""')
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // ""')

[ -z "$file" ] && exit 0
[ ! -f "$file" ] && exit 0

case "$tool" in
  Write)
    diff_content=$(printf '%s' "$input" | jq -r '.tool_input.content // ""')
    ;;
  Edit)
    diff_content=$(printf '%s' "$input" | jq -r '.tool_input.new_string // ""')
    line_count=$(printf '%s' "$diff_content" | awk 'END {print NR}')
    char_count=${#diff_content}
    if [ "${line_count:-0}" -le "$LINE_THRESHOLD" ] \
       && [ "${char_count:-0}" -le "$CHAR_THRESHOLD" ]; then
      exit 0
    fi
    ;;
  *)
    exit 0
    ;;
esac

# Sub-claude reviewer — Haiku for speed/cost
truncated=$(printf '%s' "$diff_content" | head -c "$PROMPT_TRUNCATE")
prompt="Review the following file for code quality, unused code, dead branches, missing edge cases, and deviations from the project's CLAUDE.md conventions. Respond with a concise bullet list of issues, or 'OK' if nothing.

File: $file

Last change:
$truncated"

review=$(claude -p --model claude-haiku-4-5-20251001 "$prompt" 2>/dev/null) || exit 0

# Trim whitespace-only lines and check for "OK"
trimmed=$(printf '%s' "$review" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g' | sed '/^$/d')
if [ -z "$trimmed" ] || [ "$trimmed" = "OK" ]; then
  exit 0
fi

echo "$trimmed" >&2
exit 2
