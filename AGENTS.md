# Group Loot Forever

WoW Forever addon: counts on the game's roll frame for the picks of each group loot roll (pending, Need,
Greed, Disenchant, Transmog, Pass) and lists the names on hover. The README says what it
does for players; this file is the workflow.

Public repo github.com/RafaelHGOliveira/GroupLootForever (private until 2026-11-22). Commits use
rafaelh9six@hotmail.com (set in the repo config), never the Gmail. Commit and push after
each change, without asking. CurseForge project 1824599, slug `grouplootforever`
(https://www.curseforge.com/wow/addons/grouplootforever); the
project description is pasted by hand from `docs/curseforge.md` (Markdown editor); it
links the GitHub repo, and the README links the CurseForge page.

## Release

`pwsh -NoProfile -File release.ps1 <version> <changelog.md>`, beta unless `-ReleaseType release`.
It runs the test, bumps the `.toc`, commits "Release X", tags, pushes, uploads the
`git archive` zip to CurseForge and copies the files into the game. Release only when
Rafael asks.

## After each change

1. `uv run tests/test_rolls.py` must print `ALL OK` (`-v` prints each case). A new chat
   line, history field or end condition gets its case. The pre-commit hook in `.githooks/`
   runs it too (enable per clone: `git config core.hooksPath .githooks`).
2. Commit and push.
3. Copy `GroupLootForever.lua` and `GroupLootForever.toc` to
   `C:\Program Files (x86)\World of Warcraft\_forever_\Interface\AddOns\GroupLootForever\`
   (and `Media\icon.tga` to its `Media\` when the icon changes).

`Media/logo.png` is the 1024 px original (Gemini, 2026-11-22); `logo-256.png` is the
README and CurseForge logo, `icon.tga` the 64 px addon list icon (Pillow resize).

The test runs the real `GroupLootForever.lua` against a stubbed API with Forever's own
chat strings. The stub follows the client: no GroupLootFrameTemplate, a missing data field
is nil, and `drawn(f)` is false for a frame anchored to one with no points. When the game
shows something the stub allowed, fix the stub too. The C_LootHistory shape in the test is the retail one, a guess until a
debug log from the game shows it.

`/glf test` copies the roll frame's parts, not its clipping, parent, scale or strata, so it
proves nothing about what is drawn outside the frame's rect: "Pending N" beside the frame
showed on the copy and not on a real roll (2026-11-23). Only a real roll confirms that.

## Debug log

Ask Rafael to type `/glf debug`, roll for loot in a group and `/reload`, then read
`C:\Program Files (x86)\World of Warcraft\_forever_\WTF\Account\*\SavedVariables\GroupLootForever.lua`
yourself. It records each roll start, chat pick, CANCEL_LOOT_ROLL, history drop with its
players and states, and why each row ended.

## Client rules

What is and is not confirmed on Forever (chat strings, C_LootHistory, CANCEL_LOOT_ROLL,
secret values, blank font strings) is in the comment at the top of
`GroupLootForever.lua`. Forever's global strings are in the GlobalStrings DB2:
`https://wago.tools/db2/GlobalStrings/csv?build=<build>`.
