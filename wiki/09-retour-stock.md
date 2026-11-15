# 09 — Retour au firmware stock (Xteink « Licorice »)

## ✅ FAIT le 15/11/2026 — stock V7.6.8 installé et fonctionnel

Le retour au stock a été réalisé : app officielle **V7.6.8** flashée @0x10000 via
JTAG (`reset halt` + `program_esp … verify reset`, ~6 min pour 6,25 Mo), en
conservant le bootloader ko.2 @0x0 et le ptable 8 Mo @0x8000. Premier boot sur
l'écran de choix de région (Domestic CN / Overseas Global) — le stock fonctionne
avec le bootloader ko.2, la preuve par l'usage.

Binaires (ne pas publier, copyright Xteink) :
- `~/Downloads/xteink-stock-app-V7.6.8.bin` — app claire, sha256
  `f68533a8c55c55144303605e6497a0178215d477ec2642375814e00612afe087`
- `~/Downloads/xteink-stock-V7.6.8-encrypted.xota` — original chiffré

### Limitation connue : les mises à jour OTA automatiques échouent (code -112)

`esp_ota_begin` retourne -112 parce que la ptable 8 Mo custom n'a qu'**un seul
slot app** (`ota_0`); l'OTA stock veut écrire la nouvelle version dans `ota_1`,
qui n'existe pas. Rien n'est cassé — la maj avorte proprement AVANT d'écrire.
Deux conséquences :

1. **Ignorer la notification de maj** sur l'appareil (elle reviendra).
2. **Maj manuelle** quand on en veut une (voir ci-dessous).

### Procédure de mise à jour manuelle du stock

```bash
# 1. Interroger l'API officielle (canal .cn = Domestic, le plus à jour ; .cc = Overseas)
curl -s "http://api-prod.xteink.cn/api/v1/check-update?current_version=V7.6.8\
&device_type=ESP32S3_X4_TL_SSD1677&device_id=12345&lng=cn&ota_type=1"
#    -> JSON : version, download_url (.xota), plain_sha256
#    Note : les toutes nouvelles versions (ex. format V26111201) ne sont
#    servies qu'aux appareils enregistrés (device_id réel) — rollout progressif.

# 2. Télécharger le .xota, le déchiffrer (voir « Comment le firmware a été
#    obtenu » plus bas), vérifier sha256 + magic e9.

# 3. Flasher via JTAG (voir wiki/02-flash.md), app seule @0x10000 :
#    reset halt ; program_esp <app.bin> 0x10000 verify reset
```

### Chantier futur : rétablir l'OTA auto (layout 16 Mo)

La puce fait physiquement **16 Mo** (esptool/JTAG le confirment ; seul le
bootloader ko.2 est *configuré* 8 Mo — c'est lui qui refuse les tables >
8 Mo). Rétablir l'OTA auto = écrire un bootloader esp-idf buildé pour 16 Mo +
une table nvs/otadata/ota_0/ota_1. Risque : paramètres flash (QIO/OPI) à
deviner ; brick toujours récupérable par JTAG. À faire en session dédiée.

## Comment le firmware a été obtenu (méthode reproductible)

```bash
# 1. Interroger l'API de mise à jour officielle (device_type du X4 Pro)
curl -s "http://api-prod.xteink.cc/api/v1/check-update?current_version=V0.0.1\
&device_type=ESP32S3_X4_TL_SSD1677&device_id=12345&lng=en&ota_type=1"
# -> JSON : version, download_url (.xota), size, plain_sha256

# 2. Télécharger le .xota depuis l'URL du JSON

# 3. Déchiffrer (format XOTA documenté dans crosspoint-tools/src/xota.rs) :
#    [0:4] "XOTA" | [4:20] IV | [20:202] métadonnées AES-128-CTR | [202:] app chiffrée
#    CTR = compteur 128-bit big-endian CONTINU sur métadonnées+app.
#    Clé AES-128 du channel ota_type=1 (constante du firmware, publiée) :
KEY1=4f2791b80dd75a6aef0d728a39a8c05e
#    pycryptodome : AES.new(key, MODE_CTR, nonce=b'',
#                           initial_value=int.from_bytes(iv,'big')).decrypt(data[20:])
# 4. Vérifier : sha256(app_claire) == plain_sha256 de l'API, premier octet 0xe9,
#    strings "XTEink X4 Pro".
```

## La réponse courte

**Techniquement : oui, et c'est maintenant prêt.** Le flash JTAG/esptool de ce
dépôt écrit l'image stock claire @0x10000 en conservant le bootloader ko.2 @0x0
et la ptable 8 Mo @0x8000 — layout compatible esp-idf (nvs, otadata, app0 en
ota_0).

## Procédure de retour au stock (avec le V7.6.8 obtenu)

```bash
cd ~/dev/xteink-x4p-rescue

# 1) Sauvegarder le flash actuel AVANT (leçon du 14/11 — toujours dumper)
esptool --chip esp32s3 -p /dev/cu.usbmodem201101 --no-stub \
  read-flash 0 0x800000 avant-retour-stock-8mb.bin
# ~15-20 min, écran figé : normal. Vérifier la taille du fichier.

# 2) Flasher l'app stock @0x10000 (méthode chunkée éprouvée, 6,25 Mo)
./scripts/flash-chunked.sh 0 ~/Downloads/xteink-stock-app-V7.6.8.bin
# ⚠️ Ne PAS écrire 0x8000 ensuite : le ptable 8 Mo actuel reste en place.

# 3) Power 10 s, boot. Console UART pour le premier boot :
python3 scripts/console-listen.py /dev/cu.usbmodem201101

# 4) Si boot KO : lire les logs (partition manquante, etc.) et ajuster la
#    ptable (scripts/make-ptable.py) en conséquence.
```

Risques résiduels : l'app stock peut réclamer une partition absente du ptable
8 Mo (les logs UART le diront) ; les futures mises à jour OTA du stock
s'installeront dans le slot unique ota_0 (OTA « même slot », supporté par
esp-idf). L'app stock V7.x gère le panneau UC8279/SSD1677 de ce X4 Pro.

## Ce qu'il ne faut PAS faire

- **La piste « swap OTA » de xteink.dve.al** : notre ptable n'a qu'un seul
  slot (`ota_1` absent), le swap suppose deux slots. Incompatible.
- **Publier les binaires stock** dans ce dépôt : copyright Xteink. La méthode
  de la section « obtenu » suffit.

## Les 3 pistes historiques (si un jour l'API tombe)

1. Dump complet 16 Mo d'un X4 Pro d'origine (`esptool --no-stub read-flash 0
   0x1000000` — un dump d'un appareil du même modèle est interchangeable).
2. Support Xteink : « recovery image X4 Pro ».
3. Forums (ereadersforum.com, Reddit r/Xteink).

## Leçons

- **Toujours dumper le flash complet avant de flasher quoi que ce soit.**
- L'OTA « chiffré » de Xteink est un chiffrement de transport AES-128-CTR avec
  une clé constante extraite du firmware — documenté par crosspoint-tools.

