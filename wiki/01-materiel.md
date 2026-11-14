# 01 — Matériel : connaître son X4 Pro

Le X4 Pro est un ESP32-S3 avec une particularité : deux « personnalités »
USB selon l'état de la puce. Comprendre ça évite 90 % des fausses paniques.

## Le SoC et le flash

- **ESP32-S3** (dual-core 240 MHz, 8 Mo PSRAM), flash **8 Mo** (0x800000).
- Piège connu : esptool et le JTAG **détectent une flash de 16 Mo**, mais le
  bootlog ROM dit `flash chip size 0x800000`. Probable eFuse. Conséquence :
  la table de partition doit rester celle d'un flash 8 Mo, c'est la seule
  que le ROM valide. Détail : [docs/partition-table.md](../docs/partition-table.md).

## Les deux ports USB série

La liseuse énumère **un seul port à la fois**, et son nom change selon qui
le possède :

| Port | Qui l'expose | À quoi il sert |
|---|---|---|
| `/dev/cu.usbmodem201101` | Le ROM (bootloader) | Console de boot 115200 8N1 + mode ROM/download |
| `/dev/cu.usbmodem84C7BB7AB2042` | L'app (firmware) | Console de l'app une fois démarrée |

- Le port `201101` n'existe que quand la puce est en ROM (boot ou download
  mode). L'app, elle, énumère toujours sous `usbmodem84C7BB7AB2042`.
- Quand l'app démarre, elle **reprend le périphérique USB** : le port saute
  sous tes pieds. C'est normal, pas une déconnexion.
- Une fois le mode download latché (IO0 bas au reset), le ROM y **reste des
  minutes** — pas de timeout court. Tu as le temps de lancer esptool.

## DTR/RTS inertes : le bouton Power EST le reset

Pas de circuit auto-reset sur ce hardware (vérifié par polling 50 ms) :
ni esptool ni un script ne peuvent forcer un reset logiciel.

- Pour rebooter : **Power ~10 s** à maintenir.
- Si le firmware est flashé en `--after no-reset` (mode ROM) : le bouton
  Power ne fait **rien**. Le `hard_reset` d'esptool ou un reflash avec
  `--after hard_reset` est le déclencheur de boot (voir [02 — Flash](02-flash.md)).

## Le freeze sans carte SD au boot est NORMAL

Sans carte SD insérée, le firmware **attend le stockage** et l'écran reste
figé. Ce n'est ni un brick ni un bug :

1. Remets la carte SD.
2. Power 10 s pour rebooter.
3. Attends le boot (~30 s).

Ne reflashe rien dans cet état.

## Batterie : le joker du hard-wedge

Si la liseuse est complètement coincée (écran figé, console muette, aucun
combo boutons ne répond, esptool ne sync pas sur aucun port) :

1. D'abord essayer `scripts/open-storm.py` — voir [02 — Flash](02-flash.md).
2. Sinon : **laisser la batterie se drainer complètement** (LED allumée =
   drain actif ; compte 12–36 h). Puis charge 15 min, Power 3 s.

Le bouton Power est une simple source d'interruption : une puce coincée
avec les interruptions coupées ne le verra jamais. Le drain complet est le
seul reset infaillible. Récit complet : [docs/full-story.md](../docs/full-story.md)
(section « Hard wedge »).

## Ne pas se fier à l'écran

Le e-ink retient l'ancienne image indéfiniment. Un écran « figé » ne prouve
ni la mort ni la vie. Pour savoir ce qui se passe : la console
([03 — Console UART](03-console-uart.md)).
