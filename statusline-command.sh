#!/bin/bash
input=$(cat)
cwd=$(echo "$input" | jq -r '.cwd // .workspace.current_dir // "?"')
model=$(echo "$input" | jq -r '.model.display_name // "Unknown"')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
remaining_pct=$(echo "$input" | jq -r '.context_window.remaining_percentage // empty')

# Shorten home directory to ~
home_dir="$HOME"
cwd_display="${cwd/#$home_dir/\~}"

if [ -n "$used_pct" ] && [ -n "$remaining_pct" ]; then
  printf "%s | %s | ctx: %.0f%% used (%.0f%% left)" "$cwd_display" "$model" "$used_pct" "$remaining_pct"
elif [ -n "$used_pct" ]; then
  printf "%s | %s | ctx: %.0f%% used" "$cwd_display" "$model" "$used_pct"
else
  printf "%s | %s" "$cwd_display" "$model"
fi
