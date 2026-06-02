# Task Board

## Active

- OpenRouter auto-routing layer added for `audit`, `code`, `cheap`, and `review` routes.
- GitHub remains the source of truth; OpenRouter is only the model fallback layer.

## Ready Next

- Run one dry-run check per route.
- Run a live smoke test with a harmless prompt after confirming `OPENROUTER_API_KEY` is available in the current shell.
- Decide whether to add a package script wrapper in a later task.

## Backlog

- Add route-specific prompt templates if repeated workflows become stable.
- Add optional JSON output mode for machine-readable review results.
- Add CI validation for `node --check .agent/run-openrouter.mjs` if this folder is moved into a Git repository.

## Done

- Added router config.
- Added system prompt and default task prompt.
- Added local output folder placeholder.
- Added usage and safety docs.
- Added Git ignore rules for env files and generated agent output.
