class PipelineError(Exception):
    """Erreur de base du pipeline."""


class Blocked(PipelineError):
    """Instagram refuse l'accès (connexion requise, trop de requêtes)."""


class ClaudeUnavailable(PipelineError):
    """claude -p est inutilisable (non connecté, quota atteint, binaire absent)."""


class ReelError(PipelineError):
    """Échec limité à un seul reel ; le lancement continue."""


class PublishError(PipelineError):
    """git add/commit/push a échoué."""


class IntegrityError(PipelineError):
    """Les données violeraient l'intégrité référentielle."""
