# Determine whether an .xlsx file is a Part 1 or Part 2 submission.

from __future__ import annotations

import logging
from pathlib import Path

import openpyxl

from sweepstake.constants import SHEET_PART1, SHEET_PART2

log = logging.getLogger(__name__)


class ClassifierError(ValueError):
    pass


def classify(path: str | Path) -> str:
    # Returns "part1" or "part2". Raises ClassifierError if neither sheet name matches.
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    sheet_names = wb.sheetnames
    wb.close()

    if SHEET_PART1 in sheet_names:
        log.debug("Classified %s as Part 1", path)
        return "part1"
    if SHEET_PART2 in sheet_names:
        log.debug("Classified %s as Part 2", path)
        return "part2"

    raise ClassifierError(
        f"Cannot classify '{Path(path).name}': expected a sheet named "
        f"'{SHEET_PART1}' (Part 1) or '{SHEET_PART2}' (Part 2), "
        f"but found: {sheet_names}"
    )
