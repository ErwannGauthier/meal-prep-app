# Spike Instagram — résultats (2026-10-03)

Machine : PC de développement (sans GPU), connexion résidentielle, aucun cookie.
Outils : instaloader 4.15.x, yt-dlp 2026.08.19.

## 1. Lister les 12 dernières publications sans compte (instaloader)

Échec :

```
ConnectionException JSON Query to api/v1/users/web_profile_info/: 429 Too Many Requests
when accessing https://www.instagram.com/api/v1/users/web_profile_info/?username=bourr_
```

## 2. Lister le profil sans compte (yt-dlp)

Échec, comme attendu :

```
WARNING: The program functionality for this site has been marked as broken, and will probably not work.
ERROR: [instagram:user] bourr_: Unable to extract data
```

## 3. Télécharger l'audio d'un reel sans compte (yt-dlp)

**Non testé** : aucun lien de reel disponible (le listing a échoué et la recherche web n'en renvoie pas).
À faire avec un lien de la liste Notion, pendant l'essai de bout en bout (Task 14).

## 4. Avec cookies

**Non testé** : pas encore de `cookies.txt` de compte secondaire.

## Conclusions

- Le listing anonyme du profil ne fonctionne pas depuis cette machine : la récupération des
  nouveautés dépendra en pratique des cookies du compte secondaire. Le code prévoit déjà ce
  repli (essai anonyme, puis cookies, puis `Blocked` signalé dans le résumé sans interrompre
  le traitement de la file).
- Message de refus observé : `429 Too Many Requests`. Côté yt-dlp, `BLOCK_MARKERS` contient
  déjà `too many requests` et `http error 429`.
- instaloader avec cookies n'a pas pu être essayé : la condition d'arrêt « instaloader échoue
  même avec cookies » n'est donc pas vérifiée. La Task 10 est réalisée ; à revalider dès qu'un
  `cookies.txt` existe.

## Complément (essai de bout en bout, 2026-10-03)

`python -m pipeline run` lancé sans cookies sur un shortcode inexistant (`DAAAAAAAAAA`) :

```
ERROR: [Instagram] DAAAAAAAAAA: Instagram sent an empty media response. Check if this post is
accessible in your browser without being logged-in. If it is not, then use --cookies-from-browser
or --cookies for the authentication.
```

yt-dlp répond donc « use --cookies » aussi bien pour un reel supprimé que pour un accès refusé :
les deux cas sont indiscernables sur un seul reel. Conséquence dans `pipeline/app.py` : un refus
isolé est « suspect » ; deux refus de suite confirment le blocage et arrêtent le lancement ; un
téléchargement réussi juste après un refus classe le reel précédent en échec (lien mort).

Vérifié avec les vrais outils : conversion ffmpeg (WAV mono 16 kHz, WebP 480 px de large),
`whisper-cli` avec et sans `-ng`, `claude -p` avec le schéma d'extraction.
Reste à vérifier avec un vrai lien : le téléchargement yt-dlp d'un reel existant, sans puis avec cookies.
