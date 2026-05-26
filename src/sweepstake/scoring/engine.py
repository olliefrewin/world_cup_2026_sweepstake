# Pure scoring functions. No I/O, no database access, no API calls.

from __future__ import annotations

from sweepstake.constants import (
    GROUP_LETTERS,
    POINTS_CHAMPION,
    POINTS_FINALIST,
    POINTS_GOLDEN_BOOT,
    POINTS_GROUP_RUNNER_UP,
    POINTS_GROUP_WINNER,
    POINTS_QF_WINNER,
    POINTS_R16_WINNER,
    POINTS_R32_WINNER,
    POINTS_SF_WINNER,
    POINTS_WINNER,
    QF_ALL_SLOTS,
    R16_ALL_SLOTS,
    R32_ALL_SLOTS,
    SF_SLOTS,
)
from sweepstake.scoring.models import Actuals, Part1Prediction, Part2Prediction, ScoreBreakdown


def score_part1(
    prediction: Part1Prediction,
    actuals: Actuals,
    golden_boot_matched: bool = False,
) -> ScoreBreakdown:
    # golden_boot_matched: caller resolves this from the golden_boot_resolutions table
    # so the engine stays pure (no DB access).
    bd = ScoreBreakdown()

    # Group stage
    for g in GROUP_LETTERS:
        pred_winner, pred_runner = prediction.group_picks.get(g, ("", ""))
        if pred_winner and actuals.group_winners.get(g) and pred_winner == actuals.group_winners[g]:
            bd.part1_group_winners += POINTS_GROUP_WINNER
        if (
            pred_runner
            and actuals.group_runners_up.get(g)
            and pred_runner == actuals.group_runners_up[g]
        ):
            bd.part1_group_runners_up += POINTS_GROUP_RUNNER_UP

    # Finalists -- set-based with duplicate guard (see spec s2 edge cases)
    # Using a set() deduplicates so picking the same team twice only scores once.
    unique_picks = {p for p in prediction.finalists if p}
    for pick in unique_picks:
        if pick in actuals.finalists_set:
            bd.part1_finalists += POINTS_FINALIST

    # World Cup winner
    if prediction.winner and actuals.champion and prediction.winner == actuals.champion:
        bd.part1_winner += POINTS_WINNER

    # Golden Boot -- only score if the caller confirmed this participant's pick was matched
    if actuals.golden_boot_canonical and golden_boot_matched:
        bd.part1_golden_boot += POINTS_GOLDEN_BOOT

    return bd


def score_part2(prediction: Part2Prediction, actuals: Actuals) -> ScoreBreakdown:
    bd = ScoreBreakdown()

    for slot in R32_ALL_SLOTS:
        pred = prediction.r32_winners.get(slot)
        actual = actuals.r32_winners.get(slot)
        if pred and actual and pred == actual:
            bd.part2_r32 += POINTS_R32_WINNER

    for slot in R16_ALL_SLOTS:
        pred = prediction.r16_winners.get(slot)
        actual = actuals.r16_winners.get(slot)
        if pred and actual and pred == actual:
            bd.part2_r16 += POINTS_R16_WINNER

    for slot in QF_ALL_SLOTS:
        pred = prediction.qf_winners.get(slot)
        actual = actuals.qf_winners.get(slot)
        if pred and actual and pred == actual:
            bd.part2_qf += POINTS_QF_WINNER

    for slot in SF_SLOTS:
        pred = prediction.sf_winners.get(slot)
        actual = actuals.sf_winners.get(slot)
        if pred and actual and pred == actual:
            bd.part2_sf += POINTS_SF_WINNER

    if prediction.champion and actuals.champion and prediction.champion == actuals.champion:
        bd.part2_champion += POINTS_CHAMPION

    return bd


def combine_scores(part1: ScoreBreakdown, part2: ScoreBreakdown) -> ScoreBreakdown:
    # Merge two ScoreBreakdown objects into one (for display purposes).
    combined = ScoreBreakdown()
    combined.part1_group_winners = part1.part1_group_winners
    combined.part1_group_runners_up = part1.part1_group_runners_up
    combined.part1_finalists = part1.part1_finalists
    combined.part1_winner = part1.part1_winner
    combined.part1_golden_boot = part1.part1_golden_boot
    combined.part2_r32 = part2.part2_r32
    combined.part2_r16 = part2.part2_r16
    combined.part2_qf = part2.part2_qf
    combined.part2_sf = part2.part2_sf
    combined.part2_champion = part2.part2_champion
    return combined


def tiebreaker_distance(prediction: Part2Prediction, actuals: Actuals) -> int:
    # Lower is better. Returns a large sentinel if either value is unknown.
    _UNKNOWN = 999_999
    if actuals.final_total_goals is None or prediction.tiebreaker_final_goals is None:
        return _UNKNOWN
    return abs(prediction.tiebreaker_final_goals - actuals.final_total_goals)


def leaderboard_sort_key(
    name: str,
    grand_total: int,
    tb_distance: int,
) -> tuple:
    # Sort descending by total, then ascending by tiebreaker distance, then alphabetical by name.
    return (-grand_total, tb_distance, name.lower())


