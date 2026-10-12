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
.venv/bin/python -m pipeline --help   # import, run, reextract, retry, accept, remove
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

## État au 2026-10-12

Le catalogue compte 149 recettes, des reels du 2023-07-12 au 2026-10-09, toutes avec miniature et macros, et 149 ingrédients. Dans `data/state.json` : 149 reels traités, 11 écartés comme « non meal prep », et deux liens morts en échec, vérifiés à la main.

Le site est publié depuis le 2026-10-10 : https://erwanngauthier.github.io/meal-prep-app/. GitHub Pages utilise la source « GitHub Actions ». Le workflow `.github/workflows/deploy.yml` republie le site à chaque push sur `main` qui touche `web/`, donc à chaque commit de données du pipeline.

La détection des nouveaux reels fonctionne sur le PC Debian avec les cookies du compte secondaire (`cookies.txt` à la racine, ignoré par git). Premier lancement réel le 2026-10-12 : 13 reels trouvés, 2 meal preps retenus.

Le créateur publie aussi des recettes à la portion, des desserts, des tests de « recettes virales » et des vidéos de musculation. Seuls les vrais meal preps (plusieurs repas complets préparés en une fois) sont retenus : le critère est dans le prompt de `pipeline/extractor.py`, avec « en cas de doute, écarter ». Le résumé d'un lancement liste les reels écartés avec un doute (lien et motif, repris dans `state.json` avec le préfixe `doute :`). Corrections à la main : `accept <code>` réintègre un reel écarté à tort, `remove <code>` retire une recette retenue à tort.

Reste à faire :

1. **Lancement automatique.** Aucun cron n'est installé sur le PC Debian : le pipeline ne tourne que lancé à la main (section 7 de `docs/pipeline-setup.md`).
2. **Tester sur iPhone.** Le partage vers Notes, « Copier la liste », le retour arrière vers la liste filtrée, le champ de recherche, et le panneau d'ingrédients avec les 149 ingrédients réels. Rien de tout cela n'a encore été vérifié sur un vrai iPhone.
3. **Régions manquantes.** 28 recettes n'ont pas de région et échappent au filtre par région.
4. **Noms d'ingrédients.** Dans `ingredients.json`, les noms sont en minuscules et certains sont plus précis que leur identifiant (`riz` s'appelle « riz basmati », `asperges` « asperge verte »). Ils s'affichent tels quels dans les filtres.
5. **Critère meal prep.** Vérifié sur 44 reels seulement (les 13 du feed et 31 de la liste d'origine). À surveiller sur les prochains lancements, surtout les faux rejets.
