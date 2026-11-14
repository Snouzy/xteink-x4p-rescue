#!/usr/bin/env python3
"""jtag-fix-ptable.py — réécrit la table de partitions 8 Mo via JTAG (OpenOCD esp32).

Usage: ./jtag-fix-ptable.py [chemin/vers/openocd-esp32]

Prérequis: openocd-esp32 d'Espressif (le vanilla échoue sur le composite CDC+JTAG),
lanceur: ce script démarre openocd lui-même, écrit ptable.bin à 0x8000, vérifie,
reset, puis tue openocd. Utilisé quand la puce boot-loope sur
"partition 3 invalid - exceeds flash chip size 0x800000"."""
import os, socket, subprocess, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPENOCD = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/dev/openocd-esp32/bin/openocd")
SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(OPENOCD)), "share/openocd/scripts")
if not os.path.isdir(SCRIPTS):
    SCRIPTS = os.path.expanduser("~/dev/openocd-esp32/share/openocd/scripts")
PTABLE = os.path.join(REPO, "ptable.bin")

ocd = subprocess.Popen(
    [OPENOCD, "-s", SCRIPTS, "-f", "interface/esp_usb_jtag.cfg",
     "-f", "target/esp32s3.cfg", "-c", "adapter speed 200"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(30):
        try:
            s = socket.create_connection(("localhost", 4444), timeout=2); break
        except OSError:
            time.sleep(1)
    else:
        sys.exit("openocd ne répond pas sur 4444")
    def cmd(c, wait):
        s.sendall(c.encode() + b"\r\n"); time.sleep(wait)
        s.setblocking(False); out = b""
        try:
            while True:
                d = s.recv(65536)
                if not d: break
                out += d
        except BlockingIOError:
            pass
        s.setblocking(True)
        print(f">>> {c}\n{out.decode('utf-8','replace')[-400:]}")
    cmd("reset halt", 5)
    cmd(f"program_esp {PTABLE} 0x8000 verify reset", 60)
    print("OK — table réécrite. Laisse la liseuse rebooter (~30 s).")
finally:
    ocd.terminate()
