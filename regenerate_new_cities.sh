#!/bin/bash
# Regenerate the 2 new city-request cities: fayetteville_nc + sacramento
# NC PBF ~200MB, CA PBF ~600MB (both should fit in available RAM, unlike Norway 1.3GB).

LOG=/tmp/regen_new_cities.log
echo "=== New cities regen started: $(date '+%Y-%m-%d %H:%M:%S') ===" | tee "$LOG"

cd /c/Users/osyanne/Documents/Claude/Projects/Proyecto\ mineapolis/cs2-minneapolis-zoning/src

TASKS=(
  "fayetteville_nc"
  "sacramento"
)

successes=()
failures=()

for city in "${TASKS[@]}"; do
  echo "" | tee -a "$LOG"
  echo "=== [$(date '+%H:%M:%S')] START: $city / zoning ===" | tee -a "$LOG"
  start=$(date +%s)
  if uv run extract-zoning --city "$city" --source pbf >> "$LOG" 2>&1; then
    elapsed=$(( $(date +%s) - start ))
    echo "=== [$(date '+%H:%M:%S')] OK: $city / zoning (${elapsed}s) ===" | tee -a "$LOG"
    successes+=("$city (${elapsed}s)")
  else
    elapsed=$(( $(date +%s) - start ))
    echo "=== [$(date '+%H:%M:%S')] FAIL: $city / zoning (exit $?, ${elapsed}s) ===" | tee -a "$LOG"
    failures+=("$city (${elapsed}s)")
  fi
done

echo "" | tee -a "$LOG"
echo "=== DONE: $(date '+%Y-%m-%d %H:%M:%S') ===" | tee -a "$LOG"
echo "SUCCESSES (${#successes[@]}):" | tee -a "$LOG"
for s in "${successes[@]}"; do echo "  + $s" | tee -a "$LOG"; done
echo "FAILURES (${#failures[@]}):" | tee -a "$LOG"
for f in "${failures[@]}"; do echo "  - $f" | tee -a "$LOG"; done
