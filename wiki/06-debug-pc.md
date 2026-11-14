# 06 — Debug sur PC : reproduire le scan avant de toucher au hardware

Un fichier « passe pas » dans la bibliothèque ? Avant de reflasher, de
formater la carte ou de soupçonner le hardware, fais tourner le **vrai code
du scan** sur ton Mac. Le build se fait avec clang++, les stubs de test
remplacent le hardware, et tu obtiens une preuve en 5 minutes.

## Les clones de référence

Deux clones locaux, en lecture seule :

- `~/dev/crosspoint-src` — clone de
  `github.com/crosspoint-reader-ko/crosspoint-reader-ko` (upstream).
- `~/dev/crossink-src` — clone de `github.com/uxjulia/CrossInk` (fork).
  Lire son `AGENTS.md` avant d'y fouiller.

Les deux partagent la même architecture :

- `lib/LibraryIndex/` — le moteur d'index (`LibraryBuilder` = le walk,
  `LibraryIndexFile` = la lecture, `LibraryFormat` = le format CLX1).
- `test/library_builder/stubs/` — stubs host : pas de matériel, tout est en
  mémoire. Deux hooks suffisent :
  - `fake::add(chemin, contenu, mtime)` — injecte un fichier en mémoire
    (taille = longueur du contenu, dossiers parents créés auto) ;
  - `bookMetadata[chemin] = {title, author, …}` — simule la lecture des
    métadonnées EPUB (y compris `success = false` pour tester l'échec).

## Compiler le vrai LibraryBuilder sur macOS

Recette vérifiée le 14/11/2026. Depuis la racine du clone (CrossInk ici,
identique pour CrossPoint) :

```bash
cd ~/dev/crossink-src

clang++ -std=c++17 -o /tmp/libtest \
  lib/LibraryIndex/LibraryBuilder.cpp \
  lib/LibraryIndex/LibraryIndexFile.cpp \
  lib/LibraryIndex/LibraryFormat.cpp \
  lib/LibraryIndex/LibraryText.cpp \
  lib/Utf8/Utf8.cpp \
  /tmp/libtest-main.cpp \
  -Itest/library_builder/stubs \
  -Ilib/FsHelpers -Ilib/LibraryIndex -Ilib/Serialization -Ilib/Utf8
```

Les stubs fournissent `Storage`, `Epub`, `SETTINGS`, le logging… — le vrai
`LibraryBuilder.cpp` compile tel quel contre eux.

## Le main : injecter les vrais fichiers

Modèle minimal (`/tmp/libtest-main.cpp`). Il injecte les vrais noms, tailles
et métadonnées du cas qui te préoccupe, lance le vrai
`library::buildLibraryIndex("/", stats, true)`, puis relit l'index écrit
pour vérifier ce qui a réellement été enregistré :

```cpp
#include <cstdio>
#include "LibraryBuilder.h"     // namespace library
#include "LibraryIndexFile.h"
#include "HalStorage.h"          // stubs : fake::add
#include "Epub.h"                // stubs : bookMetadata

int main() {
  fake::add("/L'ours - MARION, Rémy.epub",
            std::string(1282614, 'x'), /*mtime=*/1700000000);
  fake::add("/Spinoza _ l'essentiel de sa pensee en 100 - Camille Rousseau.epub",
            std::string(295461, 'x'), 1700000001);
  bookMetadata["/L'ours - MARION, Rémy.epub"] = {"L'ours", "Rémy Marion"};
  bookMetadata["/Spinoza _ l'essentiel de sa pensee en 100 - Camille Rousseau.epub"] =
      {"Spinoza : l'essentiel", "Camille Rousseau"};

  library::BuildStats stats{};
  const bool ok = library::buildLibraryIndex("/", stats, /*readMetadata=*/true);
  std::printf("build ok=%d books=%u skipped=%u dup=%u walkMs=%u\n",
              ok, stats.books, stats.unreadableSkipped,
              stats.duplicatesDropped, stats.walkMs);

  LibraryIndexFile idx;
  if (idx.open(library::libraryIndexPath()))
    std::printf("index relu: %u livres\n", idx.header().bookCount);
  return ok && stats.books == 2 ? 0 : 1;
}
```

Adapter les champs affichés à la version du clone (les noms de certains
compteurs `BuildStats` bougent entre CrossPoint et CrossInk — `rg
"struct BuildStats" lib/LibraryIndex`).

## Le résultat du 14/11/2026 (affaire Spinoza)

Les deux vrais fichiers, apostrophes et accents inclus :

- `L'ours - MARION, Rémy.epub` — 1 282 614 o
- `Spinoza _ l'essentiel de sa pensee en 100 - Camille Rousseau.epub` —
  295 461 o

→ **tous les deux trouvés et indexés** par le vrai code. Le scan marche.

Interprétation : si le vrai code indexe le fichier sur PC mais que la
liseuse ne le montre pas, le problème n'est **ni le fichier ni le firmware**
— c'est la déclenche du scan ou le tri (voir
[05 — Bibliothèque](05-bibliotheque-scan.md)), ou un souci carte/FAT
(vérifier sur le Mac avec la procédure de [04](04-carte-sd.md)). C'est
exactement comme ça que l'affaire Spinoza a été classée en une soirée au
lieu d'une semaine de flashes.

## Variantes utiles

- `bookMetadata[chemin].success = false;` → vérifier que le livre est
  quand même indexé (titre = nom de fichier). Confirme la règle de
  [05 — Bibliothèque](05-bibliotheque-scan.md).
- `fake::add("/.crosspoint/library.dirty", "");` → tester le chemin dirty.
- 300× `fake::add` d'un coup → stresser le plafond de livres et la dédup.
