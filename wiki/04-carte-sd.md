# 04 — Carte SD : montage, nettoyage, sauvegarde

La carte SD est le stockage principal de la liseuse. Tout se passe ici :
livres, index de bibliothèque, dictionnaires, caches.

## Monter la carte sans la sortir

Sur la liseuse : menu connectivité → **« Lecteur USB »**. L'écran propose
notamment OPDS / rejoindre un réseau / point d'accès / lecteur USB — choisis
le dernier. Un volume **`XTEINK`** apparaît sur le Mac.

Alternative si la liseuse est plantée : sortir la carte, adaptateur USB-C.
Pas de risque tant qu'elle n'est pas en cours d'écriture (écran éteint ou
app idle).

## Pièges macOS

### Les fichiers `._*` (AppleDouble)

À chaque montage, macOS crée des sidecars `._*` de 4096 o, y compris de
faux `._truc.epub`. Le walk de la bibliothèque les ignore (les noms
commençant par `.` sont exclus — vérifié dans le code), mais ils polluent la
carte et le backup. Nettoyage :

```bash
cd /Volumes/XTEINK && dot_clean . && find . -name "._*" -delete
```

### Éjection propre

Impérativement **sortir du volume avant d'éjecter** : un shell positionné
sur `/Volumes/XTEINK` bloque l'éjection (`Unmount was dissented`).

```bash
cd /
diskutil eject /Volumes/XTEINK
```

### Montage lent

Le premier `ls` peut mettre quelques secondes à répondre après le montage
USB. Patienter, ne pas débrancher.

## Sauvegarde complète

Dump de tout le volume avant toute grosse manip (flash, nettoyage, ajout
massif) :

```bash
mkdir -p ~/Downloads/xteink-sd-card-backup-20261114
rsync -a /Volumes/XTEINK/ ~/Downloads/xteink-sd-card-backup-20261114/
```

(Vérifier avec `du -sh ~/Downloads/xteink-sd-card-backup-20261114` que tout
est passé, puis éjecter.)

## Ajouter des livres : par paquets de ~5

Un scan massif surcharge la liseuse : **28 EPUB d'un coup** ont provoqué des
freezes et des écrans figés. La méthode qui marche :

1. Copier ~5 livres sur la carte.
2. Sur la liseuse : bouton ⟳ ou menu ⋮ → « Rescanner la bibliothèque ».
3. Attendre la fin du scan (10–30 s pour 2 EPUB, plus pour 5).
4. Vérifier que les livres apparaissent, puis paquet suivant.

Rappel : copier un EPUB sur la carte **ne suffit jamais** à le rendre
visible — il faut toujours un rescan. Pourquoi : [05 — Bibliothèque](05-bibliotheque-scan.md).

## Le dictionnaire ralentit tout (c'est normal)

Le dossier `dictionaries/` (~1,2 Go) fait grimper le temps de scan et la
latence de la sélection de mots dans le lecteur. CrossPoint et CrossInk ont
le même moteur : le comportement est identique sur les deux firmwares. Ce
n'est **pas** un bug du firmware. Si le scan paraît anormalement long,
retirer temporairement le dictionnaire pour isoler la cause.

## Structure utile à connaître

- `/.crosspoint/` — dossier de config partagé par CrossPoint **et** CrossInk
  (index `library.idx`, flag `library.dirty`, caches EPUB). Ne pas supprimer.
- `/.crossink/` — certaines données propres à CrossInk.
- `dictionaries/`, `fonts/`, `Livres/…` — contenu utilisateur normal.

Tout détail sur l'index : [05 — Bibliothèque](05-bibliotheque-scan.md).
