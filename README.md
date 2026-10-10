# Meal preps @bourr_

Catalogue des meal preps publiés en reels par @bourr_ : recettes, ingrédients, macros par portion et liste de courses exportable vers Notes.

- `pipeline/` : script Python qui récupère les reels, les transcrit (whisper.cpp) et en extrait les recettes (Claude). Installation : [docs/pipeline-setup.md](docs/pipeline-setup.md).
- `web/` : site React statique, en ligne sur https://erwanngauthier.github.io/meal-prep-app/. Il est republié à chaque push sur `main` qui touche `web/` (GitHub Pages, source « GitHub Actions »).

## Développer le site

    cd web
    npm install
    npm run dev        # http://localhost:5173
    npx vitest run     # tests

## Tests du pipeline

    .venv/bin/pytest
