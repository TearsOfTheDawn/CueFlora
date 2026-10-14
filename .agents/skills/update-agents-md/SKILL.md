---
name: update-agents-md
description: Update AGENTS.md to reflect the current state of the codebase. Use after making significant changes to the project — new/removed files, changed data structures, updated dependencies, modified build commands, or new coding patterns.
---

# Update AGENTS.md

Scan the project source files and update `AGENTS.md` at the project root to match the current codebase.

## Steps

1. Read `AGENTS.md`.
2. Scan all source files for discrepancies with what the document describes:
   - `entrypoints/` — all `.ts` files and `youtube.content/` directory
   - `utils/` — all `.ts` files
   - `native/cueflora_host/` — all `.py` files
   - `package.json`, `wxt.config.ts`, `native/pyproject.toml`
3. Update `AGENTS.md` in place. Preserve the existing structure and section ordering. Add new sections only if there is genuinely new architectural surface area. Do not remove sections unless the corresponding code has been deleted.
4. Update the "Last updated" date at the top of the file.

## Rules

- Match the existing writing style (concise, tabular where appropriate, code examples for data structures).
- Only document what exists in the codebase — no speculative content.
- Do not modify any source code. This is documentation-only.
