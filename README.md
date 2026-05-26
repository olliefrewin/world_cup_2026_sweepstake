# 2026 World Cup Sweepstake

A standalone Windows desktop application for running a workplace sweepstake for the 2026 FIFA World Cup (USA/Canada/Mexico, 11 June – 19 July 2026).

## Features

- Upload participant prediction spreadsheets (Part 1: group stage, Part 2: knockout bracket)
- Live scoring against API-Football results (api-sports.io)
- Manual result override for any match
- Live leaderboard with tiebreaker support
- Golden Boot fuzzy-match resolution workflow

## Design decisions

- **Leaderboard visibility**: participants who haven't submitted both parts are shown at the bottom with "—" in the missing column rather than hidden entirely, so everyone can see who's outstanding.
- **No API key configured**: all tabs remain functional. API refresh is disabled; manual override is sufficient to run a complete sweepstake.
- **Cache TTL**: 30 minutes on any day where a World Cup match is scheduled; 24 hours otherwise.
- **Score breakdown**: shown only on click (modal) to keep the leaderboard table tight.
- **Accent colour**: `#C0142C` (deep FIFA red).

## Quick start

1. Install Python 3.11+
2. `pip install -r requirements.txt`
3. `python -m sweepstake`

## Build

```
build.bat
```

Produces `dist\WorldCupSweepstake.exe` — a single self-contained executable.

## Testing

```
pytest
```
