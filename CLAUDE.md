@AGENTS.md

## Claude Code notes

- The workflows listed in AGENTS.md are skills here: `/handoff`, `/regenerate-data`,
  `/geocode` and `/ai-parse`.
- `.claude/settings.json` pre-approves the tests, both parsers and read-only git
  commands, and blocks edits under `Sperry-Tech-Challenge/`. Put personal settings in
  `.claude/settings.local.json` and personal notes in `CLAUDE.local.md`. Both are
  git-ignored.
- The commands in AGENTS.md are written for the Bash tool (Git Bash on Windows).
- Some contributors run the `dcg` command guard. It blocks `rm -rf`, branch deletion
  and shell redirects to paths held in variables. If it blocks something, ask the user
  instead of working around it.
- Another session or a teammate may be working in the same checkout. Check
  `git status` before switching branches, and stage files by name, not with
  `git add -A`.
