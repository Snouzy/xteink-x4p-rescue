# 08 — Playbooks : fiches scénarios

Checklists sans théorie. Chaque scénario : symptômes → étapes → vérification.
Le détail derrière chaque étape vit dans les pages liées.

## A — Nouveau livre invisible dans la bibliothèque

**Symptômes** : EPUB copié sur la carte, introuvable dans la bibliothèque ;
seuls les livres déjà ouverts s'affichent ; pas de popup de scan.

1. Ouvrir l'écran **Bibliothèque**.
2. Vérifier le tri : s'il est sur « Récemment ouverts », passer à **Titre**
   ou **Date d'ajout** (le tri court-circuite l'index —
   [05](05-bibliotheque-scan.md)).
3. Bouton ⟳ ou menu ⋮ → **« Rescanner la bibliothèque »**.
4. Attendre 10–30 s (plus si le dictionnaire ~1,2 Go est sur la carte).
5. Vérifier que le livre apparaît.

**Vérification** : le livre est dans la liste. Si non → scénario B de
[05](05-bibliotheque-scan.md) (ordre de diagnostic complet), puis
[06](06-debug-pc.md) si le doute persiste.

## B — Liseuse figée, écran bloqué

**Symptômes** : écran figé, tactile mort. Rappel : le e-ink retient la
dernière image — un écran figé ne prouve rien ([01](01-materiel.md)).

1. Attendre 30 s (un scan ou un gros EPUB peuvent paralyser l'UI).
2. **Power 10 s** à maintenir (DTR/RTS inertes : le bouton EST le reset).
3. Si le freeze était au boot : vérifier que la **carte SD est insérée**
   (sans elle, le firmware attend le stockage — c'est normal,
   [01](01-materiel.md)).
4. Toujours figé → lire la console pendant un reboot
   ([03](03-console-uart.md)) : la dernière ligne avant le silence nomme le
   coupable.
5. Console muette + aucune réponse = hard-wedge → `scripts/open-storm.py`
   ([02](02-flash.md)), sinon drain de batterie complète puis charge 15 min,
   Power 3 s ([01](01-materiel.md)).

**Vérification** : boot normal, `[MEM] Periodic` toutes les ~10 s sur la
console ([03](03-console-uart.md)).

## C — Boot-loop « partition 3 invalid »

**Symptômes** : la console répète en boucle :

```
E (24) flash_parts: partition 3 invalid - offset 0x6b0000 size 0x6a0000
                    exceeds flash chip size 0x800000
```

1. C'est la **table 16 Mo** à `0x8000` (image full écrite après la table
   corrigée, ou vieux flash). Ne pas toucher à l'app.
2. Régénérer : `python scripts/make-ptable.py ptable.bin`.
3. La réécrire **en dernier** : après un éventuel reflash de l'image full.
   Deux voies : `write_flash 0x8000 ptable.bin` en download mode, ou
   **JTAG** qui marche même en boot-loop :
   `./scripts/jtag-fix-ptable.py` ([02](02-flash.md)).
4. Laisser rebooter (~30 s).

**Vérification** : plus de ligne `flash_parts` ; vendeur USB `Espressif` ;
l'écran se rafraîchit.

## D — Flasher CrossInk

**Symptômes** : tu veux installer/remettre l'app CrossInk.

1. Identifier l'image : c'est une **app seule** (header `E9` en 0x0, strings
   en 0x8000 — [07](07-firmwares.md)).
2. Flasher **uniquement à `0x10000`** : jamais à `0x0`.
3. Suivre la méthode du dépôt : chunks + `--after no-reset`, détail dans
   [README.fr.md](../README.fr.md) et [02 — Flash](02-flash.md).
4. Ne pas oublier : la table 8 Mo doit déjà être en place (scénario C si
   doute).

**Vérification** : boot CrossInk, bibliothèque accessible, rescan manuel
fonctionnel (scénario A).

## E — Ajouter 10–30 livres

**Symptômes** : grosse importation à faire.

1. Monter la carte en Lecteur USB ([04](04-carte-sd.md)).
2. Copier **~5 livres à la fois** (28 d'un coup = freezes constatés).
3. Sur la liseuse : ⟳ → « Rescanner la bibliothèque ».
4. Attendre la fin, vérifier l'apparition, paquet suivant.
5. Nettoyer les sidecars macOS avant d'éjecter :
   `cd /Volumes/XTEINK && dot_clean . && find . -name "._*" -delete`.
6. Éjection : `cd /` PUIS `diskutil eject /Volumes/XTEINK`
   ([04](04-carte-sd.md)).

**Vérification** : tous les livres apparaissent après le dernier rescan ;
le volume a éjecté proprement.

## F — Récupérer les logs d'un boot

**Symptômes** : tu veux savoir ce qui se passe pendant un boot ou un scan.

1. Préparer le venv : `python3 -m venv /tmp/xteink-venv &&
   /tmp/xteink-venv/bin/pip install pyserial` ([03](03-console-uart.md)).
2. Lancer la capture avec reconnexion en background (script de
   [03](03-console-uart.md)) :
   `/tmp/xteink-venv/bin/python /tmp/capture-uart.py 240 > /tmp/boot-capture.log 2>&1 &`
3. **Pendant la capture** : rebooter la liseuse (Power 10 s).
4. Attendre la fin, puis :
   `grep -E "LIBIDX|SDMMC|MEM\]|CPRO" /tmp/boot-capture.log`.

**Vérification** : le log contient les transitions `<<<PORT OUVERT>>>` /
`<<<PORT PERDU>>>` et les lignes attendues du glossaire
([03](03-console-uart.md)). Absence totale de `[LIBIDX]` = scan jamais
déclenché.
