# Executive summary: El Clásico in the Messi era (2005–2021)

**Question.** How did Barcelona and Real Madrid play against each other over 16 years, is the Clásico different
from their other matches, and how sure can we be?

**Data.** StatsBomb open event data: 29 league Clásicos, 524 Barcelona league matches (those Messi played), the
complete 2015/16 season and 7 Champions League finals. Every number comes with a 90% bootstrap interval, resampling
whole matches.

## Five findings

1. **The two styles converged.** Barcelona's build-up peaked under Guardiola (11.1 completed passes before an
   open-play shot, 2009-13) and fell to 7.0 (2017-21). Real Madrid went from direct (4.1) to patient (7.2).
   Both changes are clear: −4.1 [−7.8, −0.7] and +3.1 [+1.6, +4.4].
2. **Barcelona stopped pressing in the Clásico, and not because it was winning.** PPDA rose from 9.5 to 17.9
   (higher = less pressure); with the score level it rose from 8.4 to 19.9. Barcelona led for only 20% of the
   minutes in 2017-21.
3. **The Clásico was special, and the difference flipped.** Under Guardiola Barcelona pressed *harder* against Real
   Madrid than against any other club (PPDA −1.6 [−2.8, −0.2]); by 2017-21 it pressed clearly *less* (+4.9
   [+2.8, +7.5]). Against the rest of the league the press loosened only slowly.
4. **A new coach can change a team within a season, or only its results.** Guardiola's first season: press success
   +5.8 points, possession +4.8 points, non-penalty xG +0.66 per match, all clear. Zidane's arrival in 2015/16:
   points per match 2.06 → 2.65, but the only clear change in how the team played was slower attacks.
5. **Finals are played differently.** In the 2009 final Barcelona had 51% of the ball, less than in any of its 31
   league matches that season, and reached its shots after 3.3 passes, fewer than in any of them.

## What it means

- **For opposition analysis:** central-midfield losses are the costly ones (12.5% end in an opponent shot for
  Barcelona against 1–4% in the attacking third); protecting zone 5 matters more than high losses.
- **For evaluating a coach:** look at how the team plays, not only at points; a jump in points with no clear
  change in play (Zidane 2015/16) is weaker evidence of a lasting change than Guardiola's.
- **For storytelling:** "Barcelona stopped pressing" holds; "because it was protecting leads" does not.

## How far to trust it

- 6–8 matches per period: intervals are wide and probably still somewhat too narrow.
- 108 period changes were tested; ~11 would look clear by chance alone, so trust the large, consistent findings
  above more than any single borderline one.
- Not controlled: home/away, line-ups and injuries, red cards. Event data only, no tracking data.

Full method, definitions and limitations: [README](../README.md) · Interactive dashboard:
[arslannizzetali.github.io/el-clasico-analytics](https://arslannizzetali.github.io/el-clasico-analytics/)
