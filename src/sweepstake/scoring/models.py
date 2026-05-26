# Dataclasses for predictions, actuals, and score breakdowns.

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Part1Prediction:
    participant_name: str
    submitted_on: str | None
    group_picks: dict[str, tuple[str, str]]  # "A" -> (winner, runner_up)
    finalists: tuple[str | None, str | None]
    winner: str | None
    golden_boot_raw: str  # free text as submitted


@dataclass(frozen=True)
class Part2Prediction:
    participant_name: str
    r32_pairs: dict[str, tuple[str, str]]    # "L1" -> (team_a, team_b)
    r32_winners: dict[str, str | None]
    r16_winners: dict[str, str | None]
    qf_winners: dict[str, str | None]
    sf_winners: dict[str, str | None]
    champion: str | None
    tiebreaker_final_goals: int | None


@dataclass(frozen=True)
class Actuals:
    group_winners: dict[str, str]            # "A" -> team
    group_runners_up: dict[str, str]         # "A" -> team
    r32_winners: dict[str, str | None]
    r16_winners: dict[str, str | None]
    qf_winners: dict[str, str | None]
    sf_winners: dict[str, str | None]
    champion: str | None
    golden_boot_canonical: str | None        # manually resolved canonical name
    finalists_set: frozenset[str]            # the two teams in the final
    final_total_goals: int | None


@dataclass
class ScoreBreakdown:
    part1_group_winners: int = 0
    part1_group_runners_up: int = 0
    part1_finalists: int = 0
    part1_winner: int = 0
    part1_golden_boot: int = 0
    part2_r32: int = 0
    part2_r16: int = 0
    part2_qf: int = 0
    part2_sf: int = 0
    part2_champion: int = 0

    @property
    def part1_total(self) -> int:
        return (
            self.part1_group_winners
            + self.part1_group_runners_up
            + self.part1_finalists
            + self.part1_winner
            + self.part1_golden_boot
        )

    @property
    def part2_total(self) -> int:
        return (
            self.part2_r32
            + self.part2_r16
            + self.part2_qf
            + self.part2_sf
            + self.part2_champion
        )

    @property
    def grand_total(self) -> int:
        return self.part1_total + self.part2_total
