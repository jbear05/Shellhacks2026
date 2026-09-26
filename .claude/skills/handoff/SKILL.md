---
name: handoff
description: Update docs/status.md, and any topic doc whose facts changed, so the next session or a teammate can pick up the work with no other context. Use at the end of a work session, before stopping with unmerged work, or when asked to wrap up, write a handoff, or update the status or notes.
---

# Handoff

The next reader starts cold: a new agent session or a teammate who wasn't here. Leave
docs/status.md true and current, and put durable facts in the topic docs.

## 1. Find out what changed

```bash
git status --short
git branch -vv
git log --oneline -20 --all --since="<the 'Last updated' date in docs/status.md>"
git diff main...HEAD --stat
```

Also go over this session's own work: what was tried, what failed and why, what was
decided, and what's half done.

## 2. Update docs/status.md

- **Last updated:** today's date.
- **Done:** add finished work with its PR link. Remove nothing that's still true.
- **Next steps:** remove finished items, add new ones, and keep them in priority order.
  Each item should say where to start.
- **Branches:** every branch that matters, with its owner and state (pushed? merged?).
- **Open issues:** add problems found, with IDs, file names and counts, and remove the
  ones that were fixed.

Keep it short. Status is what changes from session to session; anything that stays
true belongs in a topic doc.

## 3. Move durable facts to their topic doc

| What you learned | Where it goes |
|---|---|
| A CSV column was added, removed or changed meaning | docs/data.md (the tests fail until it's there) |
| Something about a PDF's layout or content | docs/sources/georgia-power-pdf.md or docs/sources/dominion-pdf.md |
| How the Geolocator behaves, or a wrong lookup | docs/geolocator.md |
| A stage's design or planned method | docs/pipeline.md |
| A choice between options, and why | docs/decisions.md (append, dated) |
| A command, rule or pitfall every session needs | AGENTS.md (keep it short) |

## 4. Rules for what you write

- Check every number by running something (count rows, run the parser). Don't copy
  it from memory or from an older doc.
- Say what you didn't verify.
- One fact in one place: link to it instead of repeating it.
- Plain, specific sentences: IDs, file names, counts, dates.
- Don't describe uncommitted work as done.

## 5. Check and hand over

```bash
.venv/Scripts/python -m pytest -m "not slow"
```

`tests/test_docs.py` checks links and the column tables in docs/data.md. Show the user
the doc diff. Commit only if they ask, and stage the files by name.
