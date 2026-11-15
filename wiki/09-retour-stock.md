# 09 — Retour au firmware stock (Xteink « Licorice »)

## La réponse courte

**Techniquement : oui.** Le flash JTAG/esptool maîtrisé ici écrit n'importe quoi,
donc une restauration usine est possible. **Pratiquement : il faut d'abord se
procurer une image complète du flash d'un X4 Pro d'origine** — elle n'existe pas
en téléchargement officiel. Xteink ne publie pas de firmware de restauration ;
même la communauté le dit noir sur blanc
([ExplorInk, section « back up first »](https://explorink.com/install/)) :
« *There is no menu entry, no recovery partition and no vendor download that puts
it back. What puts it back is a copy of the flash you made before you wrote
anything.* » — et ce dump peut être celui **d'un appareil d'un autre
propriétaire**.

## Ce qu'il faut exactement

Un **dump complet du flash 16 Mo** d'un X4 Pro stock (16 777 216 octets exactement,
short = à jeter), pris avec `esptool --no-stub read-flash 0 0x1000000` avant tout
flash. Ce fichier rétablit en une seule écriture @0x0 : bootloader stock, table
de partition 16 Mo, otadata, les deux slots OTA et l'app Licorice.

> Pourquoi 16 Mo alors que notre setup dit « 8 Mo » : la **puce physique fait
> 16 Mo** (esptool/JTAG la détectent ainsi). C'est le bootloader ROM du X4 Pro
> qui est configuré 8 Mo et qui refuse les tables 16 Mo — d'où le ptable 8 Mo
> custom de ce dépôt. Une image stock complète ramène le bootloader d'origine
> qui, lui, connaît le 16 Mo.

## Pourquoi nos `update.bin` ne sont pas le stock

Les deux `update.bin` trouvés (`~/Downloads/update.bin`, celui de la sauvegarde
de carte) sont des images **CrossPoint 2.0.0** (magic `e9`, strings
`CrossPoint-ESP32-2.0.0`). Ils ne remettent pas Licorice.

## Le piège de la piste « swap de partition »

[https://xteink.dve.al/](https://xteink.dve.al/) propose « Flash English firmware »
(OTA rapide : écrit le firmware officiel sur la partition de *backup* puis swap).
**Ça ne marchera pas ici** : la ptable 8 Mo custom de ce dépôt n'a qu'**un seul
slot app** (`app0`, pas de `ota_1`). Le swap suppose le layout d'origine à deux
slots. Même remarque pour « Swap boot partition » de la page debug.

## Les 3 pistes concrètes (par ordre de chances)

1. **La communauté** — demander un dump « full flash » d'un X4 Pro stock sur le
   GitHub [crosspoint-reader-ko](https://github.com/crosspoint-reader-ko/crosspoint-reader-ko)
   (Discussions/Issues) ou le Discord Xteink. Beaucoup de gens ont cliqué
   « Save full flash » sur xteink.dve.al avant de flasher ; un dump est
   interchangeable entre appareils du même modèle.
2. **Le support Xteink** — mail demandant le « firmware de restauration usine /
   recovery image » pour X4 Pro. Réponse probable : procédure SAV, mais ça
   coûte un email.
3. **Les forums** (ereadersforum.com, Reddit) — sujets « Xteink X4 Pro » où un
   dump a pu être partagé.

## La procédure le jour où l'image arrive

```bash
# 1) (Refaire un backup du flash actuel AVANT, par sécurité — leçon du 14/11)
esptool --chip esp32s3 -p /dev/cu.usbmodem201101 --no-stub \
  read-flash 0 0x1000000 avant-retour-stock.bin
# ~18-25 min, écran figé pendant la lecture : c'est normal.
# Vérifier : exactement 16777216 octets, sinon refaire.

# 2) Écrire l'image stock @0x0
esptool --chip esp32s3 -p /dev/cu.usbmodem201101 --no-stub \
  write-flash 0x0 xteink-stock-16mb.bin
# Si esptool coince : JTAG (voir wiki/02-flash.md), program_esp @0x0.
# Le bootloader stock s'occuppe du reste (16 Mo, 2 slots OTA, app Licorice).

# 3) Power 10 s, boot : liseuse d'usine.
# La carte SD peut rester ; Licorice utilise ses propres dossiers.
```

## Leçons de ce cas (ajoutées aux playbooks)

- **Toujours dumper le flash complet avant de flasher quoi que ce soit.**
  `read-flash 0 0x1000000` (avec `--no-stub` — sinon le transfert long meurt
  à 15 %, « Packet content transfer stopped »). 18-25 min, une seule fois,
  et n'importe quel firmware redevient réversible.
- Un dump d'un appareil **du même modèle** est interchangeable : ce n'est pas
  un secret, c'est le firmware usine.
