# World Cup 2026 Sweepstake — Host Guide

This guide is for the person running the sweepstake. No technical knowledge is needed.

---

## Contents

1. [Getting started](#1-getting-started)
2. [Collecting and uploading entries](#2-collecting-and-uploading-entries)
3. [Keeping results up to date](#3-keeping-results-up-to-date)
4. [Entering results manually](#4-entering-results-manually)
5. [The Golden Boot](#5-the-golden-boot)
6. [Reading the leaderboard](#6-reading-the-leaderboard)
7. [Exporting final results](#7-exporting-final-results)
8. [Scoring reference](#8-scoring-reference)

---

## 1. Getting started

Open the app by double-clicking `WorldCupSweepstake.exe`. No installation or internet account is needed.

The app has four tabs across the top:
- **Leaderboard** — live standings, updates automatically
- **Submissions** — upload and manage participant entries
- **Actuals** — refresh results and enter manual overrides
- **Settings** — export results and view the database location

You do not need to configure anything before the tournament starts. Once entries are uploaded, the leaderboard will show predicted scores. Real points will accumulate as you refresh results during the tournament.

---

## 2. Collecting and uploading entries

### What participants need to fill in

Send each participant two Excel files:
- **Part 1** (`WorldCupSweep_Part1_Form.xlsx`) — group stage picks, finalists, winner, and Golden Boot guess. Due before the tournament starts.
- **Part 2** (`WorldCupSweep_Part2_Form.xlsx`) — knockout bracket predictions. Due before the Round of 32 begins.

Ask them to save the file with their name somewhere visible (the app reads the name from inside the spreadsheet).

### Uploading an entry

1. Click the **Submissions** tab.
2. Click **Browse for file** and select the participant's Excel file, or drag and drop it onto the upload area.
3. The app shows a preview of what it found — check the name and picks look right.
4. Click **Confirm and Save**. The entry appears in the submissions list below.

Repeat for each participant and each part.

### Common upload errors

| Error | What to do |
|---|---|
| "Participant X has already submitted" | Click **Remove P1** or **Remove P2** next to their name, then re-upload the corrected file. |
| "Validation errors" | The spreadsheet contains something invalid (e.g. a team name spelt incorrectly). Ask the participant to fix and resubmit. |
| "Could not classify file" | The wrong file was uploaded, or the sheet name has been changed. Make sure the original template was used. |

Participants who have only submitted one part appear at the bottom of the leaderboard with `--` in the missing column — they are not hidden, so everyone can see who is still outstanding.

---

## 3. Keeping results up to date

The app fetches live results from a free public data source — no account or API key is required.

### Refreshing results

1. Click the **Actuals** tab.
2. Click **Refresh Now**.
3. The leaderboard updates automatically within a few seconds.

Results are cached for 30 minutes, so clicking Refresh repeatedly during a match is fine — it will only actually fetch new data once the cache expires.

### How often to refresh

- **During a matchday**: click Refresh after each match finishes, or whenever you want an up-to-date leaderboard.
- **Between matchdays**: once a day is plenty.

### If the data looks wrong or is out of date

The data source is community-maintained and occasionally lags a few hours behind real results. If a result hasn't appeared yet, enter it manually (see Section 4).

---

## 4. Entering results manually

You can add or correct any result yourself. Manual overrides always take priority over fetched data.

1. Click the **Actuals** tab.
2. Scroll down to the **Manual Overrides** section.
3. Type a key and value in the boxes and click **Add**.

### Key reference

| What you want to set | Key | Example value |
|---|---|---|
| Group A winner | `group_winner.A` | `Mexico` |
| Group A runner-up | `group_runner_up.A` | `South Korea` |
| Round of 32 slot L1 winner | `r32_winner.L1` | `England` |
| Round of 16 slot L_R16_1 winner | `r16_winner.L_R16_1` | `England` |
| Quarter-final slot L_QF_1 winner | `qf_winner.L_QF_1` | `England` |
| Semi-final slot L_SF winner | `sf_winner.L_SF` | `England` |
| Tournament champion | `champion` | `England` |
| Final participant 1 | `finalist_1` | `England` |
| Final participant 2 | `finalist_2` | `France` |
| Total goals in the final | `final_total_goals` | `3` |

Groups run A–L. Knockout slots follow the bracket printed on the Part 2 form.

To **remove** an override and revert to the fetched value, click **Remove** on that row.

---

## 5. The Golden Boot

The Golden Boot is awarded to the participant who correctly predicted the tournament's top scorer.

### Setting the winner

Once the Golden Boot is decided:

1. Click the **Actuals** tab.
2. In the **Golden Boot** section, type the player's full name (e.g. `Kylian Mbappe`) and click **Set & Seed**.
3. The app compares this against everyone's picks and flags any close matches as **Pending**.

### Reviewing pending matches

The app automatically approves exact matches and rejects clearly wrong ones. For any remaining cases marked as pending:

- Read the participant's original text.
- Click **Match** if it refers to the same player — they receive 15 points.
- Click **No match** if it is a different player — they receive 0 points.

You only need to review entries the app is genuinely unsure about (typically misspellings or shortened names like "Mbappe" vs "Kylian Mbappe").

---

## 6. Reading the leaderboard

The **Leaderboard** tab shows everyone's current score and refreshes automatically every 5 seconds.

| Column | Meaning |
|---|---|
| Rank | Current position |
| Name | Participant name (from their spreadsheet) |
| Part 1 | Points from group stage predictions and bonus picks |
| Part 2 | Points from knockout bracket |
| Total | Combined score |
| TB Pred. | Their predicted total goals in the final — used as tiebreaker only if two people are level on points |
| `--` | That part has not been submitted yet |

Click **Breakdown** on any row to see exactly how their points were calculated.

### Tiebreaker

If two participants finish level on total points, the one whose final goal prediction was closest to the actual score is ranked higher. If they are still level, they share the position.

---

## 7. Exporting final results

At the end of the tournament, export a full spreadsheet to share with everyone.

1. Click the **Settings** tab.
2. Click **Export Results as CSV**.
3. Choose where to save the file and open it in Excel.

The CSV includes final rank, all scores broken down by category, and tiebreaker predictions for every participant.

---

## 8. Scoring reference

### Part 1 — Group stage and bonus picks

| Prediction | Points |
|---|---|
| Correct group winner | 10 pts each (12 groups) |
| Correct group runner-up | 5 pts each (12 groups) |
| Correct finalist (either finalist) | 15 pts each (2 picks) |
| Correct tournament winner | 25 pts |
| Correct Golden Boot winner | 15 pts |
| **Part 1 maximum** | **250 pts** |

### Part 2 — Knockout bracket

| Round | Points per correct winner |
|---|---|
| Round of 32 (16 matches) | 3 pts |
| Round of 16 (8 matches) | 5 pts |
| Quarter-finals (4 matches) | 8 pts |
| Semi-finals (2 matches) | 12 pts |
| Champion | 20 pts |
| **Part 2 maximum** | **164 pts** |

**Overall maximum: 414 points.**
