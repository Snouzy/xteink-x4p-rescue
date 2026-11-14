# Wiki Xteink X4 Pro — Index

Pages courtes, ordre logique. Chaque page renvoie aux docs du dépôt au lieu
de les recopier. Commence par ici, saute direct à la page qui matche ton
symptôme.

## Table des matières

- **[01 — Matériel](01-materiel.md)** — les ports USB, le flash 8/16 Mo,
  DTR/RTS inertes, le freeze sans carte SD, la batterie comme dernier recours.
  *Quand consulter : avant toute manip, pour comprendre pourquoi le port
  change de nom, pourquoi le bouton Power ne répond pas, ou pourquoi la
  liseuse semble morte sans sa carte SD.*

- **[02 — Flasher le firmware](02-flash.md)** — ordre de flash (leçon
  brûlée), JTAG, esptool, open-storm. Renvoie vers `README.fr.md` et
  `docs/partition-table.md` pour le détail.
  *Quand consulter : tu vas flasher une image, corriger une boot-loop
  `partition 3 invalid`, ou installer CrossInk.*

- **[03 — Console UART](03-console-uart.md)** — lire les logs en direct,
  script de capture avec reconnexion, glossaire des lignes réelles observées.
  *Quand consulter : tu veux savoir ce que fait la liseuse pendant un boot,
  un scan ou un freeze, ou attraper un log fugitif.*

- **[04 — Carte SD](04-carte-sd.md)** — Lecteur USB, fichiers `._*`,
  éjection propre, sauvegarde, ajouts de livres par paquets.
  *Quand consulter : tu copies des livres, tu nettoies la carte, ou le Mac
  refuse d'éjecter le volume `XTEINK`.*

- **[05 — Bibliothèque & scan](05-bibliotheque-scan.md)** — LE morceau
  central : pourquoi un EPUB copié sur la carte n'apparaît pas, le piège du
  tri « Récemment ouverts », la mécanique complète du scan, la procédure de
  déblocage et l'ordre de diagnostic.
  *Quand consulter : un livre est introuvable dans la bibliothèque, le scan
  ne se lance pas, ou tu hésites à supprimer `library.idx`.*

- **[06 — Debug sur PC](06-debug-pc.md)** — reproduire le scan du firmware
  sur le Mac avec le vrai code `LibraryBuilder`, pour trancher en 5 minutes
  entre « bug du firmware » et « problème de carte ».
  *Quand consulter : un fichier refuse d'être indexé et tu veux une preuve
  avant de toucher au hardware.*

- **[07 — Firmwares](07-firmwares.md)** — CrossPoint vs CrossInk : même
  base, différences d'UI, tris de la bibliothèque, types d'images (full vs
  app seule).
  *Quand consulter : tu choisis un firmware, tu changes de tri, ou tu veux
  savoir quelle image flasher à quel offset.*

- **[08 — Playbooks](08-playbooks.md)** — fiches scénarios A→F : symptômes,
  étapes courtes, vérification.
  *Quand consulter : tu as un symptôme précis et tu veux la checklist sans
  théorie.*

## Docs du dépôt (à ne pas dupliquer)

- [`README.fr.md`](../README.fr.md) — procédure de sauvetage complète,
  comparaison des méthodes, bugs corrigés.
- [`docs/partition-table.md`](../docs/partition-table.md) — format de la
  table 8 Mo, byte par byte, quirk du magic MD5 `EB EB`.
- [`docs/full-story.md`](../docs/full-story.md) — journal chronologique des
  sessions de sauvetage (phases 0→4, sessions 2 et 3).
- [`scripts/`](../scripts/) — `make-ptable.py`, `flash-chunked.sh`,
  `console-listen.py`, `open-storm.py`, `jtag-fix-ptable.py`.

## Règle d'or

> Un écran e-ink figé ne prouve rien : le panneau retient la dernière image
> indéfiniment. Seuls comptent : la console UART, les logs, et le
> scintillement au boot.
