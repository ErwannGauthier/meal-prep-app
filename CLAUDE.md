# Meal preps @bourr_

Catalogue des meal preps publiés en reels par @bourr_. Deux parties indépendantes, reliées seulement par des fichiers JSON :

- `pipeline/` (Python 3.11) : récupère les reels, les transcrit (whisper.cpp) et en extrait les recettes (`claude -p`). Il écrit `web/public/data/recipes.json`, `ingredients.json` et `thumbs/`.
- `web/` (Vite, React, TypeScript) : site statique qui lit ces fichiers. Usage principal : iPhone.

Répondre en français.

## Où trouver quoi

- Spec (fait autorité) : `docs/superpowers/specs/2026-10-02-meal-prep-catalog-design.md`
- Plans d'implémentation, déjà exécutés : `docs/superpowers/plans/`
- Installation du pipeline sur le PC Debian (GPU AMD) : `docs/pipeline-setup.md`
- Ce qu'Instagram accepte ou refuse : `docs/superpowers/notes/2026-10-02-instagram-spike.md`

## Commandes

```bash
.venv/bin/pytest                      # tests du pipeline
cd web && npx vitest run              # tests du site
cd web && npm run build               # vérification des types + compilation
.venv/bin/python -m pipeline --help   # import, run, reextract, retry
```

## Conventions git

- Une branche par changement, fusionnée dans `main` en **un seul commit** (`git merge --squash`). Pas de fusion en avance rapide avec les commits de travail.
- Messages au format **gitmoji + type conventionnel** : `✨ feat(web): …`, `🐛 fix(pipeline): …`, `📝 docs: …`, `👷 ci: …`, `🔧 chore: …`. Les commits de données créés par le pipeline s'écrivent `🍱 data: …`.
- Le dépôt est **public**. Chaque clone doit utiliser l'adresse anonyme GitHub, sinon l'adresse personnelle se retrouve dans l'historique :
  ```bash
  git config user.email "78931821+ErwannGauthier@users.noreply.github.com"
  ```
- Ne jamais commiter `config.toml`, un fichier de cookies, ni `data/sources/` (descriptions et transcriptions du créateur : elles restent en local). Le `.gitignore` les couvre ; ne pas le contourner.
- Demander avant tout `push` forcé ou toute réécriture d'historique.

## Règles du projet

- Le pipeline se lance sur `main`, à jour avec `origin/main`, un seul lancement à la fois. Il ne crée un commit que si `web/public/data/` a changé.
- Tests écrits avant le code, pour le pipeline comme pour le site.
- Le contrat de données entre les deux parties est défini par `pipeline/models.py` et `web/src/types.ts` : toute modification de l'un se répercute sur l'autre.
- Design du site : direction « étiquette nutritionnelle » (police Archivo, couleurs réservées aux trois macros). Toute évolution visuelle passe par le skill `frontend-design`.

## État au 2026-10-10

L'import de la liste de liens est fait, depuis le PC Debian (whisper.cpp sur le GPU AMD). Le catalogue compte 147 recettes, des reels du 2023-07-12 au 2026-10-02, toutes avec miniature et macros, et 149 ingrédients. Deux liens morts sont en échec dans `data/state.json`, vérifiés à la main. Le site n'est pas publié.

Reste à faire :

1. **Détection des nouveaux reels.** Le listing fonctionne avec les cookies d'un compte secondaire (gallery-dl, vérifié le 2026-10-10 : 10 reels inconnus trouvés). Il reste à configurer `cookies_file` sur le PC Debian, à y réinstaller les dépendances (`.venv/bin/pip install -e .`) et à faire un premier lancement réel : `lastFeedCheck` vaut encore `null` dans `data/state.json`. Sans compte, Instagram refuse le listing.
2. **Régions manquantes.** 28 recettes n'ont pas de région et échappent au filtre par région.
3. **Publier.** Activer GitHub Pages (source « GitHub Actions »), puis remettre `push: branches: [main]` dans `.github/workflows/deploy.yml`, qui est en déclenchement manuel pour l'instant.
4. **Tester sur iPhone.** Le partage vers Notes, « Copier la liste », le retour arrière vers la liste filtrée, le champ de recherche, et le panneau d'ingrédients avec les 149 ingrédients réels.
