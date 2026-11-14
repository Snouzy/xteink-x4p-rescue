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

#    3a. Flash the full image in 256 KB chunks (auto-resume on failure)
./scripts/flash-chunked.sh 0 x4pro-full.bin
#
#    ⚠ ORDRE IMPORTANT (brûlé le 2026-11-14) : l'image "full" contient la
#    table 16 Mo cassée à 0x8000. Si on écrit ptable.bin AVANT, le flash
#    chunké (offset 0) RE-écrase la table corrigée avec la cassée.
#    La table corrigée doit donc partir EN DERNIER :

#    3b. Flash the corrected partition table at 0x8000 (après l'image !)
$ESPTOOL --chip esp32s3 --port /dev/cu.usbmodemXXXXXX --baud 460800 \
  --before no-reset --after hard_reset write_flash 0x8000 ptable.bin

#    3c. Si le flash s'est terminé en mode download (--after no-reset),
#    le bouton Power ne fait RIEN en mode ROM. Le hard_reset d'esptool
#    (3b) est le déclencheur de boot. Sinon: débrancher 10 s + Power 3 s.

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

## Session 2 field report (2026-11-14) : hard wedge → résurrection JTAG

Pire cas observé : écran figé (e-ink figé sur l'ancienne image), console muette,
aucun esptool (tous bauds/modes), aucun combo boutons (Power/pages, 60 s),
DTR/RTS **inertes** (vérifié par polling 50 ms — pas de circuit auto-reset sur ce
hardware), pas de mDNS. La puce est bloquée avec les interruptions coupées :
aucun signal logiciel ne la réveille. Le drain de batterie reste le plan de
secours, mais AVANT d'attendre 36 h, la séquence suivante a tout débloqué :

### Étape 1 — L'orage d'ouvertures (open-storm) : forcer un reboot

L'app plantée crash quand on ouvre son port USB (événement qu'elle ne sait plus
traiter → panic → reboot). `scripts/open-storm.py` ouvre/ferme le port en boucle
(bauds et DTR/RTS aléatoires) jusqu'à obtenir la fenêtre ROM :
le port réapparaît alors comme **`/dev/cu.usbmodem201101`** (nom par défaut du
ROM ; l'app, elle, énumère `usbmodem84C7BB7AB2042`). Environ 4 s la première fois.
Attraper le mode download : `esptool --before no-reset --after no-reset flash_id`
(le `--after no-reset` EST le secret : sinon esptool hard-reset la puce à la fin
et on perd la fenêtre).

### Étape 2 — Flash chunké, PUIS table (ordre !)

`./scripts/flash-chunked.sh 0 <image-full.bin>` (le script auto-détecte le port ;
21 chunks de 256 Ko, ~45 s). La puce reste en download mode à la fin
(`--after no-reset`). Ne PAS compter sur le bouton Power : réécrire la table
corrigée avec `--after hard_reset` (voir Quick rescue 3b).

### Étape 3 — Si boot-loop "partition 3 invalid" : JTAG

Si le boot affiche en boucle `partition 3 invalid - offset 0x6b0000 … exceeds
flash chip size 0x800000`, c'est la table 16 Mo d'origine à 0x8000 (Étape 2 mal
ordonnée, ou flash ancien). Deux remarques clés :

- La console de boot **parle sur l'USB-JTAG à 115200** (pyserial, port 201101) :
  on lit le diagnostic directement.
- **Le mode download n'est PAS nécessaire pour réécrire le flash.** Le JTAG est
  actif même en boot-loop. Mais OpenOCD *vanilla* échoue
  (`esp_usb_jtag: could not find or open device`) car le composite CDC+JTAG a
  l'interface JTAG en **position 2** (class 0xFF). Utiliser **openocd-esp32
  d'Espressif** (prebuilt macOS-arm64 :
  https://github.com/espressif/openocd-esp32/releases). pyusb ouvre le device
  sans sudo ; lancer openocd-esp32 sans sudo suffit.

```bash
./scripts/jtag-fix-ptable.py [chemin/openocd-esp32/bin/openocd]
# halt → program_esp ptable.bin 0x8000 verify reset (~25 s)
```

Le reset final fait démarrer l'app (logs mémoire `[INF] [MEM]…` sur la console
= succès ; l'écran e-ink se rafraîchit au boot).

### Faits techniques nouveaux (session 2)

- Le flash bank est détecté **16 Mo** par esptool/JTAG, mais le ROM bootlog dit
  `flash chip size 0x800000` (8 Mo) — probable eFuse. La table 8 Mo reste la
  bonne ; boot validé deux fois (12/11 et 14/11).
- Une fois le mode download latché (IO0 bas au reset), le ROM y **reste des
  minutes** — pas de timeout court. On a le temps de lancer esptool.
- Le e-ink retient l'ancienne image indéfiniment : un écran « figé » ne prouve
  ni la mort ni la vie. Seuls comptent : console, logs, scintillement au boot.

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
