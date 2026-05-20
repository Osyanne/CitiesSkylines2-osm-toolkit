#!/bin/bash
# Resume regeneration after Claude was closed mid-script.
# Wait for in-flight Trondheim extract (PID 27124) to exit, then run Amsterdam.

LOG=/tmp/regen_all.log
echo "" | tee -a "$LOG"
echo "=== [resume $(date '+%H:%M:%S')] Waiting for Trondheim (PID 27124) to finish ===" | tee -a "$LOG"

# Poll every 60s checking if PID 27124 still alive
while kill -0 27124 2>/dev/null; do
  sleep 60
done

echo "=== [resume $(date '+%H:%M:%S')] Trondheim process exited ===" | tee -a "$LOG"
sleep 5  # brief settle

# Verify Trondheim output was actually regenerated (mtime newer than May 19 00:00)
TRONDHEIM_OUT="/c/Users/osyanne/Documents/Claude/Projects/Proyecto mineapolis/cs2-minneapolis-zoning/visualizer/cities/trondheim/datos_zonificacion.js"
TRONDHEIM_MTIME=$(stat -c %Y "$TRONDHEIM_OUT" 2>/dev/null || echo 0)
TODAY_START=$(date -d "2026-05-19 00:00:00" +%s 2>/dev/null || date +%s)

if [ "$TRONDHEIM_MTIME" -gt "$TODAY_START" ]; then
  echo "=== [resume $(date '+%H:%M:%S')] Trondheim output OK (regenerated) ===" | tee -a "$LOG"
else
  echo "=== [resume $(date '+%H:%M:%S')] WARNING: Trondheim output NOT regenerated (mtime=$TRONDHEIM_MTIME) ===" | tee -a "$LOG"
  echo "   Will re-run extract-zoning for trondheim before amsterdam" | tee -a "$LOG"
fi

cd /c/Users/osyanne/Documents/Claude/Projects/Proyecto\ mineapolis/cs2-minneapolis-zoning/src

# Re-run Trondheim only if it didn't produce updated output
if [ "$TRONDHEIM_MTIME" -le "$TODAY_START" ]; then
  echo "" | tee -a "$LOG"
  echo "=== [resume $(date '+%H:%M:%S')] START: trondheim / zoning (retry) ===" | tee -a "$LOG"
  start=$(date +%s)
  if uv run extract-zoning --city trondheim --source pbf >> "$LOG" 2>&1; then
    elapsed=$(( $(date +%s) - start ))
    echo "=== [resume $(date '+%H:%M:%S')] OK: trondheim / zoning (${elapsed}s) ===" | tee -a "$LOG"
  else
    elapsed=$(( $(date +%s) - start ))
    echo "=== [resume $(date '+%H:%M:%S')] FAIL: trondheim / zoning (exit $?, ${elapsed}s) ===" | tee -a "$LOG"
  fi
fi

# Now Amsterdam
echo "" | tee -a "$LOG"
echo "=== [resume $(date '+%H:%M:%S')] START: amsterdam / zoning ===" | tee -a "$LOG"
start=$(date +%s)
if uv run extract-zoning --city amsterdam --source pbf >> "$LOG" 2>&1; then
  elapsed=$(( $(date +%s) - start ))
  echo "=== [resume $(date '+%H:%M:%S')] OK: amsterdam / zoning (${elapsed}s) ===" | tee -a "$LOG"
else
  elapsed=$(( $(date +%s) - start ))
  echo "=== [resume $(date '+%H:%M:%S')] FAIL: amsterdam / zoning (exit $?, ${elapsed}s) ===" | tee -a "$LOG"
fi

echo "" | tee -a "$LOG"
echo "=== [resume $(date '+%H:%M:%S')] ALL REGEN DONE ===" | tee -a "$LOG"
