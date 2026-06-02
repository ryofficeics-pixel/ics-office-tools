# Agent Rules

## Source of Truth

GitHub remains the central source of truth. OpenRouter is only the model router and fallback layer.

## Repository Safety

- Do not modify working app source unless the task explicitly requires it.
- Do not rewrite working modules.
- Do not replace existing modules with new versions.
- Do not rename routes, keys, components, functions, or storage structures without migration and backward compatibility.
- Do not invent missing files.
- Use `CODEX_ICS_OFFICE_TOOLS.md` as the master project brief if present.
- Keep changes minimal, isolated, and justified by the requested issue.

## Secrets

- Read `OPENROUTER_API_KEY` from `process.env` only.
- Do not print API keys, tokens, or credentials.
- Do not save secrets into files.
- Do not commit `.env` or `.env.*`.
- Do not commit `.agent/output/*` except `.agent/output/.gitkeep`.

## Deployment

Do not deploy production unless explicitly instructed.

## Output Expectations

Return practical patch plans by default. Return unified diffs only when requested. When unsure whether a module is working, inspect first and preserve existing behavior by default.
