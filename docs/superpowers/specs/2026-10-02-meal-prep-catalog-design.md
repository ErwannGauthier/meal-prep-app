# Catalogue des meal preps de @bourr_ — Design

Date : 2026-10-02
Statut : validé en brainstorming, en attente de relecture

## 1. Objectif

Cataloguer l'intégralité des meal preps publiés en reels par le compte Instagram **@bourr_** dans un site web consultable principalement sur iPhone.

**Critère de réussite :** depuis l'iPhone, on ouvre le site, on trouve une recette en filtrant par ingrédient, et on envoie sa liste de courses dans l'app Notes.

### Périmètre

Inclus :
- Un pipeline local qui récupère les reels, transcrit l'audio et extrait une recette structurée (nom, ingrédients, étapes, macros, région, lien).
- Un site React statique hébergé sur GitHub Pages : liste filtrable + fiche recette + export de la liste de courses.

Exclus (YAGNI) :
- Plusieurs comptes Instagram (un seul compte, définitivement).
- Mode hors ligne / PWA (le site est en ligne sur GitHub Pages).
- Panier multi-recettes avec fusion des quantités.
- Budget / nombre de jours comme critères (toujours ~5 jours / 20 € chez ce créateur, pas discriminant).
- Backend, base de données, authentification.

## 2. Contraintes et décisions

| Sujet | Décision | Raison |
|---|---|---|
| Hébergement | GitHub Pages, dépôt **public** | Gratuit ; aucune donnée personnelle. Balise `noindex` ajoutée. |
| Stockage | Fichiers JSON versionnés dans le dépôt | Quelques centaines de recettes ; filtrage côté client. |
| Backend | Aucun | Le site est statique ; le pipeline est un script local. |
| Machine du pipeline | PC Debian 12, Radeon RX 7800 XT | Choix utilisateur. Doit aussi tourner en CPU seul. |
| Transcription | whisper.cpp compilé avec Vulkan, option `--no-gpu` | Supporte la RX 7800 XT sans ROCm ; même binaire en GPU et en CPU. |
| Extraction | `claude -p` (abonnement Claude Code) | Pas de clé API à gérer, bonne qualité d'extraction en français. |
| Historique | Import d'un export Notion contenant les liens des reels | Évite de lister tout le profil (fragile, nécessite connexion). |
| Nouveautés | Lecture anonyme des ~12 dernières publications, repli sur cookies d'un compte secondaire | Lancement au moins hebdomadaire suffit. |
| Site | Vite + React + TypeScript, React Router en mode hash | Préférence utilisateur ; le mode hash évite le problème de fallback SPA sur Pages. |

Hypothèses validées :
- La liste Notion ne contient que des meal preps.
- La région d'origine est déduite par Claude.
- Les miniatures sont téléchargées et stockées compressées (WebP) dans le dépôt.
- Le site est en français.

## 3. Architecture

```
meal-prep-app/
├── pipeline/                    # Python 3.11, tourne sur le PC Debian
├── web/                         # Vite + React + TS
│   └── public/data/
│       ├── recipes.json         # écrit par le pipeline, lu par le site
│       ├── ingredients.json     # référentiel d'ingrédients
│       └── thumbs/<id>.webp
├── data/
│   ├── state.json               # statut de chaque reel connu
│   └── sources/                 # LOCAL, ignoré par git : <id>.json (description + transcription), <id>.webp (miniature en attente)
├── config.example.toml          # config.toml et cookies : ignorés par git
├── .gitignore
└── .github/workflows/deploy.yml
```

Flux : `pipeline run` → écrit JSON + miniatures → `git commit && git push` → GitHub Action build Vite → déploiement GitHub Pages.

`config.toml` et le fichier de cookies Instagram sont listés dans `.gitignore` : le dépôt étant public, ils ne doivent jamais être commités. `publish` n'ajoute que `web/public/data/` et `data/state.json`.

