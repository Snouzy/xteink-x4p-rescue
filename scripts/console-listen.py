#!/usr/bin/env python3
"""console-listen.py — read the X4 Pro serial console for boot-loop diagnosis.

Usage:
  python console-listen.py /dev/cu.usbmodemXXXXXX

Prints up to ~2 boot cycles and interprets the most common failure
signatures. Exits silently on an app that has taken over the port
(a success sign on this device).
"""
import sys
import time

try:
    import serial
except ImportError:
    sys.exit("pip install pyserial")

p = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.usbmodem201101"

try:
    s = serial.Serial(p, 115200, timeout=1)
except Exception as e:
    sys.exit(f"port unavailable: {e}")

print(f"listening on {p} for 45 s ...", flush=True)
end = time.time() + 45
chunks = []
while time.time() < end:
    try:
        d = s.read(4096)
    except Exception:
        print("\nport vanished mid-read — the app likely booted and "
              "re-enumerated USB (success).")
        sys.exit(0)
    if d:
        chunks.append(d.decode("utf-8", errors="replace"))
s.close()
txt = "".join(chunks)

lines = txt.splitlines()
uniq = []
for ln in lines:
    if "ESP-ROM" in ln and any("ESP-ROM" in u for u in uniq[-30:]):
        break
    uniq.append(ln)
shown = "\n".join(uniq[-40:]) if uniq else ""

if not shown.strip():
    print("total silence — if the screen changed, the device booted.")
elif "exceeds flash chip size" in shown:
    print(">> partition table sized for 16 MB flash — use make-ptable.py")
elif "No MD5 found in partition table" in shown:
    print(">> MD5 trailer missing/malformed — use make-ptable.py (ebeb magic)")
elif "invalid magic number 0xffeb" in shown:
    print(">> MD5 magic is eb ff; this device wants eb eb — use make-ptable.py")
else:
    print(shown)
