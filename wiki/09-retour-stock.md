# 09 — Retour au firmware stock (Xteink « Licorice »)

## ✅ Le firmware stock est OBTENU (15/11/2026) — voie OTA officielle

Mise à jour majeure : il n'y a **pas besoin d'un dump d'un autre appareil**.
L'API de mise à jour officielle de Xteink distribue le firmware stock en
`.xota` (`encrypted_v1`), et le format a été publié par le projet open-source
[crosspoint-tools](https://github.com/crosspoint-reader/crosspoint-tools)
(`unlocker-tool/crates/unlocker-core/src/xota.rs`). Firmware récupéré et
**déchiffré le 15/11/2026** :

- **Xteink stock V7.6.8** (2026-09-22), app image ESP32-S3 claire,
  sha256 `f68533a8c55c55144303605e6497a0178215d477ec2642375814e00612afe087`
- Copies locales : `~/Downloads/xteink-stock-V7.6.8-encrypted.xota` (chiffré)
  et `~/Downloads/xteink-stock-app-V7.6.8.bin` (clair, flashable)
- ⚠️ Ne pas publier ces binaires dans le dépôt public (copyright Xteink) —
  la méthode ci-dessous suffit à les régénérer.

### Comment le firmware a été obtenu (méthode reproductible)

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