Décisions du 2026-10-03 (après essai réel et relecture) :
- `data/sources/` reste en local (ignoré par git) : les descriptions et transcriptions du créateur ne sont pas publiées.
- La miniature d'un reel est gardée dans `data/sources/` et copiée dans `web/public/data/thumbs/` seulement quand la recette est retenue : les reels écartés ne laissent rien sur le site.
- `publish` ne crée un commit que si `web/public/data/` a changé ; `data/state.json` part alors dans le même commit.
- Un seul lancement à la fois (verrou) ; code de sortie non nul en cas d'arrêt anticipé.
- yt-dlp répond la même chose pour un reel supprimé et pour un blocage : en cas de refus, le pipeline sonde un reel déjà traité pour trancher ; un reel qui interrompt 5 lancements de suite est abandonné ; `python -m pipeline retry` remet en file les reels en échec.

Le **seul contrat** entre le pipeline et le site est le format de `recipes.json` et `ingredients.json` (section 4). Le pipeline ignore React ; le site ignore Instagram.

## 4. Modèle de données

### 4.1 `ingredients.json` — référentiel

```json
[
  { "id": "poulet", "name": "Poulet", "category": "viandes-poissons" },
  { "id": "lait-de-coco", "name": "Lait de coco", "category": "epicerie" }
]
```

