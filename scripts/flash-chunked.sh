#!/usr/bin/env bash
# flash-chunked.sh — chunked, resumable, retrying flasher for the Xteink X4 Pro.
#
# The ESP32-S3 USB-Serial/JTAG link on this device stalls on long transfers
# ("Packet content transfer stopped" / "No more data to read"). Writing in
# 256 KB slices with per-slice retries works around it.
#
# Usage:
#   ./flash-chunked.sh [START_CHUNK] [FIRMWARE.bin]
#
#   START_CHUNK   0 on first run. If the script abandons at chunk N, re-run
#                 with N to resume (chunks < N are already written).
#   FIRMWARE      Path to a *full* image (bootloader+partitions+app).
#
# Needs: esptool (pip install esptool), a data-capable USB-C cable, the
# device awake and plugged in.
set -u

FW="${2:-x4pro-full.bin}"
CHUNK=262144
START="${1:-0}"
ESPTOOL="${ESPTOOL:-esptool}"
LOG="${LOG:-flash-chunked.log}"
MAX_TRIES=15

SIZE=$(stat -f%z "$FW" 2>/dev/null || stat -c%s "$FW")
N=$(( (SIZE + CHUNK - 1) / CHUNK ))
echo "$(date '+%H:%M:%S') === flash $FW : chunks $START..$((N-1)) of $N ($SIZE bytes) ===" | tee -a "$LOG"

for (( i=START; i<N; i++ )); do
  OFF=$((i * CHUNK))
  PART="$(mktemp /tmp/fwchunk.XXXXXX.bin)"
  dd if="$FW" of="$PART" bs=$CHUNK skip=$i count=1 2>/dev/null
  OK=0
  for (( try=1; try<=MAX_TRIES; try++ )); do
    PORT=""
    for (( w=0; w<15; w++ )); do
      PORT=$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)
      [ -n "$PORT" ] && break
      sleep 2
    done
    if [ -z "$PORT" ]; then
      echo "$(date '+%H:%M:%S') chunk $i: no port, waiting" >> "$LOG"
      sleep 5
      continue
    fi
    HEXOFF=$(printf '0x%x' "$OFF")
    echo "$(date '+%H:%M:%S') chunk $i/$N @ $HEXOFF try $try" >> "$LOG"
    "$ESPTOOL" --chip esp32s3 --port "$PORT" --baud 460800 \
      --before usb-reset --after no-reset \
      write_flash --flash-size 8MB "$HEXOFF" "$PART" >> "$LOG" 2>&1
    if [ $? -eq 0 ]; then OK=1; break; fi
    echo "$(date '+%H:%M:%S') chunk $i failed (try $try)" >> "$LOG"
    sleep 3
  done
  rm -f "$PART"
  if [ "$OK" -ne 1 ]; then
    echo "$(date '+%H:%M:%S') ABANDON at chunk $i — resume with: $0 $i \"$FW\"" | tee -a "$LOG"
    exit 1
  fi
  echo "$(date '+%H:%M:%S') chunk $i OK ($(( (i+1)*100/N ))%)" | tee -a "$LOG"
done
echo "$(date '+%H:%M:%S') === FLASH COMPLETE — unplug USB, hold Power ~3 s ===" | tee -a "$LOG"
