# Sims 4 Mod Manager — Design

## Purpose

A desktop app that removes the tedious parts of installing Sims 4 mods/CC for a non-technical user, and gives them one place to search for mods across the sites they actually use instead of hunting manually. It does not attempt to fully automate mod discovery/download end-to-end — most mod sites block automated scraping and downloading via ToS and anti-bot measures, so the app leans on the browser for actual downloading and automates everything after that point.

## Background

The Sims 4 modding process (per the source guide, moddingcommunity.com/blog/how-to-install-mods-in-the-sims-4) is:

1. Download a mod as `.zip`/`.rar` from a trusted site (ModTheSims, TSR, CurseForge, Patreon, etc.).
2. Extract it.
3. Place the resulting `.package`/`.ts4script` files (or a folder containing them) into `Documents\Electronic Arts\The Sims 4\Mods`, no deeper than one folder level, or the game won't load them.
4. One-time: enable "Enable Custom Content and Mods" and "Script Mods Allowed" in Options > Game Options > Other, then restart the game.
5. Ongoing: keep the Mods folder organized, avoid duplicates, back up `Mods`/`Saves`/`Tray` before big changes, and remove mods that break after game patches.

The fiddly, error-prone parts are: enforcing the one-folder-deep rule, organizing/deduping a growing pile of CC, and not forgetting the in-game settings toggle. None of that requires talking to the mod sites at all — it's local file management. The other pain point is discovery: finding a specific mod across ModTheSims/CurseForge without knowing whether either site has it.

## Goals

- One desktop app the user can double-click to open — no terminal, no scripts.
- Search across ModTheSims and CurseForge from one search box.
- Turn "I downloaded a zip" into "it's correctly installed and categorized" with minimal clicks.
- Handle the one-time game-settings toggle automatically where possible.
- Never silently overwrite, lose, or misplace a file.

## Non-goals (v1)

- No automated scraping or automated downloading from ModTheSims (blocked by ToS/anti-bot; not attempted).
- No CurseForge API integration (explicitly descoped — avoids the API key application/approval process).
- No support for The Sims Resource or Lumpinou Mods (may be added later; not built in v1).
- No reconciliation of a pre-existing, already-populated Mods folder — this is designed for a fresh modding setup.
- No mod-update/compatibility checking after game patches.
- No background service — the app only watches/acts while its window is open.

## Architecture

Single Python + PySide6 (Qt) desktop application, packaged as one standalone `.exe` via PyInstaller. One process, no background service, no browser extension. Local SQLite (or JSON — decide during implementation based on what's simplest) tracks installed-file hashes and an activity log.

Two tabs share one install engine underneath:

- **Find** — search/discovery.
- **Inbox** — files awaiting or ready for install, plus the install pipeline.

## Find tab

- **Search box** with a site toggle (ModTheSims / CurseForge / both). Since neither site has an automation-friendly path in v1, submitting a search opens pre-filled search-results pages for the selected site(s) in the user's default browser (deep-linked to each site's own search URL format). The user browses and downloads there as normal.
- **Paste-a-link box**: a single field for any URL, with three-way routing on submit:
  1. A direct file URL (ends in `.zip`/`.rar`/`.package`/`.ts4script`) → downloaded directly by the app, then handed to the install pipeline.
  2. Anything else (a ModTheSims or CurseForge mod page, etc.) → opened in the user's default browser, with an in-app note: "Opened in your browser — download it there and I'll catch it automatically."

## Inbox tab & install pipeline

**Downloads watcher**: while the app is open, a background thread watches the user's Downloads folder for new files matching mod patterns (`.zip`, `.rar`, `.package`, `.ts4script`). Matches appear as cards in the Inbox: filename, detected type, "ready to install." Nothing installs until the user acts on a card (or a direct-file-link install completes) — the watcher only surfaces candidates, it never writes into `Mods` on its own.

**Install pipeline** (per item):

1. **Extract** `.zip`/`.rar` into a temp staging area (`py7zr`/`rarfile`, or a bundled 7-Zip binary — pick whichever is more reliable during implementation).
2. **Flatten**: locate all `.package`/`.ts4script` files regardless of source nesting, and lay them out at most one folder deep under `Mods/`, per the game's hard requirement.
3. **Categorize** into `Mods/CAS`, `Mods/Build-Buy`, `Mods/Gameplay`, `Mods/Script`, inferred from file type (`.ts4script` → Script) and filename/folder-name heuristics for the rest. Anything the heuristics can't confidently place goes to `Mods/Uncategorized` rather than a wrong guess.
4. **Dedupe**: SHA-256 hash each file; if it matches a file already recorded as installed, skip writing it and flag it in the activity log as a duplicate rather than silently overwriting or silently dropping it.
5. **Record**: log the install (source, files, category, hash, timestamp) to the local store, so future dedup checks and the activity log both work.

**Backups**: before the first install pipeline run of each app session, zip-copy `Mods`, `Saves`, and `Tray` (under `Documents\Electronic Arts\The Sims 4`) to a timestamped backup folder.

**Settings toggle**: on first run, attempt to locate the game's `Options.ini` and set the custom-content/script-mods flags directly, so the user never has to open the in-game menu. The exact key names get confirmed against a real install during implementation. If the file can't be found or the edit can't be made reliably, fall back to a one-time on-screen instruction instead of failing silently.

## Error handling

- **Extraction failure** (corrupt/password-protected archive, unknown format): item stays in the Inbox flagged "couldn't open — check the file." Never silently dropped.
- **Ambiguous categorization**: goes to `Mods/Uncategorized`; nothing is lost, the user can move it manually.
- **Duplicate detected**: skipped and logged as "already installed," never silently overwritten.
- **`Options.ini` not found or not editable**: falls back to the one-time on-screen reminder; the app doesn't crash or fail silently.
- **Downloads watcher false positive** (a non-mod zip matched the pattern): worst case it sits unactioned in the Inbox — nothing writes to `Mods` until a card is acted on, and the session backup is a second safety net regardless.
- **Activity log**: every install action (what, when, from where, into which category) is recorded in-app so mistakes are traceable and manually reversible.

## Testing approach

Personal single-user desktop tool — testing is pragmatic, not exhaustive:

- Unit tests for the deterministic logic: flatten/path rules, categorization heuristics, dedup hashing, `Options.ini` parsing/editing.
- Manual end-to-end pass before handoff: a real zip from ModTheSims, a real zip from CurseForge, a `.ts4script`-only mod, a mod with deeply nested folders, and a duplicate-install case — verified against a real (or throwaway) `Mods` folder.
- No automated GUI testing — not worth the overhead here; correctness lives in the pipeline logic under the GUI, which the unit tests cover.

## Open questions to resolve during implementation

- Exact `Options.ini` key names/format for the two settings flags (verify against a real Sims 4 install).
- Whether SQLite or a flat JSON file is simpler for the local install-tracking store — pick during implementation, no functional difference at this scale.
- Exact archive-handling library choice (`py7zr`/`rarfile` vs. bundling 7-Zip) — pick based on what packages most reliably into a single `.exe`.
