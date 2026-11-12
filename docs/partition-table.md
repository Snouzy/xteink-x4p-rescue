# The partition table fix, byte by byte

## Symptom

After flashing the CrossPoint KO full image to an X4 Pro, the device
boot-loops. Serial console (115200) shows:

```
E (24) flash_parts: partition 3 invalid - offset 0x6b0000 size 0x6a0000
                    exceeds flash chip size 0x800000
E (24) boot: Failed to verify partition table
E (24) boot: load partition table error!
```

## Root cause

The KO full image's partition table (offset `0x8000`) declares partitions up
to `0x1000000` (16 MB) — it targets a 16 MB flash variant. The X4 Pro ships
with **8 MB** (`0x800000`), so the bootloader rejects the table before any
app runs.

Original (broken-on-8MB) table entries:

| label   | offset   | size     | ends at    | fits 8 MB? |
|---------|----------|----------|------------|------------|
| nvs     | 0x009000 | 0x005000 | 0x00E000   | yes        |
| otadata | 0x00E000 | 0x002000 | 0x010000   | yes        |
| app0    | 0x010000 | 0x6A0000 | 0x6B0000   | yes        |
| app1    | 0x6B0000 | 0x6A0000 | 0xD50000   | **no**     |
| spiffs  | 0xD50000 | 0x2A0000 | 0xFF0000   | **no**     |
| coredump| 0xFF0000 | 0x010000 | 0x1000000  | **no**     |

## Fixed layout (8 MB)

One OTA app partition spanning the rest of the flash. OTA updates from
CrossPoint overwrite this same slot via SD card, which CrossPoint supports
(`Settings → System → SD Card Firmware Update`).

| label   | type/subtype | offset   | size     |
|---------|--------------|----------|----------|
| nvs     | 0x01 / 0x02  | 0x009000 | 0x005000 |
| otadata | 0x01 / 0x00  | 0x00E000 | 0x002000 |
| app0    | 0x00 / 0x10  | 0x010000 | 0x7F0000 |

Entry format = standard ESP-IDF `esp_partition_info_t`, 32 bytes each:

```
u16 magic  = 0x50AA          (bytes: aa 50)
u8  type, u8 subtype
u32 offset (LE), u32 size (LE)
char label[16]
u32 flags
```

## The MD5 trailer quirk

ESP-IDF appends a 32-byte MD5 entry after the last partition. Two magic
values circulate in documentation and tools: `EB FF` and `EB EB`. On this
device's bootloader (ESP-IDF v5.x, MD5 enabled in the app but the ROM
bootloader path being picky), **only `EB EB` with `0xFF` padding is
accepted**.

Layout of the trailer:

```
offset  bytes
+0      eb eb                      <- magic (NOT eb ff)
+2      ff ff ff ff ff ff ff ff
        ff ff ff ff ff ff ff ff    <- 14 bytes of 0xFF padding
+16     <16 bytes>                <- MD5 of ALL preceding 32-byte entries
```

The MD5 input is the concatenation of the partition entries **only** (96
bytes for the 3-entry table above), not the trailer itself. Verified:
`md5(entries) == stored[16:32]` against the KO image's own table.

### Failure signatures by trailer state

| trailer bytes | console symptom |
|---|---|
| absent | `partition: No MD5 found in partition table` → app assert `esp_ota_get_running_partition` → reboot loop |
| `eb ff` magic | `flash_parts: partition 3 invalid magic number 0xffeb` → boot loop |
| `eb eb` magic, correct MD5 | boots |

## Writing the fixed table

One 4 KiB sector at `0x8000`:

```bash
python scripts/make-ptable.py ptable.bin
esptool --chip esp32s3 --port /dev/cu.usbmodemXXXXXX --baud 460800 \
  --before usb-reset write_flash 0x8000 ptable.bin
```

This write is small (one sector) and normally succeeds on the first try
even on the flaky link. Verify with a readback if in doubt:

```bash
esptool --chip esp32s3 --port /dev/cu.usbmodemXXXXXX --baud 460800 \
  --before usb-reset read_flash 0x8000 0x80 - | xxd
```

Expected first 128 bytes: three `aa 50`-prefixed entries then `eb eb ff…`.
