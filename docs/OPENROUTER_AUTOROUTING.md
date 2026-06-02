# OpenRouter Auto-Routing

This repo uses OpenRouter only as a model router and fallback layer. GitHub remains the central source of truth for project files, reviews, and changes.

The router reads `OPENROUTER_API_KEY` from `process.env` only. Do not paste the key into prompts, config files, docs, shell history examples, or committed files.

## Routes

- `audit`: stronger reasoning models first, then `openrouter/auto`.
- `code`: coding-capable models first, then `openrouter/auto`.
- `cheap`: free or low-cost models first for drafts and quick checks.
- `review`: strongest review models first, then `openrouter/auto`.

The fallback order is configured in `.agent/router.config.json` with the OpenRouter `models` array.

## PowerShell Usage

Use `npm.cmd` in Windows PowerShell when `npm.ps1` is blocked by execution policy:

```powershell
npm.cmd -v
node --check .agent/run-openrouter.mjs
node .agent/run-openrouter.mjs audit --dry-run
node .agent/run-openrouter.mjs audit
node .agent/run-openrouter.mjs code --task .agent/task.md
node .agent/run-openrouter.mjs cheap --prompt "Summarize the current task board."
node .agent/run-openrouter.mjs review --out review-notes.md
```

## CMD Usage

```bat
npm.cmd -v
node --check .agent\run-openrouter.mjs
node .agent\run-openrouter.mjs audit --dry-run
node .agent\run-openrouter.mjs audit
node .agent\run-openrouter.mjs code --task .agent\task.md
node .agent\run-openrouter.mjs cheap --prompt "Summarize the current task board."
node .agent\run-openrouter.mjs review --out review-notes.md
```

## Output

Agent responses are saved in `.agent/output/`. That folder is ignored by Git except for `.agent/output/.gitkeep`.

The script prints:
- selected route
- fallback model list
- model used by OpenRouter
- output file path

The script never prints the API key.

## Safety Boundaries

- Do not deploy from this router unless a human explicitly instructs it in a separate task.
- Do not use OpenRouter as the source of truth for repository state.
- Do not change app source from agent output without a separate review and patch step.
- Do not change storage keys without migration and backward compatibility.
