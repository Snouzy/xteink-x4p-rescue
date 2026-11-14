# 02 — Flasher le firmware (rappels et renvois)

Page volontairement courte : la procédure complète est dans
[`README.fr.md`](../README.fr.md) (section « Procédure de sauvetage ») et le
format de la table dans [`docs/partition-table.md`](../docs/partition-table.md).
Ici, seulement ce qui a été appris à la dure.

## L'ordre de flash (leçon brûlée le 14/11/2026)

1. **Image full D'ABORD** à l'offset `0x0` (via `scripts/flash-chunked.sh`).
2. **Table 8 Mo ENSUITE** à `0x8000` (`python scripts/make-ptable.py ptable.bin`
   puis un `write_flash 0x8000 ptable.bin`).

Pourquoi : l'image full embarque **sa propre table 16 Mo** à l'offset
`0x8000`. Si tu écris `ptable.bin` avant, le flash chunké (qui part de
l'offset 0) **ré-écrase** la table corrigée avec la cassée → boot-loop :

```
E (24) flash_parts: partition 3 invalid - offset 0x6b0000 size 0x6a0000
                    exceeds flash chip size 0x800000
```

3. **App seule (CrossInk)** : `@0x10000`. Une image d'app n'a ni bootloader
   ni table à `0x8000` — flasher ça à `0x0` tue le bootloader sans message.
   Comment la reconnaître : son offset `0x0` a un header `E9` d'app, et son
   `0x8000` contient des strings, pas une table (voir [07 — Firmwares](07-firmwares.md)).

## Les deux méthodes qui marchent

### esptool (mode download)

- Toujours `--after no-reset` pour **garder le download mode** entre les
  commandes ; le `hard_reset` final est le déclencheur de boot.
- `scripts/flash-chunked.sh 0 image-full.bin` : chunks de 256 Ko avec retry
  (le lien USB-Serial/JTAG lâche sur les transferts longs). Reprendre au
  chunk N si abandon : `./scripts/flash-chunked.sh N image-full.bin`.

### JTAG (la méthode fiable dans tous les états)

Le JTAG reste actif **même en boot-loop** ou quand le download mode est
injoignable. Deux points critiques :

- Le openocd **vanilla de brew échoue** (`esp_usb_jtag: could not find or
  open device`) : l'interface JTAG du composite CDC+JTAG est en position 2.
- Utiliser **openocd-esp32 d'Espressif** : `~/dev/openocd-esp32/bin/openocd`.
  pyusb ouvre le device **sans sudo**.

```bash
./scripts/jtag-fix-ptable.py [chemin/openocd-esp32/bin/openocd]
# halt → program_esp ptable.bin 0x8000 verify reset (~25 s)
```

## Attraper la fenêtre ROM d'une app plantée

`scripts/open-storm.py` martèle l'ouverture/fermeture du port USB (bauds et
DTR/RTS aléatoires) : l'app plantée crashe sur l'événement qu'elle ne sait
plus traiter → panic → reboot → le port réapparaît en
`/dev/cu.usbmodem201101` et le script flashe `ptable.bin` tout seul.

Limites : ça échoue si la boucle de boot fait **moins de ~1 s** (pas le
temps d'ouvrir le port), et ça ne décoince pas un hard-wedge complet
(interruptions coupées) — là, drain batterie, voir [01 — Matériel](01-materiel.md).

## Après le flash

Silence console + vendeur USB `Espressif` = ça a booté. Premier boot ~30 s.
Écran qui se rafraîchit = succès. Si boot-loop, lire la console
([03 — Console UART](03-console-uart.md)) et comparer aux signatures du
README.
