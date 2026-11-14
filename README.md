# Xteink X4 Pro — Rescue & CrossPoint Flash Guide

Rescue and flashing toolkit for the **Xteink X4 Pro** e-reader (ESP32-S3, 8 MB flash), plus documentation of two firmware bugs found in the wild and their fixes.

> 🇫🇷 Version française plus bas.

---

## Why this repo exists

Flashing [CrossPoint](https://crosspointreader.com) on an X4 Pro sounds trivial — until every standard method fails. This repo documents a complete rescue path that was verified end-to-end on a real device (Nov 2026), and ships scripts that survive the X4 Pro's flaky USB connection.

### The two bugs this repo fixes

**Bug 1 — The CrossPoint KO full image has a 16 MB partition table on an 8 MB device.**

`CrossPoint-*-x4pro-full.bin` (crosspoint-reader-ko releases) ships a partition table sized for **16 MB** of flash (`app1` at `0x6B0000`, size `0x6A0000`, spiffs/coredump above `0xD50000`). The X4 Pro has **8 MB**. Result: a boot loop the moment you flash it:

```
E (24) flash_parts: partition 3 invalid - offset 0x6b0000 size 0x6a0000
                    exceeds flash chip size 0x800000
E (24) boot: Failed to verify partition table
E (24) boot: load partition table error!
```

**Fix:** a custom 8 MB partition table (`scripts/make-ptable.py`), written once at `0x8000`. See [docs/partition-table.md](docs/partition-table.md).

**Bug 2 — The partition-table MD5 entry magic is `EB EB`, not `EB FF`.**

ESP-IDF's own `gen_esp32part.py` documentation and most references show the MD5 entry as `EB FF + padding`. On this device (ESP-IDF bootloader built without MD5 support in ROM path but app requiring it), the working format — reverse-engineered from the KO image itself — is:

```
ebeb ffff…(14×FF)… <16-byte MD5 of the 32-byte entries>
```

Getting this wrong produces either `partition: No MD5 found in partition table` (app-side assert + reboot loop) or `partition N invalid magic number 0xffeb` (bootloader-side reject). The exact bytes are verified in [docs/partition-table.md](docs/partition-table.md).

### Method comparison (what works, what doesn't)

| Method | Result on X4 Pro (Nov 2026, macOS, firmware 26111201) |
|---|---|
| Xteink Unlocker (OTA hijack) | ❌ `TLS handshake failed: BadCertificate` — stock Licorice firmware pins the update-server certificate since build 26111201 |
| Web flasher (crosspointreader.com) | ❌ `Packet content transfer stopped` after ~0.5–4 % — USB-Serial/JTAG link dies on long transfers |
| esptool, full image in one shot | ❌ Same transfer-stall, consistently |
| **esptool, 256 KB chunks + auto-retry** | ✅ **Works.** ~21 chunks, most pass first try, stragglers retry individually |

The USB-Serial/JTAG flakiness is a known ESP32-S3 + host combination issue: short transfers survive, multi-second ones stall. Chunking turns one long stall-prone transfer into many sub-second transfers.

---

## Quick rescue procedure

Prereqs: macOS/Linux, Python 3, Chrome not required anymore.

```bash
# 1. Firmware + tools
pip install esptool                    # or: python -m venv venv && venv/bin/pip install esptool
curl -L -o x4pro-full.bin \
  https://github.com/crosspoint-reader-ko/crosspoint-reader-ko/releases/download/2.0.0-ko.2/CrossPoint-2.0.0-ko.2-x4pro-full.bin

# 2. Generate the 8 MB partition table sector
python scripts/make-ptable.py ptable.bin

# 3. Connect the X4 Pro over USB-C (data cable!), wake the screen, then:
ESPTOOL=$(which esptool || echo venv/bin/esptool)

#    3a. Flash the corrected partition table at 0x8000
$ESPTOOL --chip esp32s3 --port /dev/cu.usbmodemXXXXXX --baud 460800 \
  --before usb-reset write_flash 0x8000 ptable.bin

#    3b. Flash the full image in 256 KB chunks (auto-resume on failure)
./scripts/flash-chunked.sh 0 x4pro-full.bin

# 4. Unplug USB, hold Power ~3 s. First boot takes ~30 s.
```

`flash-chunked.sh` writes 256 KB slices at their real offsets, verifies each with a hash, retries each slice up to 15×, and prints progress. If it stops, re-run it with the chunk number it printed (e.g. `./scripts/flash-chunked.sh 12 x4pro-full.bin`) — already-written chunks are skipped by starting there.

---

## Diagnosing a boot loop

The X4 Pro exposes a serial console over the same USB port (115200 8N1). Read it while the device loops:

```bash
python scripts/console-listen.py /dev/cu.usbmodemXXXXXX
```

Boot-loop fingerprints and their meanings:

| Console says | Meaning | Fix |
|---|---|---|
| `partition N invalid - offset … exceeds flash chip size 0x800000` | Partition table sized for 16 MB | `make-ptable.py` + write at `0x8000` |
| `No MD5 found in partition table` then `assert failed: esp_ota_get_running_partition` | MD5 entry missing/wrong magic | same table — check `ebeb` magic |
| `partition N invalid magic number 0xffeb` | MD5 entry present but magic misread (`eb ff` instead of `ebeb`) | same table |
| `Installation could not finish / Packet content transfer stopped` | host-side flash stall (web flasher or long esptool run) | chunked script |
| Silence after writing, vendor string becomes `Espressif` | **It booted.** The app re-enumerates USB under Espressif's VID — success. | — |

---

## Repo layout

```
scripts/
  make-ptable.py      # Build the corrected 8 MB partition-table sector
  flash-chunked.sh    # Chunked, resumable, retrying esptool flasher
  console-listen.py   # Serial console reader for boot-loop diagnosis
docs/
  partition-table.md  # Byte-level format of the fixed table + MD5 quirk
  full-story.md       # The complete chronological rescue log
```

## Device facts (X4 Pro)

- SoC: **ESP32-S3** (dual-core 240 MHz, 8 MB PSRAM), flash: **8 MB**
- USB: native USB-Serial/JTAG — enumerates as `XTEink` (stock) / `Espressif` (CrossPoint). **No mass-storage interface ever appears** — the Finder will not show it; that is normal, not a fault.
- Stock firmware: Licorice OS (build `26111201` = 2026-11-12), USB flashing locked only on units from third-party sellers; xteink.com units are unlocked.
- MAC prefix `84:C7:BB` (Espressif), mDNS name `espressif.local` on your LAN.

## Legal

Firmware images belong to their respective projects (CrossPoint, Xteink). This repo contains only original scripts and documentation. MIT license.

## Hard wedge (added 2026-11-14, from the field)

Symptom: screen frozen, console silent, no mDNS, esptool sync fails on every
port/baud/`--before` mode, power/page-button combos (up to 60 s) do nothing,
DTR/RTS patterns do not reset the chip (verified by 50 ms port polling).

Meaning: the CPU is wedged with interrupts off. The power button is only an
interrupt source — a hung CPU never sees it. USB enumerates at descriptor
level, but the app owns the peripheral and never services requests.

What un-wedged it once (not reproducible on demand): a pyserial line-dance
script *crashed* while holding DTR low; the abrupt close coincided with a panic
reboot that landed in ROM download mode (`/dev/cu.usbmodem201101`) — `esptool
flash_id` succeeded. If a ROM port (`201101`) reappears, immediately run with
`--before no-reset --after no-reset` to *stay* in download mode, then flash as
usual.

Reliable recovery without opening: **let the battery drain fully** (LED on =
active drain; gentle warmth ~30-35 C roughly halves the time, 650 mAh ->
12-36 h). When the LED is off: charge 15 min, Power 3 s. If the firmware
re-wedges at boot, reflash (procedure above) as soon as a ROM port appears.
