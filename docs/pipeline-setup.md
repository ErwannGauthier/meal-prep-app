# Installer le pipeline sur le PC Debian 12 (Radeon RX 7800 XT)

## 1. Paquets système

```bash
sudo apt update
sudo apt install -y git python3-venv ffmpeg cmake build-essential \
  libvulkan-dev glslc vulkan-tools mesa-vulkan-drivers
```

Vérifier que la carte est vue en Vulkan :

```bash
vulkaninfo --summary | grep -i deviceName
```

Il faut voir la carte avec le pilote RADV, par exemple `AMD Radeon Graphics (RADV GFX1101)` (le nom commercial n'apparaît pas forcément). Si seule `llvmpipe` apparaît, installer un Mesa plus récent :

```bash
echo "deb http://deb.debian.org/debian bookworm-backports main" | sudo tee /etc/apt/sources.list.d/backports.list
sudo apt update && sudo apt install -y -t bookworm-backports mesa-vulkan-drivers
```

Si la carte n'apparaît toujours pas, mettre `use_gpu = false` dans `config.toml` : tout fonctionne sur CPU, en plus lent.

## 2. whisper.cpp

Les en-têtes Vulkan de Debian 12 (1.3.239) sont trop anciens pour le backend Vulkan de whisper.cpp (erreur `'LayerSettingEXT' is not a member of 'vk'`), et les en-têtes SPIR-V ne sont pas installés (erreur `Could not find ... "SPIRV-Headers"`). On installe donc des versions récentes des deux dans `~/.local`, sans toucher au système. Ce ne sont que des en-têtes : la bibliothèque Vulkan et le pilote restent ceux de Debian.

```bash
git clone --depth 1 https://github.com/KhronosGroup/SPIRV-Headers /tmp/SPIRV-Headers
cmake -S /tmp/SPIRV-Headers -B /tmp/SPIRV-Headers/build -DCMAKE_INSTALL_PREFIX=$HOME/.local
cmake --install /tmp/SPIRV-Headers/build

git clone --depth 1 https://github.com/KhronosGroup/Vulkan-Headers /tmp/Vulkan-Headers
cmake -S /tmp/Vulkan-Headers -B /tmp/Vulkan-Headers/build \
  -DCMAKE_INSTALL_PREFIX=$HOME/.local -DVULKAN_HEADERS_ENABLE_MODULE=OFF
cmake --install /tmp/Vulkan-Headers/build
```

Puis whisper.cpp, en pointant cmake sur ces en-têtes :

```bash
git clone https://github.com/ggml-org/whisper.cpp ~/whisper.cpp
cd ~/whisper.cpp
cmake -B build -DGGML_VULKAN=1 -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH=$HOME/.local \
  -DVulkan_INCLUDE_DIR=$HOME/.local/include \
  -DCMAKE_CXX_FLAGS=-I$HOME/.local/include
cmake --build build -j --config Release
sh ./models/download-ggml-model.sh large-v3-turbo
sh ./models/download-ggml-model.sh small
./build/bin/whisper-cli -m models/ggml-large-v3-turbo.bin -f samples/jfk.wav
```

Dans la sortie, les lignes `ggml_vulkan: 0 = AMD Radeon Graphics (RADV ...)` et `whisper_backend_init_gpu: using Vulkan0 backend` confirment l'utilisation du GPU. Vérifié le 2026-10-06 sur ce PC : l'échantillon est transcrit en 8 s environ.

## 3. Claude Code

```bash
curl -fsSL https://claude.ai/install.sh | bash
claude   # se connecter une fois avec ton compte, puis /exit
```

## 4. Le dépôt

```bash
git clone git@github.com:<ton-pseudo>/meal-prep-app.git ~/meal-prep-app
cd ~/meal-prep-app
python3 -m venv .venv
.venv/bin/pip install -e .
cp config.example.toml config.toml
```

`git push` doit fonctionner sans mot de passe (clé SSH ajoutée à GitHub) : tester avec `git push --dry-run`.

Le pipeline se lance **sur la branche `main`, à jour avec `origin/main`**. Avant chaque lancement :

```bash
git switch main
git pull --ff-only
git status -sb        # doit afficher « ## main...origin/main », sans « behind »
```

Si `main` est en retard sur `origin/main`, le `git push` de fin de lancement est refusé.

## 5. Cookies du compte Instagram secondaire (recommandé)

Sans cookies, Instagram refuse de lister le profil (réponse « require_login », constatée le 2026-10-10) : les nouveaux reels ne sont pas détectés automatiquement. L'import d'une liste de liens, lui, fonctionne sans compte.

Avec des cookies, chaque lancement lit l'onglet Reels du profil, du reel le plus récent jusqu'au premier reel déjà connu, puis s'arrête. Les reels épinglés en tête de profil ne comptent pas comme signal d'arrêt. La lecture se fait avec gallery-dl et coûte deux requêtes quand il y a moins de 12 nouveautés. Elle s'arrête de toute façon après 50 reels.

Le compte ne sert qu'à cette lecture : les téléchargements se font sans compte, et les cookies n'y servent qu'en secours. Le fichier de cookies n'est jamais réécrit par le pipeline.

Après avoir mis à jour le dépôt, réinstaller les dépendances (gallery-dl a remplacé instaloader) : `.venv/bin/pip install -e .`

1. Dans Firefox, se connecter à instagram.com avec le compte secondaire.
2. Exporter les cookies au format Netscape (extension « cookies.txt ») dans `~/meal-prep-app/cookies.txt`. Garder « cookies » dans le nom du fichier : c'est ce qui le fait ignorer par git.
3. `chmod 600 cookies.txt`, puis dans `config.toml` : `cookies_file = "~/meal-prep-app/cookies.txt"`.

`*cookies*.txt` est ignoré par git : il ne sera jamais publié.

## 6. Premier lancement : l'historique Notion

1. Dans Notion : `•••` → Exporter → Markdown & CSV → télécharger le `.zip`.
2. Ajouter les liens à la file :

```bash
.venv/bin/python -m pipeline import ~/Téléchargements/Export-xxxx.zip
```

3. Lancer le traitement. Chaque lancement traite au maximum `max_reels_per_run` reels. Relancer jusqu'à épuisement de la file, en espaçant les lancements si Instagram bloque :

```bash
.venv/bin/python -m pipeline run
```

## 7. Lancement automatique chaque semaine

`crontab -e`, puis ajouter (dimanche à 10 h) :

```cron
PATH=/home/<user>/.local/bin:/usr/local/bin:/usr/bin:/bin
0 10 * * 0 cd /home/<user>/meal-prep-app && git pull -q --ff-only && .venv/bin/python -m pipeline run >> data/work/run.log 2>&1
```

## Ce qui est publié, ce qui reste sur ce PC

- **Publié** (dépôt public) : `web/public/data/` (recettes, ingrédients, miniatures des recettes retenues) et `data/state.json` (suivi des reels).
- **Local uniquement** : `data/sources/` (descriptions, transcriptions et miniatures en attente). Ce dossier est ignoré par git. Il sert à `reextract` : s'il est perdu, il faut retélécharger les reels. Pense à le sauvegarder si tu changes de machine.
- Un commit n'est créé que s'il y a du nouveau pour le site. Un lancement sans nouvelle recette ne laisse aucune trace dans l'historique.

## Commandes utiles

| Commande | Effet |
|---|---|
| `python -m pipeline run --no-publish` | traite sans pousser |
| `python -m pipeline run --cpu` | force whisper.cpp sur CPU |
| `python -m pipeline reextract` | relance l'extraction de toutes les recettes (après une amélioration du prompt) |
| `python -m pipeline reextract C9xYz12AbC` | relance une seule recette |
| `python -m pipeline retry` | remet dans la file tous les reels en échec (ou seulement ceux dont on donne le code) |

## Lire le résumé d'un lancement

- **« Arrêt anticipé »** : le lancement s'est arrêté avant la fin de la file, parce qu'Instagram refuse l'accès ou que Claude est indisponible (non connecté, quota atteint). Rien n'est perdu : relancer plus tard reprend au même endroit.
- **« reel inaccessible »** : Instagram répond pour d'autres reels mais pas pour celui-ci. Le lien est sans doute mort (reel supprimé ou privé).
- **« a interrompu 5 lancements de suite »** : le même reel a arrêté cinq lancements sans qu'on puisse dire s'il était en cause. Il est mis de côté pour que la file avance.
- **« 3 échecs consécutifs »** : trois reels de suite ont échoué. Le problème vient sans doute de l'installation (whisper, ffmpeg, yt-dlp), pas des reels. Corriger, puis `python -m pipeline retry`.
- **« Installation incomplète »** : un outil ou un fichier manque. Rien n'est traité tant que ce n'est pas corrigé.
- **« Un autre lancement est déjà en cours »** : un seul lancement à la fois est autorisé, pour ne jamais faire deux téléchargements Instagram en parallèle.

Code de sortie de la commande : `0` terminé, `1` arrêt anticipé ou publication en échec, `2` configuration ou installation à corriger, `3` autre lancement en cours.

Les reels en échec sont listés dans `data/state.json` (`"status": "failed"`, champ `error`). Après correction de la cause, `python -m pipeline retry` les remet dans la file.
