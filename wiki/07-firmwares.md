# 07 — Firmwares : CrossPoint vs CrossInk

Deux firmwares, une base commune. Choisir l'un ou l'autre ne change pas la
mécanique du scan — ça change l'UI et le nom de certains menus.

## CrossPoint (upstream)

- Dépôt : `github.com/crosspoint-reader-ko/crosspoint-reader-ko`.
- Site : [crosspointreader.com](https://crosspointreader.com).
- Issue connue : **#31 ouverte** sur le freeze (comportement observé sur le
  X4 Pro en conditions réelles).
- UI : menu home avec **« Parcourir les fichiers / Bibliothèque / Transfert /
  Paramètres »**.
- Déclenche un scan au boot via la cover-grid du home (si l'index est
  absent) — CrossInk ne le fait pas.

## CrossInk (fork)

- Dépôt : `github.com/uxjulia/CrossInk` (fork d'upstream, UI revue).
- Clone de référence local : `~/dev/crossink-src` (lire son `AGENTS.md`,
  lecture seule).
- UI : écran bibliothèque direct, avec tris :
  **Date d'ajout, Titre, Auteur nom/prénom, Récemment ouverts, Séries, Genre**
  + menu Rechercher / Paramètres / Rescan.
- Déclenche le scan seulement à l'ouverture de l'écran Bibliothèque (sous
  conditions, voir [05](05-bibliotheque-scan.md)) ou sur rescan manuel.

## Ce qui est identique

- Le moteur EPUB (parsing, rendu, caches `/.crosspoint/epub_<hash>/`).
- `lib/LibraryIndex` : même walk, même format d'index CLX1
  (`/.crosspoint/library.idx`), même dossier `/.crosspoint/`.
- La sémantique du dirty flag (posé par les arrivées via l'appareil,
  jamais par une copie Mac) — fichier chez CrossPoint, flag mémoire chez
  CrossInk.
- Les pièges de scan de [05 — Bibliothèque](05-bibliotheque-scan.md) :
  présents sur les deux.

## Piège de traduction UI : « Récemment ouverts » ≠ « Date d'ajout »

CrossInk propose les deux tris. Ils n'ont rien à voir :

- **Date d'ajout** : trié depuis l'index — passe par le scan.
- **Récemment ouverts** : trié depuis l'historique de lecture — **ferme
  l'index et court-circuite le scan** (`LibraryActivity.cpp:146-153`).

Si ta bibliothèque s'affiche « toute seule » sans popup de scan, regarde
d'abord quel tri est actif. Voir [05](05-bibliotheque-scan.md).

## Les images : full vs app seule

| Image | Contenu | Offset de flash |
|---|---|---|
| `CrossPoint-2.0.0-ko.2-x4pro-full.bin` | Bootloader + table 16 Mo + app | `0x0` (PUIS table 8 Mo @ `0x8000`, voir [02](02-flash.md)) |
| App CrossInk | App seule, pas de bootloader | `0x10000` |

Comment distinguer une image d'app : son offset `0x0` commence par un
header `E9` d'application, et son offset `0x8000` contient des strings
d'app — pas une table de partition (`aa 50`). Flasher une app seule à `0x0`
**efface le bootloader silencieusement**. Le piège a déjà été payé une fois :
l'asset officiel `firmware-x4pro.bin` des releases crosspoint-reader-ko est
justement une app seule ; la bonne image complète est le `-full.bin`.

## OTA

CrossPoint supporte la mise à jour par carte SD
(`Settings → System → SD Card Firmware Update`) : elle écrit dans la
partition app0 unique de la table 8 Mo. Pratique pour tester CrossInk sans
JTAG… tant que la table est la bonne.
