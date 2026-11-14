# Full rescue story — chronological log

*Xteink X4 Pro, stock Licorice OS build 26111201 (2026-11-12), macOS host,
target: CrossPoint 2.0.0. Every step below was executed on the real device.*

## Phase 0 — Symptoms

- Device frozen on the settings screen with a Chinese factory menu overlay
  (`选择模式 / 老化 / 工厂测试 / 恢复出厂设置` = select mode / burn-in /
  factory test / factory reset). Touch unresponsive.
- USB connected but the Mac saw *only a serial port* (`/dev/cu.usbmodem*`,
  vendor string `XTEink`) — never a disk. That is by design: stock Licorice
  OS exposes no mass-storage interface. The Finder stays empty; this is
  normal, not a fault.

## Phase 1 — Standard methods, all failed

1. **Xteink Unlocker (OTA hijack).** The tool spawns a hotspot, intercepts
   DNS for `api-prod.xteink.cc`, and serves a fake update manifest.
   The reader joined the hotspot and asked for the update — but TLS failed:
   `received fatal alert: BadCertificate`. Stock firmware since build
   26111201 pins the update server's certificate, so the unlocker's
   self-signed cert is rejected. **Dead end for this firmware.**
2. **Web flasher (crosspointreader.com/install).** Port selection worked
   (`USB JTAG/serial debug unit`), but the transfer stalled within seconds:
   `Installation could not finish — Packet content transfer stopped`,
   consistently at 0.5–4 %.
3. **esptool, one-shot full image.** Same stall pattern: connection dropped
   during the long erase/write phase (`No more data to read from the serial
   port`), at random progress points.

## Phase 2 — Chunked flashing (breakthrough)

Hypothesis: the USB-Serial/JTAG link survives short transfers only.
Writing the image in 256 KB slices turned one stall-prone 2-minute transfer
into ~21 sub-second transfers. Each slice is hash-verified by esptool;
failed slices retry individually; the bootloader is kept warm with
`--after no-reset` and re-entered per attempt with `--before usb-reset`.

Result: ~80 % of slices passed on the first try, the rest within 2–5
retries, one stubborn slice (7) needed a resume run. Full image written and
verified, 100 %.

*Trap encountered on the way:* the official release asset
`firmware-x4pro.bin` is **application-only** (no bootloader, no partition
table — verifiable: offset 0x8000 contains string data, not a partition
table). Flashing it at 0x0 silently kills the bootloader. The **full** image
(with bootloader) is the `-full.bin` asset in the crosspoint-reader-ko
releases.

## Phase 3 — The 16 MB partition table on an 8 MB chip

With the full image in place the device boot-looped with:

```
partition 3 invalid - offset 0x6b0000 size 0x6a0000
exceeds flash chip size 0x800000
```

The KO image targets a 16 MB flash variant; the X4 Pro has 8 MB. Fix:
generate an 8 MB table (nvs / otadata / one 0x7F0000 app0 slot), write it at
0x8000. See [partition-table.md](partition-table.md).

## Phase 4 — The MD5 magic rabbit hole

First table attempt (entries only, no trailer): the app loaded, then
`No MD5 found in partition table` → `assert failed:
esp_ota_get_running_partition` → reboot loop. So an MD5 trailer is
mandatory.

Second attempt with the documented `EB FF` magic: the *bootloader* now
rejected the table — `partition 3 invalid magic number 0xffeb`.

Reading the KO image's own table revealed the working trailer:
`EB EB` + fourteen `0xFF` + MD5(entries). Third attempt with that exact
format: **clean boot.** The app enumerates USB under the Espressif vendor
string afterwards, which is the success tell.

## Verified end state

- Screen: CrossPoint UI up.
- USB: re-enumerates as `Espressif` (vendor ID 0x303A) once the app runs.
- Serial: goes silent after boot (the app owns the port).

## Reproducible recipe

See the [README](../README.md#quick-rescue-procedure) — three commands:
`make-ptable.py`, one small `write_flash 0x8000`, then `flash-chunked.sh`.

## Session 3 (2026-11-14, soirée) — l'affaire Spinoza

L'EPUB `Spinoza _ l'essentiel de sa pensee en 100 - Camille Rousseau.epub`
(295 461 o, copié à la racine de la carte) est introuvable dans la
bibliothèque : seuls les livres déjà ouverts s'affichent, aucun popup de
scan. Soirée passée sur les logs UART (`[CPRO]` confondu avec l'index — en
réalité ContentProtection, le DRM d'un livre en cours d'ouverture). Cause
finale vérifiée dans le code CrossInk (`src/activities/library/LibraryActivity.cpp:146-153`)
: avec le tri **« Récemment ouverts »**, `refreshIndexIfNeeded()` ferme
l'index et retourne sans jamais scanner. Le dirty flag n'étant posé que par
les arrivées via l'appareil, une copie Mac ne déclenche jamais rien.
Repro PC du vrai `LibraryBuilder` (voir [wiki/06](../wiki/06-debug-pc.md)) :
les deux vrais fichiers (accents et apostrophes inclus) indexent sans
erreur. Session consignée dans le [wiki](../wiki/00-index.md) (pages 03–06).
