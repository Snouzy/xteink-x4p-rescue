# Xteink X4 Pro — Sauvetage & installation de CrossPoint

Boîte à outils et documentation pour sauver un **Xteink X4 Pro** (ESP32-S3,
flash 8 Mo) et y installer [CrossPoint](https://crosspointreader.com), avec
la correction de deux bugs de firmware rencontrés en conditions réelles.

🇬🇧 [English version](README.md)

## Pourquoi ce dépôt

Flasher CrossPoint sur un X4 Pro paraît trivial… jusqu'à ce que **toutes**
les méthodes standard échouent. Ce dépôt documente un chemin de sauvetage
vérifié de bout en bout sur un vrai appareil (novembre 2026), avec des
scripts qui survivent à la connexion USB capricieuse du X4 Pro.

### Les deux bugs corrigés ici

**Bug 1 — L'image complète CrossPoint KO embarque une table de partition
16 Mo sur un appareil 8 Mo.** La table de `CrossPoint-*-x4pro-full.bin`
cible un flash de **16 Mo** ; le X4 Pro en a **8 Mo**. Résultat : boucle
de boot immédiate après flash.

```
E (24) flash_parts: partition 3 invalid - offset 0x6b0000 size 0x6a0000
                    exceeds flash chip size 0x800000
```

**Correction :** une table de partition 8 Mo custom (`scripts/make-ptable.py`),
écrite une fois à l'adresse `0x8000`. Détail byte par byte :
[docs/partition-table.md](docs/partition-table.md).

**Bug 2 — Le magic MD5 de la table de partition est `EB EB`, pas `EB FF`.**
Le format fonctionnel — reverse-engineeré depuis l'image KO elle-même — est
`ebeb + 14×ff + md5(entrées)`. Le mauvais magic donne soit
`No MD5 found in partition table` (assert côté app), soit
`invalid magic number 0xffeb` (rejet côté bootloader).

### Comparaison des méthodes

| Méthode | Résultat sur X4 Pro (firmware 26111201, macOS) |
|---|---|
| Xteink Unlocker (OTA) | ❌ `TLS handshake failed: BadCertificate` — le firmware pin le certificat depuis le build 26111201 |
| Flasher web (crosspointreader.com) | ❌ `Packet content transfer stopped` à 0,5–4 % — le lien USB-Serial/JTAG lâche sur les longs transferts |
| esptool, image entière d'un coup | ❌ Même coupure, de façon constante |
| **esptool en chunks de 256 Ko + retry** | ✅ **Fonctionne.** ~21 chunks, retries individuels |

## Procédure de sauvetage

```bash
pip install esptool
curl -L -o x4pro-full.bin \
  https://github.com/crosspoint-reader-ko/crosspoint-reader-ko/releases/download/2.0.0-ko.2/CrossPoint-2.0.0-ko.2-x4pro-full.bin

python scripts/make-ptable.py ptable.bin

ESPTOOL=$(which esptool)
$ESPTOOL --chip esp32s3 --port /dev/cu.usbmodemXXXXXX --baud 460800 \
  --before usb-reset write_flash 0x8000 ptable.bin

./scripts/flash-chunked.sh 0 x4pro-full.bin
# Si le script s'arrête au chunk N : ./scripts/flash-chunked.sh N x4pro-full.bin

# Débrancher l'USB, Power ~3 s. Premier boot ~30 s.
```

## Diagnostiquer une boucle de boot

```bash
python scripts/console-listen.py /dev/cu.usbmodemXXXXXX
```

| La console dit | Cause | Solution |
|---|---|---|
| `exceeds flash chip size 0x800000` | Table prévue pour 16 Mo | `make-ptable.py` → écriture à `0x8000` |
| `No MD5 found in partition table` | Trailer MD5 absent | idem, vérifier le magic `ebeb` |
| `invalid magic number 0xffeb` | Magic MD5 `eb ff` au lieu de `eb eb` | idem |
| `Packet content transfer stopped` | Transfert long interrompu | script chunké |
| Silence + vendeur USB `Espressif` | **Ça a booté.** | — |

## Fiches techniques (X4 Pro)

- SoC **ESP32-S3** (240 MHz dual-core, 8 Mo PSRAM), flash **8 Mo**
- USB : USB-Serial/JTAG natif — s'annonce `XTEink` (stock) / `Espressif`
  (CrossPoint). **Aucun mode disque** : le Finder ne le montrera jamais,
  c'est normal.
- Stock : Licorice OS, build `26111201` (format date AAAAMMJJ).
- Le verrouillage USB-flash n'existe que sur les unités achetées hors
  xteink.com (AliExpress etc.).

## Licence

Images firmware = propriété de leurs projets respectifs. Scripts et docs
originaux ici : MIT.
