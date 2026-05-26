"""
Canonical reference data for the 2026 FIFA World Cup sweepstake.
All team names, group structures, bracket topology and scoring weights are defined here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Groups (12 × 4 teams)
# ---------------------------------------------------------------------------

GROUPS: dict[str, list[str]] = {
    "A": ["Mexico", "South Africa", "South Korea", "Czech Republic"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Türkiye"],
    "E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

# Flat set of all 48 teams for quick membership checks
ALL_TEAMS: frozenset[str] = frozenset(t for teams in GROUPS.values() for t in teams)

GROUP_LETTERS: list[str] = list(GROUPS.keys())  # ["A", "B", ..., "L"]

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

POINTS_GROUP_WINNER: int = 10
POINTS_GROUP_RUNNER_UP: int = 5
POINTS_FINALIST: int = 15         # per finalist correctly named (set-based)
POINTS_WINNER: int = 25
POINTS_GOLDEN_BOOT: int = 15

POINTS_R32_WINNER: int = 3
POINTS_R16_WINNER: int = 5
POINTS_QF_WINNER: int = 8
POINTS_SF_WINNER: int = 12
POINTS_CHAMPION: int = 20

MAX_PART1: int = (
    POINTS_GROUP_WINNER * 12
    + POINTS_GROUP_RUNNER_UP * 12
    + POINTS_FINALIST * 2
    + POINTS_WINNER
    + POINTS_GOLDEN_BOOT
)  # 250
MAX_PART2: int = (
    POINTS_R32_WINNER * 16
    + POINTS_R16_WINNER * 8
    + POINTS_QF_WINNER * 4
    + POINTS_SF_WINNER * 2
    + POINTS_CHAMPION
)  # 164
MAX_TOTAL: int = MAX_PART1 + MAX_PART2  # 414

# ---------------------------------------------------------------------------
# Knockout bracket topology
# ---------------------------------------------------------------------------
#
# Slot IDs: L1–L8 (left half) and R1–R8 (right half) for R32.
# Parent chain: each R32 feeds an R16 slot, which feeds a QF, which feeds an SF, then Final.
#
# Layout (left side, top → bottom):
#   R32 L1 + L2  → R16 L_R16_1
#   R32 L3 + L4  → R16 L_R16_2
#   R32 L5 + L6  → R16 L_R16_3
#   R32 L7 + L8  → R16 L_R16_4
#   R16 L_R16_1 + L_R16_2 → QF L_QF_1
#   R16 L_R16_3 + L_R16_4 → QF L_QF_2
#   QF  L_QF_1  + L_QF_2  → SF L_SF
#
# Right side mirrors:
#   R32 R1 + R2  → R16 R_R16_1
#   R32 R3 + R4  → R16 R_R16_2
#   R32 R5 + R6  → R16 R_R16_3
#   R32 R7 + R8  → R16 R_R16_4
#   R16 R_R16_1 + R_R16_2 → QF R_QF_1
#   R16 R_R16_3 + R_R16_4 → QF R_QF_2
#   QF  R_QF_1  + R_QF_2  → SF R_SF
#
# Both SFs feed the Final → Champion

R32_LEFT_SLOTS: list[str] = [f"L{i}" for i in range(1, 9)]   # L1..L8
R32_RIGHT_SLOTS: list[str] = [f"R{i}" for i in range(1, 9)]  # R1..R8
R32_ALL_SLOTS: list[str] = R32_LEFT_SLOTS + R32_RIGHT_SLOTS

R16_LEFT_SLOTS: list[str] = ["L_R16_1", "L_R16_2", "L_R16_3", "L_R16_4"]
R16_RIGHT_SLOTS: list[str] = ["R_R16_1", "R_R16_2", "R_R16_3", "R_R16_4"]
R16_ALL_SLOTS: list[str] = R16_LEFT_SLOTS + R16_RIGHT_SLOTS

QF_LEFT_SLOTS: list[str] = ["L_QF_1", "L_QF_2"]
QF_RIGHT_SLOTS: list[str] = ["R_QF_1", "R_QF_2"]
QF_ALL_SLOTS: list[str] = QF_LEFT_SLOTS + QF_RIGHT_SLOTS

SF_SLOTS: list[str] = ["L_SF", "R_SF"]

# Mapping: which two R32 slots feed each R16 slot
R32_TO_R16: dict[str, str] = {
    "L1": "L_R16_1", "L2": "L_R16_1",
    "L3": "L_R16_2", "L4": "L_R16_2",
    "L5": "L_R16_3", "L6": "L_R16_3",
    "L7": "L_R16_4", "L8": "L_R16_4",
    "R1": "R_R16_1", "R2": "R_R16_1",
    "R3": "R_R16_2", "R4": "R_R16_2",
    "R5": "R_R16_3", "R6": "R_R16_3",
    "R7": "R_R16_4", "R8": "R_R16_4",
}

R16_TO_QF: dict[str, str] = {
    "L_R16_1": "L_QF_1", "L_R16_2": "L_QF_1",
    "L_R16_3": "L_QF_2", "L_R16_4": "L_QF_2",
    "R_R16_1": "R_QF_1", "R_R16_2": "R_QF_1",
    "R_R16_3": "R_QF_2", "R_R16_4": "R_QF_2",
}

QF_TO_SF: dict[str, str] = {
    "L_QF_1": "L_SF", "L_QF_2": "L_SF",
    "R_QF_1": "R_SF", "R_QF_2": "R_SF",
}

# ---------------------------------------------------------------------------
# Part 2 Excel cell map (for the parser)
# ---------------------------------------------------------------------------
#
# Each R32 slot maps to:
#   team_cells: the two cells containing the competing teams
#   winner_cell: the cell for the predicted winner
#
# Left side (col A = teams, col B = winner)
R32_LEFT_CELL_MAP: dict[str, dict] = {
    "L1": {"team_cells": [("A", 8),  ("A", 9)],  "winner_cell": ("B", 8)},
    "L2": {"team_cells": [("A", 11), ("A", 12)], "winner_cell": ("B", 11)},
    "L3": {"team_cells": [("A", 14), ("A", 15)], "winner_cell": ("B", 14)},
    "L4": {"team_cells": [("A", 17), ("A", 18)], "winner_cell": ("B", 17)},
    "L5": {"team_cells": [("A", 20), ("A", 21)], "winner_cell": ("B", 20)},
    "L6": {"team_cells": [("A", 23), ("A", 24)], "winner_cell": ("B", 23)},
    "L7": {"team_cells": [("A", 26), ("A", 27)], "winner_cell": ("B", 26)},
    "L8": {"team_cells": [("A", 29), ("A", 30)], "winner_cell": ("B", 29)},
}

# Right side (col K = teams, col J = winner)
R32_RIGHT_CELL_MAP: dict[str, dict] = {
    "R1": {"team_cells": [("K", 8),  ("K", 9)],  "winner_cell": ("J", 8)},
    "R2": {"team_cells": [("K", 11), ("K", 12)], "winner_cell": ("J", 11)},
    "R3": {"team_cells": [("K", 14), ("K", 15)], "winner_cell": ("J", 14)},
    "R4": {"team_cells": [("K", 17), ("K", 18)], "winner_cell": ("J", 17)},
    "R5": {"team_cells": [("K", 20), ("K", 21)], "winner_cell": ("J", 20)},
    "R6": {"team_cells": [("K", 23), ("K", 24)], "winner_cell": ("J", 23)},
    "R7": {"team_cells": [("K", 26), ("K", 27)], "winner_cell": ("J", 26)},
    "R8": {"team_cells": [("K", 29), ("K", 30)], "winner_cell": ("J", 29)},
}

R32_CELL_MAP: dict[str, dict] = {**R32_LEFT_CELL_MAP, **R32_RIGHT_CELL_MAP}

# R16 winner cells
R16_CELL_MAP: dict[str, tuple[str, int]] = {
    "L_R16_1": ("C", 10),
    "L_R16_2": ("C", 16),
    "L_R16_3": ("C", 22),
    "L_R16_4": ("C", 28),
    "R_R16_1": ("I", 10),
    "R_R16_2": ("I", 16),
    "R_R16_3": ("I", 22),
    "R_R16_4": ("I", 28),
}

# QF winner cells
QF_CELL_MAP: dict[str, tuple[str, int]] = {
    "L_QF_1": ("D", 13),
    "L_QF_2": ("D", 25),
    "R_QF_1": ("H", 13),
    "R_QF_2": ("H", 25),
}

# SF winner cells
SF_CELL_MAP: dict[str, tuple[str, int]] = {
    "L_SF": ("E", 19),
    "R_SF": ("G", 19),
}

CHAMPION_CELL: tuple[str, int] = ("F", 19)
TIEBREAKER_CELL: tuple[str, int] = ("E", 41)

# ---------------------------------------------------------------------------
# Part 1 Excel cell map
# ---------------------------------------------------------------------------

PART1_NAME_CELL: str = "B4"
PART1_SUBMITTED_ON_CELL: str = "B47"
PART1_FINALIST_1_CELL: str = "B40"
PART1_FINALIST_2_CELL: str = "B41"
PART1_WINNER_CELL: str = "B42"
PART1_GOLDEN_BOOT_CELL: str = "B43"

# Group winner/runner-up cells: rows 23–34, cols C (winner) and D (runner-up)
PART1_GROUP_CELL_MAP: dict[str, dict[str, str]] = {
    "A": {"winner": "C23", "runner_up": "D23"},
    "B": {"winner": "C24", "runner_up": "D24"},
    "C": {"winner": "C25", "runner_up": "D25"},
    "D": {"winner": "C26", "runner_up": "D26"},
    "E": {"winner": "C27", "runner_up": "D27"},
    "F": {"winner": "C28", "runner_up": "D28"},
    "G": {"winner": "C29", "runner_up": "D29"},
    "H": {"winner": "C30", "runner_up": "D30"},
    "I": {"winner": "C31", "runner_up": "D31"},
    "J": {"winner": "C32", "runner_up": "D32"},
    "K": {"winner": "C33", "runner_up": "D33"},
    "L": {"winner": "C34", "runner_up": "D34"},
}

# ---------------------------------------------------------------------------
# Sheet names (used by classifier)
# ---------------------------------------------------------------------------

SHEET_PART1: str = "My Predictions"
SHEET_PART2: str = "Knockout Bracket"

# ---------------------------------------------------------------------------
# Tournament dates (for cache TTL logic)
# ---------------------------------------------------------------------------

TOURNAMENT_START: str = "2026-06-11"
TOURNAMENT_END: str = "2026-07-19"

# ---------------------------------------------------------------------------
# Fuzzy match threshold for Golden Boot resolution
# ---------------------------------------------------------------------------

GOLDEN_BOOT_FUZZY_THRESHOLD: float = 0.7
