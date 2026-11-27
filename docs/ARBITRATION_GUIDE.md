# SickShift Arbitration Guide (Owner Quick Reference)

When SickGear changes code that SickShift intentionally customized, you will receive a GitHub email for an issue titled:

> **`[ACTION REQUIRED] SickShift synchronization — decision needed`**

You do **not** need to open Git, inspect code, or run local commands.

## How to resolve in under 1 minute

1. Read the short plain-English summary (**WHAT HAPPENED?**, **WHY DOES IT MATTER?**, **RECOMMENDED DECISION**).
2. Reply directly to the GitHub issue — **or reply directly to the GitHub notification email** — with one line:

| Command | What it does |
|---|---|
| `/approve` | Applies the **Recommended Decision** shown in the issue, runs all tests & Docker checks, pushes to `main`, and closes the issue automatically. |
| `/choose A` | Keeps the **SickShift** behavior for the conflicting section(s). |
| `/choose B` | Adopts the new **SickGear** behavior (adapted to SickShift's namespace). |
| `/choose C` | Combines **both** approaches (only shown when technically feasible). |
| `/retry` | Re-runs automatic synchronization without changing your previous choice. |
| `/explain` | Posts an additional plain-English breakdown without modifying any files. |

## Safety Guarantees

- **Owner-only:** Commands from anyone other than `@pomercier` are rejected automatically.
- **Stale-approval protection:** If SickGear pushes new commits before you reply, your previous approval is not blindly applied; the issue is refreshed to a new revision first.
- **No blind merges:** Every approved decision still runs full privacy checks, compilation, import checks, and unit tests before pushing to `main`.

## One-time GitHub Email Notification Check

To guarantee GitHub emails arrive whenever an arbitration or watchdog alert is created:

1. Visit **https://github.com/settings/notifications**
2. Under **Subscriptions**:
   - **Participating, @mentions and custom:** enable **Email**.
   - **Watching:** enable **Email**.
3. Under **System → Actions:** enable **Email** and check **Send notifications for failed workflows only**.
4. On **https://github.com/pomercier/SickShift**, click **Watch** → select **Participating and @mentions** (or **All Activity**).
5. Verify your primary notification email address is confirmed at **https://github.com/settings/emails**.

> **Email replies:** GitHub natively delivers email replies to issue notification emails as issue comments. Because `scripts/arbitration.py` ignores quoted lines (`>`) and email signatures (`--`), replying `/approve` straight from your inbox triggers `arbitration-handler.yml` safely.