- `id` : slug unique, minuscules, sans accents, mots séparés par `-`.
- `name` : libellé affiché, au singulier.
- `category` : une valeur de la liste fermée suivante, dans cet ordre (ordre d'affichage des rayons) :

| Valeur | Libellé affiché |
|---|---|
| `viandes-poissons` | Viandes & poissons |
| `fruits-legumes` | Fruits & légumes |
| `feculents` | Féculents |
| `produits-laitiers-oeufs` | Produits laitiers & œufs |
| `epicerie` | Épicerie |
| `epices-condiments` | Épices & condiments |
| `surgeles` | Surgelés |
| `autre` | Autre |

### 4.2 `recipes.json`

```json
[
  {
    "id": "C9xYz12AbC",
    "title": "Poulet satay coco",
    "url": "https://www.instagram.com/reel/C9xYz12AbC/",
    "postedAt": "2026-05-14",
    "thumbnail": "thumbs/C9xYz12AbC.webp",
    "region": "Asie du Sud-Est",
    "portions": 5,
    "ingredients": [
      { "ingredientId": "poulet", "quantity": 1, "unit": "kg", "raw": "1 kg de blanc de poulet" }
    ],
    "steps": ["Couper le poulet en dés.", "…"],
    "macros": { "kcal": 620, "protein": 48, "carbs": 55, "fat": 22, "source": "estimated" },
    "extractedAt": "2026-10-02T21:00:00Z"
  }
]
```

Règles :
- `id` : shortcode Instagram, clé unique.
- `postedAt` : date ISO `YYYY-MM-DD`, ou `null` si inconnue.
- `thumbnail` : chemin relatif à `web/public/data/`, ou `null` si la miniature n'a pas pu être récupérée.
- `region` : chaîne libre courte (ex. « Asie du Sud-Est », « Mexique », « France ») ou `null`. Claude reçoit la liste des régions déjà utilisées pour rester cohérent.
- `portions` : entier ou `null`.
- `ingredients[].ingredientId` : doit exister dans `ingredients.json` (vérifié par le pipeline).
- `ingredients[].quantity` : nombre ou `null` (ex. « sel »). `unit` : chaîne ou `null`. `raw` : ligne lisible utilisée pour la liste de courses.
- `macros` : **par portion**, en kcal et grammes. `source` vaut `announced` (donné par le créateur dans la vidéo ou la description) ou `estimated` (calculé par Claude à partir des ingrédients). `macros` vaut `null` si aucune estimation n'est possible (quantités absentes).
- Le fichier est trié par `postedAt` décroissant.

### 4.3 `data/state.json`

```json
{
  "reels": {
    "C9xYz12AbC": { "status": "done", "source": "notion", "attempts": 1, "error": null, "updatedAt": "…" }
  },
  "lastFeedCheck": "2026-10-02T21:00:00Z"
}
```

`status` ∈ `pending` | `done` | `not_meal_prep` | `failed`. `source` ∈ `notion` | `feed`.

## 5. Pipeline

### 5.1 Commandes

```
python -m pipeline import <export-notion>   # ajoute les liens de l'export en "pending"
python -m pipeline run                      # traite les pending + nouveautés, puis publie
python -m pipeline reextract [id]           # ré-exécute l'extraction depuis les transcriptions
```

`run` accepte `--no-publish` (pas de git push) et `--cpu` (force whisper.cpp en CPU).
`reextract` relit `data/sources/<id>.json` (aucun accès Instagram) ; sans `id`, il ré-extrait toutes les recettes `done`.

### 5.2 Modules

| Module | Responsabilité |
|---|---|
| `config` | Charge `config.toml` : compte, mode GPU/CPU, chemins des modèles Whisper (GPU et CPU), délai min/max entre téléchargements, nombre max de reels par lancement (défaut 30), chemin du fichier de cookies, nombre max de tentatives (défaut 3). |
| `sources/notion` | Extrait les shortcodes depuis un export Notion (CSV, Markdown ou texte brut) par regex sur `instagram.com/(reel\|p)/<shortcode>`. Dédoublonne. |
| `sources/feed` | Récupère les ~12 dernières publications de @bourr_ (shortcode, date, description). Essai anonyme, puis avec cookies si refus. Bibliothèque pressentie : instaloader — **à valider par un spike en début de plan**. |
| `downloader` | Via yt-dlp : audio seul converti en WAV mono 16 kHz (ffmpeg), métadonnées (description, date), miniature convertie en WebP (largeur max 480 px). Utilise les cookies si configurés et que l'essai anonyme échoue. |
| `transcriber` | Appelle whisper.cpp en français. GPU : modèle large (ex. `large-v3-turbo`). CPU : modèle plus léger (ex. `small`). Écrit `data/sources/<id>.json` (`caption`, `transcript`, `postedAt`), supprime le WAV. |
| `extractor` | Un appel `claude -p` par reel. Entrées : description, transcription, référentiel d'ingrédients, liste des régions existantes. Sortie : soit `{"isMealPrep": false}`, soit la recette + les nouveaux ingrédients à créer. Validée par pydantic ; 1 nouvel essai si invalide, sinon `failed`. |
| `store` | Lecture/écriture atomique (fichier temporaire + rename) de `recipes.json`, `ingredients.json`, `state.json`. Vérifie l'intégrité référentielle avant écriture. |
| `publish` | `git add` des fichiers de données, `git commit`, `git push` — uniquement s'il y a des changements. |

### 5.3 Déroulé de `run`

1. Interroger le feed ; ajouter en `pending` (source `feed`) les shortcodes inconnus.
2. Prendre jusqu'à N reels `pending` ou `failed` (avec `attempts` < max), les plus anciens en premier.
3. Pour chacun : télécharger → transcrire → extraire → enregistrer → mettre à jour le statut. Pause aléatoire entre deux téléchargements.
4. Les reels issus de Notion sont considérés comme meal preps : si Claude répond `isMealPrep: false` pour l'un d'eux, il est marqué `failed` avec l'erreur « classé non meal prep » pour vérification manuelle, plutôt qu'ignoré.
5. Publier.

### 5.4 Gestion des erreurs

- **Blocage Instagram** (connexion requise, HTTP 429, rate limit) : arrêt propre de la boucle, sauvegarde de l'état, publication de ce qui a été traité. Le lancement suivant reprend.
- **Échec sur un reel** (téléchargement, transcription, extraction invalide) : statut `failed`, `attempts` incrémenté, message d'erreur enregistré ; on passe au reel suivant.
- **whisper.cpp GPU en échec** : nouvel essai automatique en CPU pour ce reel.
- **`claude -p` indisponible** (non connecté, quota) : arrêt propre comme pour un blocage Instagram ; les transcriptions déjà faites sont conservées et l'extraction reprendra au lancement suivant.
- **Échec du `git push`** : message d'erreur explicite ; les données restent commitées localement.
- Fin de lancement : résumé en console (traités, nouvelles recettes, ignorés, échecs avec raisons).

## 6. Site web

### 6.1 Stack

Vite + React + TypeScript, React Router en mode hash (`/#/`, `/#/recette/<id>`). Conçu mobile d'abord. `base` Vite réglée sur le nom du dépôt. Balise `<meta name="robots" content="noindex">`. Plugin frontend-design.

### 6.2 Données

Au démarrage : chargement de `data/recipes.json` et `data/ingredients.json`, construction d'un index ingrédient → recettes en mémoire. Les types TypeScript `Recipe`, `RecipeIngredient`, `Ingredient`, `Macros` reprennent la section 4.

### 6.3 Page d'accueil

- Grille de cartes : miniature, nom, région, protéines et kcal par portion.
- Recherche texte sur le nom (insensible à la casse et aux accents).
- Filtre ingrédients : sélection multiple, groupée par rayon ; une recette s'affiche si elle contient **tous** les ingrédients sélectionnés.
- Filtre région : sélection unique.
- Tri : plus récentes (défaut), plus de protéines, moins de kcal, meilleur ratio protéines/kcal. Les recettes sans macros sont placées en fin de liste pour les tris par macros.
- L'état des filtres est stocké dans les paramètres de l'URL, pour que le retour depuis une recette restaure la liste filtrée.
- État vide : message « Aucune recette ne correspond » + bouton pour réinitialiser les filtres.

### 6.4 Page recette

- Miniature, nom, région, bouton « Voir le reel » (lien Instagram).
- Macros par portion avec badge « estimé » si `source = estimated` ; nombre de portions.
- Ingrédients groupés par rayon (ordre de la section 4.1), affichant `raw`.
- Étapes numérotées.
- Bouton « Liste de courses → Notes » : `navigator.share({ text })` (feuille de partage iOS). Si `navigator.share` est indisponible ou échoue (hors annulation), bouton « Copier » via le presse-papiers.
- Id inconnu : message « Recette introuvable » + lien vers l'accueil.

Format du texte exporté :

```
Poulet satay coco — courses

Viandes & poissons
1 kg de blanc de poulet

Épicerie
400 ml de lait de coco
```

Rayons sans ingrédient omis. Dans Notes, l'utilisateur peut convertir le texte en liste à cocher.

### 6.5 Organisation du code

- Logique pure, sans React : `filterRecipes`, `sortRecipes`, `buildIngredientIndex`, `formatShoppingList`, `normalizeText`.
- Composants de présentation : `RecipeGrid`, `RecipeCard`, `Filters`, `RecipePage`, `ShareButton`.

### 6.6 Déploiement

GitHub Action sur push `main` : `npm ci` → `vite build` → déploiement GitHub Pages (`actions/deploy-pages`).

## 7. Tests

Pipeline (pytest) :
- Tests unitaires : parsing Notion (CSV, Markdown, texte), `store` (écriture atomique, intégrité référentielle), validation du schéma d'extraction, transitions de statut et sélection des reels à traiter.
- yt-dlp, instaloader, whisper.cpp et `claude -p` derrière des interfaces, remplacées par des faux dans les tests.
- Test manuel de bout en bout sur 2–3 vrais reels.

Site (Vitest + Testing Library) :
- Tests unitaires de `filterRecipes`, `sortRecipes`, `formatShoppingList`, `normalizeText`.
- Tests de composants : filtres appliqués à la grille, page recette, repli « Copier » du bouton de partage.

## 8. Risques à lever en début d'implémentation

1. **Listing du profil Instagram** : vérifier qu'instaloader (ou à défaut yt-dlp) récupère les dernières publications anonymement et avec cookies.
2. **whisper.cpp + Vulkan sur Debian 12** : vérifier que le Mesa de Debian 12 gère la RX 7800 XT en Vulkan compute ; sinon Mesa de `bookworm-backports`.
3. **Sortie structurée de `claude -p`** : vérifier les options disponibles (`--output-format json`, schéma) ; à défaut, extraction du JSON de la réponse texte puis validation pydantic.
