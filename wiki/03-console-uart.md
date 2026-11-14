# 03 — Console UART : diagnostiquer en direct

La console 115200 8N1 est ta fenêtre sur la liseuse. C'est par elle qu'on a
compris chaque bug de ce dépôt.

## Installer pyserial (sans toucher au python système)

Le python3 système (3.15) est en PEP-668 : `pip install --user` refuse.
Utilise un venv jetable :

```bash
python3 -m venv /tmp/xteink-venv
/tmp/xteink-venv/bin/pip install pyserial
```

Ensuite tous les scripts du dépôt se lancent avec
`/tmp/xteink-venv/bin/python scripts/console-listen.py …`.

## Lecture rapide (boot-loop connue)

```bash
/tmp/xteink-venv/bin/python scripts/console-listen.py /dev/cu.usbmodem201101
```

Le script écoute 45 s, coupe au deuxième `ESP-ROM` (deux cycles de boot),
et interprète les signatures d'échec connues (table 16 Mo, magic MD5).
Silence + changement d'écran = ça a booté, l'app a pris le port.

## Capture longue avec reconnexion

Problème : **le port saute au reboot** — la liseuse change de
`/dev/cu.usbmodem201101` à `/dev/cu.usbmodem84C7BB7AB2042` (voir
[01 — Matériel](01-materiel.md)), et pyserial lâche en cours de route. Pour
capturer un boot entier, il faut rouvrir le port en boucle et marquer les
transitions. Script de capture (`/tmp/capture-uart.py`) :

```python
import glob, sys, time, serial

DUREE = int(sys.argv[1]) if len(sys.argv) > 1 else 180
t0, ouvert = time.time(), False

while time.time() - t0 < DUREE:
    ports = sorted(glob.glob("/dev/cu.usbmodem*"))
    if not ports:
        ouvert = False
        time.sleep(0.3)
        continue
    try:
        s = serial.Serial(ports[0], 115200, timeout=0.5)
    except Exception:
        time.sleep(0.3)
        continue
    if not ouvert:
        print(f"<<<PORT OUVERT {ports[0]}>>>", flush=True)
        ouvert = True
    try:
        d = s.read(4096)
        if d:
            sys.stdout.write(d.decode("utf-8", errors="replace"))
            sys.stdout.flush()
    except Exception:
        print(f"<<<PORT PERDU {ports[0]}>>>", flush=True)
        ouvert = False
    s.close()
```

Mode d'emploi (le reboot se fait PENDANT la capture) :

```bash
/tmp/xteink-venv/bin/python /tmp/capture-uart.py 240 > /tmp/boot-capture.log 2>&1 &
# pendant ce temps : rebooter la liseuse (Power 10 s)
wait
grep -E "LIBIDX|SDMMC|MEM\]|CPRO" /tmp/boot-capture.log
```

150–240 s couvrent un boot lent + un début de scan. Les marqueurs
`<<<PORT OUVERT>>>` / `<<<PORT PERDU>>` te disent exactement où la puce a
changé d'état.

## Glossaire des logs réels observés

| Log | Signification |
|---|---|
| `[SD] SDMMC card mounted` | La carte SD est montée au boot. Son absence explique un freeze (voir [01 — Matériel](01-materiel.md)). |
| `[MEM] Periodic: heap free=…` toutes les ~10 s | L'app tourne en idle et est saine. Si ces lignes s'arrêtent, l'app vient de se bloquer — repérer la dernière ligne avant le silence. |
| `[CPRO] open: free=…` | **ContentProtection** : le DRM d'un livre en cours d'ouverture. Ce n'est PAS la bibliothèque. Le confondre avec l'ouverture de l'index a coûté une soirée (voir [05 — Bibliothèque](05-bibliotheque-scan.md)). |
| `[LIBIDX] built: … books` | Le scan a fini et indexé N livres. |
| `[LIBIDX] unchanged: … reused, … parsed` | Le scan a tourné mais l'index existant était déjà à jour. |
| *(aucune ligne LIBIDX)* | `buildLibraryIndex` n'a **jamais** été appelé pendant la fenêtre de capture — le scan n'a pas été déclenché. |
| `Warn : Transport "jtag" was already selected` | Message openocd inoffensif quand le JTAG est déjà actif. Ignorer. |

## Astuces

- Cible le port `201101` pour le boot (ROM) ; si l'app est déjà lancée,
  c'est `usbmodem84C7BB7AB2042`.
- Un boot normal CrossPoint/CrossInk est bavard. Le silence total avec écran
  figé = plus haut dans la stack (carte SD absente, app bloquée, hard-wedge).
- Garde chaque capture : le diff entre « boot qui marche » et « boot qui
  plante » se fait en une minute avec les marqueurs.
