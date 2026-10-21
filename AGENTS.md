# Working on ios-sweet

- All new GitHub-facing content must be in English: documentation, code
  comments, commit messages, workflow labels, issues and pull requests.
  The user conversation may remain in Russian. On 2026-10-21 the user also
  requested rewriting our published changes in English; preserve the
  original upstream history and keep any recovery refs local.
- Read `NOTES.md` before starting; it contains the project goal, hardware facts,
  current blocker, local artifact locations and the next concrete action.
- The user switches agents frequently. Update the active handoff in `NOTES.md`
  after each milestone and before stopping. Record commits, CI run IDs, exact
  build/boot results and unfinished work. Distinguish observations from guesses.
- Commit completed changes. Use `gh` for GitHub Actions kernel builds and logs.
  Local single-file cross-compiles are useful before spending a CI run.
- Device bring-up uses temporary `fastboot boot` images. Preserve the Android
  installation and partition backups. The user approved (2026-10-15) using
  internal UFS for iOS and said Android may be deleted: the iOS root goes
  into the existing `userdata` partition (no GPT changes). Keep bootloaders,
  recovery, modem, persist and the backups intact, and confirm each
  destructive step with the user before running it.
- Current Munch storage decision (2026-10-21): preserve Android and plan
  dual boot with a separate 16 GiB iosroot. This supersedes overwriting
  userdata for Munch. Collect actual Munch GPT/geometry and verify PC backups
  before proposing edits; upstream Sweet geometry must not be reused.
- Latest Munch status (2026-10-21): the user explicitly waived the userdata
  backup. The16GiB split and Data recreation are complete; Android boots.
  XNU identifies iosroot read-only. Preserve Android and target only iosroot
  for the requested on-device root installation. The prepared TWRP USB
  installer requires no PC flashing and does not write GPT, userdata or boot.
  Do not re-request the waived backup. See the active NOTES.md handoff.
- Keep device dumps, serial numbers and downloaded Apple artifacts out of git.
