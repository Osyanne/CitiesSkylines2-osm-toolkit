#!/bin/bash
# Regenerate all cities' data files with v3.4.0 PBF + quick-wins format.
# Order: smallest PBF downloads first, so user gets early progress signal.

set -u  # error on undefined vars, but DON'T exit on individual failures

LOG=/tmp/regen_all.log
echo "=== Regeneration started: $(date '+%Y-%m-%d %H:%M:%S') ===" | tee "$LOG"

cd /c/Users/osyanne/Documents/Claude/Projects/Proyecto\ mineapolis/cs2-minneapolis-zoning/src

# Format: "city_slug:module1,module2,..."
# Module map: zoning -> extract-zoning, vial -> extract-vial,
# services -> extract-services, google_buildings -> extract-google-buildings
TASKS=(
  "minneapolis:vial,services"
  "madison:zoning"
  "charleston:zoning"
  "bacau_ro:zoning"
  "mafra_sc_brazil:zoning,google_buildings"
  "trondheim:zoning"
  "amsterdam:zoning"
)

successes=()
failures=()

for entry in "${TASKS[@]}"; do
  city="${entry%%:*}"
  modules="${entry##*:}"
  IFS=',' read -ra MODS <<< "$modules"
  for mod in "${MODS[@]}"; do
    case "$mod" in
      zoning) cmd="uv run extract-zoning --city $city --source pbf" ;;
      vial) cmd="uv run extract-vial --city $city --source pbf" ;;
      services) cmd="uv run extract-services --city $city --source pbf" ;;
      google_buildings) cmd="uv run extract-google-buildings --city $city --source pbf" ;;
      *) echo "[!] Unknown module: $mod for $city, skipping" | tee -a "$LOG"; continue ;;
    esac

    echo "" | tee -a "$LOG"
    echo "=== [$(date '+%H:%M:%S')] START: $city / $mod ===" | tee -a "$LOG"
    echo "    $cmd" | tee -a "$LOG"

    start=$(date +%s)
    if $cmd >> "$LOG" 2>&1; then
      elapsed=$(( $(date +%s) - start ))
      echo "=== [$(date '+%H:%M:%S')] OK: $city / $mod (${elapsed}s) ===" | tee -a "$LOG"
      successes+=("$city/$mod (${elapsed}s)")
    else
      elapsed=$(( $(date +%s) - start ))
      echo "=== [$(date '+%H:%M:%S')] FAIL: $city / $mod (exit $?, ${elapsed}s) ===" | tee -a "$LOG"
      failures+=("$city/$mod (${elapsed}s)")
    fi
  done
done

echo "" | tee -a "$LOG"
echo "=== Regeneration done: $(date '+%Y-%m-%d %H:%M:%S') ===" | tee -a "$LOG"
echo "" | tee -a "$LOG"
echo "SUCCESSES (${#successes[@]}):" | tee -a "$LOG"
for s in "${successes[@]}"; do echo "  + $s" | tee -a "$LOG"; done
echo "" | tee -a "$LOG"
echo "FAILURES (${#failures[@]}):" | tee -a "$LOG"
for f in "${failures[@]}"; do echo "  - $f" | tee -a "$LOG"; done
