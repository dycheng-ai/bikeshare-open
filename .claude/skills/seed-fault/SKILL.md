---
name: seed-fault
description: Seed one deliberate fault into the pipeline, record the red test
  output and hook stderr in docs/SEEDED_FAULTS.md, then wait before fixing.
  Use when asked to seed, inject, or demonstrate a fault.
allowed-tools: Read, Edit, Bash(python -m pytest*), Bash(make*), Bash(git diff*)
---
# Seeding a fault: $ARGUMENTS

1. Make exactly the one edit described above. Change nothing else.
2. If the PostToolUse hook printed stderr, keep it verbatim. Do not summarise it.
3. Run `python -m pytest tests/ -q` and keep the full output.
   If nothing fails, say so plainly: a suite that stays green under a seeded
   fault is a finding, not a success.
4. Append to docs/SEEDED_FAULTS.md under a heading naming the fault: the
   `git diff` of the change, the red test output, and the hook stderr, all
   pasted verbatim inside code blocks.
5. Stop and wait. Do not fix the fault until told to.

When told to fix: restore the original behaviour, run `make test`, show it
green, and append one line to docs/SEEDED_FAULTS.md saying how many turns the
fix took.
