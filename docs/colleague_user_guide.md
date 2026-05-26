# World Cup 2026 Sweepstake - User Guide

This guide is written for anyone running the sweepstake, with no technical knowledge assumed.

---

## 1. First-time setup: getting an API key

The app can fetch live World Cup results automatically. To use this feature you need a free API key.

1. Go to **https://api-sports.io** in your web browser.
2. Click **Register** and create a free account.
3. Once logged in, go to your dashboard and copy your **API key** (a long string of letters and numbers).
4. Open the sweepstake app and click the **Settings** tab.
5. Paste your key into the **API-Football key** box and click **Save**.
6. Click **Test Connection** to confirm it works. You should see a message saying how many requests remain today.

You do not need an API key to use the app. You can enter results manually instead (see section 4).

---

## 2. Uploading a participant's entry

Each participant fills in their own Excel spreadsheet and sends it to you.

### Uploading Part 1 (group stage picks)

1. Click the **Submissions** tab.
2. Click **Browse for file** and select the participant's Part 1 Excel file (`WorldCupSweep_Part1_Entry.xlsx`), or drag and drop the file onto the upload area.
3. The app will read the file and show you a preview of what it found.
4. Check the details look correct, then click **Confirm and Save**.
5. The participant's entry now appears in the submissions list below.

### Uploading Part 2 (knockout bracket)

Same steps as above, but select the Part 2 file (`WorldCupSweep_Part2_Bracket.xlsx`).

### If you see an error

- **"Participant X has already submitted"** - that person has already been uploaded. If you need to replace their entry, click **Remove P1** or **Remove P2** next to their name in the submissions list, then upload the new file.
- **"Validation errors"** - the file contains something invalid (for example, a team name from the wrong group). Fix the spreadsheet and re-upload.

---

## 3. Refreshing results during the tournament

Once the API key is set up, you can pull in the latest results with one click.

1. Click the **Actuals** tab.
2. Click the **Refresh Now** button.
3. The leaderboard will update automatically within a few seconds.

The app will show today's API call count. The free tier allows 100 calls per day, so refresh as often as you like without worrying.

---

## 4. Overriding a result manually

If the API returns an incorrect result, or you want to enter results without an API key, use manual overrides.

1. Click the **Actuals** tab.
2. In the **Manual Overrides** section, type a key and value in the boxes and click **Add**.

Key examples:
- `champion` - value: the winning country, e.g. `England`
- `group_winner.A` - value: the Group A winner, e.g. `Mexico`
- `group_runner_up.B` - value: the Group B runner-up
- `r32_winner.L1` - value: the winner of Round of 32 slot L1
- `finalist_1` and `finalist_2` - the two finalists
- `final_total_goals` - the total number of goals in the final (used for the tiebreaker)

The override wins over any API value. To remove an override and revert to the API value, click **Remove** on that row.

---

## 5. Resolving a Golden Boot pending match

Once you know the actual Golden Boot winner, you need to tell the app.

1. Click the **Actuals** tab.
2. In the **Golden Boot** section, type the winner's full name (e.g. `Kylian Mbappe`) and click **Set and Seed**.
3. The app will automatically compare this name against everyone's picks and show you any close matches as **Pending**.
4. For each pending match, read the participant's original text and decide whether it refers to the same player.
   - Click **Match** if it is the same player - they score 15 points.
   - Click **No match** if it is a different player - they score nothing.

Picks that are clearly different (very low similarity) are automatically rejected and do not appear for review.

---

## 6. Reading the leaderboard

The **Leaderboard** tab shows everyone's current score.

- **Part 1** - points from group stage predictions and up-front bonus picks.
- **Part 2** - points from the knockout bracket.
- **Total** - the combined score.
- **TB Pred.** - each participant's tiebreaker guess (total goals in the final). Used only if two people are tied on total points.
- **--** in a column means that participant has not yet submitted that part.

Click **Breakdown** on any row to see a detailed breakdown of how their points were calculated.

The leaderboard refreshes automatically every 5 seconds while the tab is open.

---

## 7. Exporting final results

Once the tournament is over, you can export a full summary to share with everyone.

1. Click the **Settings** tab.
2. Click **Export Results as CSV**.
3. Choose where to save the file.
4. Open it in Excel to view the final standings with full score breakdowns for every participant.
