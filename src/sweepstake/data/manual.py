# Helpers for populating golden boot resolutions via fuzzy matching.
# Called once the admin sets the canonical golden boot winner in the Actuals tab.

from __future__ import annotations

import logging

from rapidfuzz import fuzz

from sweepstake.constants import GOLDEN_BOOT_FUZZY_THRESHOLD

log = logging.getLogger(__name__)


def compute_similarity(raw_text: str, canonical: str) -> float:
    # Returns a 0.0-1.0 similarity score between the raw pick and the canonical name.
    if not raw_text or not canonical:
        return 0.0
    score = fuzz.token_sort_ratio(raw_text.lower(), canonical.lower()) / 100.0
    return score


def seed_golden_boot_resolutions(repository, canonical: str) -> dict[str, int]:
    # For every Part 1 submission, compute similarity and create a resolution record.
    # Returns counts: {"pending": N, "auto_rejected": N}
    counts = {"pending": 0, "auto_rejected": 0}

    for row in repository.list_all_part1():
        pid = row["participant_id"]
        raw = row["golden_boot_raw"] or ""

        # Skip if already resolved
        existing = repository.list_golden_boot_resolutions()
        already_done = {r["participant_id"]: r["status"] for r in existing}
        if pid in already_done and already_done[pid] in ("matched", "rejected"):
            continue

        sim = compute_similarity(raw, canonical)
        if sim >= GOLDEN_BOOT_FUZZY_THRESHOLD:
            status = "pending"
            counts["pending"] += 1
        else:
            status = "auto_rejected"
            counts["auto_rejected"] += 1

        repository.upsert_golden_boot_resolution(pid, raw, status)
        log.debug("Golden boot: participant %d, raw='%s', sim=%.2f, status=%s", pid, raw, sim, status)

    return counts
