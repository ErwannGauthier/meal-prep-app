from collections.abc import Iterable
from datetime import datetime, timezone

from .models import ReelState, SourceKind, State, Status


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def add_pending(state: State, reel_ids: Iterable[str], source: SourceKind) -> list[str]:
    added: list[str] = []
    for rid in reel_ids:
        if rid in state.reels:
            continue
        state.reels[rid] = ReelState(source=source, updatedAt=now_iso())
        added.append(rid)
    return added


def select_batch(state: State, limit: int, max_attempts: int) -> list[str]:
    """Reels à traiter, dans l'ordre d'ajout (les plus anciens d'abord)."""
    batch: list[str] = []
    for rid, reel in state.reels.items():
        retryable = reel.status == "failed" and reel.attempts < max_attempts
        if reel.status == "pending" or retryable:
            batch.append(rid)
            if len(batch) >= limit:
                break
    return batch


def record_attempt(state: State, reel_id: str, status: Status, error: str | None = None) -> None:
    reel = state.reels[reel_id]
    reel.status = status
    reel.error = error
    reel.attempts += 1
    reel.stalls = 0
    reel.updatedAt = now_iso()


def give_up(state: State, reel_id: str, error: str, max_attempts: int) -> None:
    """Échec définitif, à vérifier à la main : le reel n'est plus jamais repris."""
    record_attempt(state, reel_id, "failed", error)
    state.reels[reel_id].attempts = max(state.reels[reel_id].attempts, max_attempts)


def stall(state: State, reel_id: str, error: str, limit: int, max_attempts: int) -> bool:
    """Le lancement s'arrête sur ce reel sans qu'on sache si le reel est en cause.

    Au bout de `limit` lancements interrompus, le reel est abandonné (True) pour
    que la file avance ; `retry_failed` permet de le reprendre.
    """
    reel = state.reels[reel_id]
    reel.stalls += 1
    reel.updatedAt = now_iso()
    if reel.stalls < limit:
        return False
    count = reel.stalls
    give_up(state, reel_id, f"a interrompu {count} lancements de suite : {error}", max_attempts)
    return True


def retry_failed(state: State, reel_ids: Iterable[str] | None) -> list[str]:
    """Remet en file les reels en échec (tous, ou seulement ceux de `reel_ids`)."""
    wanted = None if reel_ids is None else set(reel_ids)
    requeued: list[str] = []
    for rid, reel in state.reels.items():
        if reel.status != "failed" or (wanted is not None and rid not in wanted):
            continue
        reel.status, reel.attempts, reel.stalls, reel.error = "pending", 0, 0, None
        reel.updatedAt = now_iso()
        requeued.append(rid)
    return requeued
