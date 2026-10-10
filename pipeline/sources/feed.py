import logging
from collections.abc import Callable, Collection, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from ..errors import Blocked

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeedPost:
    shortcode: str
    pinned: bool = False


# Renvoie les reels du profil à la demande : les épinglés d'abord, puis du plus récent
# au plus ancien. S'arrêter de lire évite de charger les pages suivantes.
FetchFn = Callable[[str, Path | None], Iterable[FeedPost]]


def gallery_dl_fetch(username: str, cookies: Path | None) -> Iterator[FeedPost]:
    """Liste l'onglet Reels du profil avec gallery-dl (une requête par page de 12 reels).

    On s'appuie sur l'API interne de son extracteur Instagram, tenue à jour au fil des
    changements du site. On n'utilise que le listing : pas d'appel par reel.
    """
    from gallery_dl import config, extractor

    section = ("extractor", "instagram")
    config.set(section, "cookies", str(cookies) if cookies else None)
    config.set(section, "cookies-update", False)   # ne jamais réécrire le fichier de l'utilisateur
    config.set(section, "sleep-request", "2.0-4.0")
    ex = extractor.find(f"https://www.instagram.com/{username}/reels/")
    if ex is None:
        raise RuntimeError("gallery-dl ne reconnaît pas l'adresse du profil")
    ex.initialize()
    for reel in ex.api.user_reels(username):
        media = reel["media"]
        yield FeedPost(media["code"], pinned=bool(media.get("clips_tab_pinned_user_ids")))


class Feed:
    def __init__(self, username: str, cookies: Path | None, max_posts: int = 50,
                 fetch: FetchFn = gallery_dl_fetch):
        self.username = username
        self.cookies = cookies
        self.max_posts = max_posts
        self.fetch = fetch

    def latest_reels(self, known: Collection[str]) -> list[FeedPost]:
        """Reels inconnus du profil, dans l'ordre où les traiter (les plus anciens d'abord).

        Remonte l'onglet Reels jusqu'au premier reel déjà connu et non épinglé,
        dans la limite de `max_posts` reels lus.
        """
        new: list[FeedPost] = []
        read = 0
        # Toute exception est traitée comme un refus : gallery-dl lève des types variés
        # (connexion requise, trop de requêtes, format de réponse inattendu…), y compris
        # en cours de lecture, au chargement d'une page suivante.
        try:
            for post in self.fetch(self.username, self.cookies):
                read += 1
                if post.shortcode not in known:
                    new.append(post)
                elif not post.pinned:
                    break
                if read >= self.max_posts:
                    log.warning("Feed : %d reels lus sans retrouver un reel connu, arrêt.", read)
                    break
        except Exception as e:
            how = "avec les cookies" if self.cookies else "sans compte (configurer cookies_file)"
            raise Blocked(f"feed refusé {how} : {e}") from e
        # Lus du plus récent au plus ancien : on inverse. Les épinglés, anciens, passent en premier.
        return sorted(reversed(new), key=lambda p: not p.pinned)
