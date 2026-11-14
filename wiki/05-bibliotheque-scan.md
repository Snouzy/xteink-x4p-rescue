# 05 — Bibliothèque & scan : pourquoi un livre disparaît

Le morceau central du wiki. Cas réel du 14/11/2026 : `Spinoza _ l'essentiel
de sa pensee en 100 - Camille Rousseau.epub` copié à la racine de la carte,
**introuvable** dans la bibliothèque. Seuls les livres déjà ouverts
s'affichent. Aucun popup de scan. Soirée entière passée dessus — la cause
était le tri actif, pas le fichier.

## Le symptôme exact

- EPUB présent sur la carte (visible en Lecteur USB).
- Dans la bibliothèque : seuls les livres **déjà lus** apparaissent.
- L'écran Bibliothèque s'ouvre **directement**, sans popup « Scan en cours ».

Ces trois points ensemble = la signature du piège ci-dessous.

## La cause exacte (vérifiée dans le code)

CrossInk, `src/activities/library/LibraryActivity.cpp:146-153` :

```cpp
void LibraryActivity::refreshIndexIfNeeded(const bool showScanning) {
  if (sort == Sort::RecentlyRead) {
    index.close();
    scanFailed = false;
    uiReady = false;
    applyFilter();
    return;               // <- jamais de scan, jamais d'index
  }
  …
```

Quand le tri actif est **« Récemment ouverts »** (`Sort::RecentlyRead`),
l'activité **ferme l'index et retourne immédiatement**. La liste affichée
provient de `RECENT_BOOKS` (l'historique de lecture) : elle ne touche ni
l'index, ni le scan, ni la carte. C'est un comportement du code, pas un bug
de ta carte.

**Leçon : « Récemment ouverts » ≠ « Date d'ajout ».** Le deuxième passe par
l'index ; le premier le court-circuite. Voir [07 — Firmwares](07-firmwares.md).

## La mécanique complète du scan

### L'index

- Fichier binaire `/.crosspoint/library.idx`, format maison **« CLX1 »**.
- Dossier de config partagé : `/.crosspoint/` (les deux firmwares y écrivent)
  + `/.crossink/` pour certaines données CrossInk.
- Une entrée = chemin + taille + métadonnées (titre/auteur lus dans l'EPUB
  si possible). Le tri et les filtres se font sur l'index, pas sur la carte.

### Quand un rebuild se déclenche

1. **Ouverture de l'écran Bibliothèque** — UNIQUEMENT si :
   - le tri ≠ « Récemment ouverts » (sinon court-circuit, ci-dessus), ET
   - l'un de ces trois cas :
     - l'index est absent (premier boot, carte fraîche) ;
     - le flag dirty est présent (voir plus bas) ;
     - le réglage « utiliser les métadonnées » a changé depuis le dernier
       scan (l'index enregistre la version du réglage dans son entête).
2. **Au boot**, via la cover-grid du home — CrossPoint seulement, et
   seulement si l'index est absent.
3. **Bouton ⟳ ou menu ⋮ → « Rescanner la bibliothèque »** — appelle
   `refreshLibrary()` : rebuild **forcé**, indépendant du tri. C'est le
   déclencheur manuel, celui qui marche à tous les coups.

### Le dirty flag : posé par l'appareil, jamais par le Mac

Le flag dirty signale « un livre a été ajouté/enlevé, re-scanne ». Il n'est
posé que quand le livre arrive **via l'appareil** : upload web, OPDS,
plugins. Une copie directe sur la carte depuis le Mac **ne le pose jamais**.

- CrossPoint (upstream) : fichier `/.crosspoint/library.dirty`
  (`DIRTY_PATH` dans `lib/LibraryIndex/LibraryBuilder.cpp`).
- CrossInk : flag en mémoire (`indexDirty`), même sémantique.

**Conséquence : copier un EPUB sur la carte ne rendra JAMAIS le livre
visible tout seul.** Il faut un rescan manuel (⟳). C'est le point que la
procédure « nouveau livre invisible » corrige, plus bas.

### Le walk (comment la carte est parcourue)

Implémenté dans `lib/LibraryIndex/LibraryBuilder.cpp` :

- Départ : racine `/`, récursif.
- Ignoré : tout nom commençant par `.` (fichiers cachés, sidecars macOS
  `._*`, dossiers `.crosspoint/`…).
- Accepté : `.epub`, `.txt`, `.md`, `.xtc`, `.xtch`.
- Sauté : taille 0 ; nom > 255 octets ; doublons (clé = hash FNV-1a du nom
  concaténé à la taille).
- Plafond : un nombre max de livres dans l'index (le build s'arrête et
  **garde l'ancien index** si la carte le dépasse).

### Les métadonnées échouées n'excluent PAS un livre

Si les métadonnées d'un EPUB ne se lisent pas, le livre est **quand même
indexé** — avec titre = nom de fichier. Donc :

> « Absent de la bibliothèque » ne peut PAS être un problème de fichier
> corrompu. C'est **toujours** un problème de scan déclenché, ou de tri.

C'est ce qui a permis de classer l'affaire Spinoza en minutes sur PC
(voir [06 — Debug PC](06-debug-pc.md)).

## Procédure « nouveau livre invisible »

Dans l'ordre, sans sauter d'étape :

1. **Vérifie l'écran et le tri.** Es-tu dans l'écran Bibliothèque ? Le tri
   est-il « Récemment ouverts » ? Change-le : « Trier par… » → Titre ou Date
   d'ajout. Le livre apparaît peut-être immédiatement.
2. **Rescan manuel.** Bouton ⟳ ou menu ⋮ → « Rescanner la bibliothèque ».
3. **Attends.** 10–30 s pour 2 EPUB, davantage si gros dictionnaire
   présent (voir [04 — Carte SD](04-carte-sd.md)).
4. **Vérifie.** Toujours absent → passe au diagnostic.

## Ordre de diagnostic correct

1. **Quel écran + quel tri ?** (le piège n°1, ci-dessus).
2. **La carte montée sur le Mac** ([04 — Carte SD](04-carte-sd.md)) : le
   fichier est bien là ? Taille > 0 ? Pas de nom > 255 octets ?
3. **Console UART** ([03 — Console UART](03-console-uart.md)) : relance un
   rescan pendant une capture. Présence de `[LIBIDX] built: …` = le scan a
   tourné et a vu N livres. Absence **absolue** de LIBIDX = le scan n'a
   jamais été déclenché (retour à l'étape 1). Attention à ne pas confondre
   avec `[CPRO]` (ContentProtection = DRM d'un livre en cours d'ouverture,
   **pas** la bibliothèque).
4. **Repro sur PC** ([06 — Debug PC](06-debug-pc.md)) : compiler le vrai
   `LibraryBuilder` avec le vrai nom de fichier tranche en 5 minutes entre
   « bug du firmware » et « problème réel de la carte/FAT ».
5. **Seulement alors**, toucher à la carte/index.

## Ce qu'il ne faut PAS faire en premier réflexe

- **Supprimer `/.crosspoint/library.idx`.** Ça ne répare pas un problème
  d'affichage (le tri court-circuite l'index de toute façon), et tu perds
  l'historique d'indexation. À réserver au cas où l'index est corrompu —
  et le firmware sait restaurer un backup sain tout seul.
- Copier-détruire-recopier le fichier : il n'est pas en cause.
- Conclure « firmware cassé » avant l'étape 4 : le même moteur tourne sous
  CrossPoint et CrossInk, les deux réagissent pareil.
