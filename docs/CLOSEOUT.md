# Closeout checklist: what the owner must do to finish and archive the project

Context: the sealed run (`run_id` 20261006T141900Z) is done, but its output files exist only on the owner's Windows machine, so Phase 6 is incomplete (`docs/results.md`). Claude's cloud session cannot reach NSE, niftyindices or RBI, so it cannot regenerate them. Do the steps in order. Commands are for PowerShell in the repository root.

Correction to earlier notes: there is no `python -m osr.report` entry point. The report statistics are produced by `report.run`, which `python -m osr.walkforward sealed` calls. The step below therefore starts by looking for output that already exists. Also, `.gitignore` contains `*.md`, so new Markdown files are ignored: always add them with `git add -f`.

## Step 1. Check what the sealed run already produced (5 minutes, no rerun)

```powershell
Get-ChildItem "data\results\sealed\20261006T141900Z"
```

Expected: `gates.parquet`, `trackS_lag*_*.parquet`, `trackT_lag*_*.parquet`, and (if the report step finished) `confirmatory_trackS.csv`, `confirmatory_trackT.csv`, `selection_trackS.csv`, `selection_trackT.csv`.

- If the four CSV files exist: go to Step 2.
- If they do not exist, `report.run` crashed or was interrupted after the ledger rows were written. Do not rerun the sealed run. Tell Claude (Step 4); the report can be recomputed from the saved parquet files and `gates.parquet` without touching the sealed stopping rule, because the returns themselves are not recomputed.

## Step 2. Answer the integrity questions (write the answers down, 10 minutes)

1. What was uncommitted in the working tree when the sealed run started? (`git status` output from that day if you have it; otherwise your best recollection.) 77 of 78 ledger rows say `dirty: true`.
2. Commit `7728e18` is not in this repository's history. Was it a local commit that you later amended or rebased away? Check `git reflog` on the machine: `git reflog | Select-String 7728e18`.
3. Was tag `prereg-v1` ever created? `git tag` and `git ls-remote --tags origin`. If not, say so; do not create it retroactively without dating it as retroactive.
4. Does `Get-FileHash data\manifest.json` (raw bytes) equal `33cb4e42...` (the ledger value)? If so, the manifest-hash difference from `prereg.lock` is only CRLF normalisation.

Paste the answers into a message to Claude or into a new file `docs/integrity_answers.md`.

## Step 3. Publish the sealed output (10 minutes)

Check first that no file contains secrets (the results folder should hold only parquet and CSV files; `.env` is never in it).

```powershell
git checkout claude/task-1k4oe5
git pull origin claude/task-1k4oe5
git add -f "data/results/sealed/20261006T141900Z"
git add -f docs/integrity_answers.md   # only if you created it
git commit -m "data: sealed run 20261006T141900Z output"
git push origin claude/task-1k4oe5
```

If the folder is larger than about 50 MB, zip it and upload the zip to the session instead.

## Step 4. Hand back to Claude for the write-up (Claude does this)

Send one message: "sealed output pushed, finish Phase 6". Claude will then:
1. Read the four CSV files and add the section 10 tests (Holm-adjusted p-values, intervals, minimum detectable effects) and section 11 DSR/PBO to `docs/results.md`.
2. Recompute the section 12 items that need only the saved returns and gates: rolling-refit stability, known-event table, episode attribution, cost curves, drawdown figures.
3. Rewrite the conclusions to match the power statement, reporting null results as null.
4. Replace the integrity notes with your Step 2 answers.

Items that need the raw F&O data (the orthogonalised-HMM ablation, which re-fits the HMM, and the synthetic validation, `python -m osr.validation synthetic`, about 40 minutes) must be run on your machine. If you want them, run:

```powershell
.venv\Scripts\python -m osr.validation synthetic
.venv\Scripts\python -m osr.validation stability
```

and commit the outputs the same way as Step 3. If you skip them, the write-up states they were not run.

## Step 5. Close the repository

After Claude's final push:

1. Read `docs/results.md` once from top to bottom and check every number against the CSV files and `ledger.jsonl`.
2. Update `PLAN.md` section 7 to "Phase 6 complete" with the date.
3. Merge: open a pull request from `claude/task-1k4oe5` into `main` on GitHub, merge it, and delete the branch.
4. Tag the final state: `git tag study-final-v1` then `git push origin study-final-v1`. Do not reuse the name `prereg-v1`.
5. Move `.venv/` and `data/` out of OneDrive or exclude them from sync (CLAUDE.md gotcha), and keep one offline copy of `data/` (raw bhavcopy rows, processed parquet, manifest, results). The sealed data cannot be re-downloaded identically if NSE changes its archive.
6. Rotate or revoke the Kite API secret and access token if you will not run the live recorder again, and confirm `KITE_LIVE_TRADING` is false.

## Step 6. If you decide not to finish Phase 6

A defensible stopping point is the current state: ledger-only results with explicit disclosure. In that case:
1. Do Step 2 (the integrity answers), because the write-up cannot be cited without them.
2. Do Step 3 so the evidence is preserved.
3. Edit the first paragraph of `docs/results.md` to say "final, limited to ledger metrics; confirmatory tests not completed", and do Step 5.
