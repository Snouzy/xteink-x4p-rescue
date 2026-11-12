#!/usr/bin/env python3
"""Build the corrected 8 MB partition-table sector for the Xteink X4 Pro.

The stock CrossPoint KO full image ships a 16 MB partition table which the
8 MB flash of the X4 Pro rejects (boot loop). This script emits a 4 KiB
sector for offset 0x8000 with an 8 MB layout and a valid MD5 trailer.

Layout:
  nvs      @ 0x00009000  size 0x00005000   (data / NVS)
  otadata  @ 0x0000E000  size 0x00002000   (data / OTA)
  app0     @ 0x00010000  size 0x007F0000   (app  / ota_0)  <- rest of flash

MD5 trailer (32 bytes) — the magic is 0xEBEB, padding is 0xFF:
  ebeb  ff*14  md5(entries)          (verified against the KO image;
                                      0xEBFF magic is rejected by this
                                      device's bootloader)
"""
import hashlib
import struct
import sys

PARTITION_MAGIC = 0x50AA


def entry(ptype: int, subtype: int, offset: int, size: int, label: str) -> bytes:
    return struct.pack("<HBBII16sI", PARTITION_MAGIC, ptype, subtype,
                       offset, size, label.encode(), 0)


def build() -> bytes:
    table = (
        entry(0x01, 0x02, 0x00009000, 0x00005000, "nvs")
        + entry(0x01, 0x00, 0x0000E000, 0x00002000, "otadata")
        + entry(0x00, 0x10, 0x00010000, 0x007F0000, "app0")
    )
    digest = hashlib.md5(table).digest()
    table += b"\xeb\xeb" + b"\xff" * 14 + digest
    return table + b"\xff" * (0x1000 - len(table))


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "ptable.bin"
    with open(out, "wb") as fh:
        fh.write(build())
    print(f"wrote {out} (4096 bytes)")


if __name__ == "__main__":
    main()
