# ICS Office Tools

Static office tooling for IC Solution, published as a Vercel-friendly site with a small collection of browser-based operational tools.

Live app:
- [Daily Report](https://ics-office-tools-deploy.vercel.app/tools/daily-report)

Included tools:
- Daily report
- Survey report
- Progress report
- Attendance admin
- Attendance karyawan
- Estimator
- Kalkulator pembesian
- Local RAB auto engine helper

## Project Structure

- `index.html`: landing page for the tool hub
- `tools/`: individual tool entry points
- `assets/`: shared static assets
- `docs/`: supporting project docs
- `prototypes/`: experimental UI/prototype files

## Local Usage

This project is mostly static HTML, CSS, and JavaScript, so you can open `index.html` directly or serve the folder with any static server.

Available npm scripts:

```bash
npm run vercel-build
npm run rab:install
npm run rab:start
```

Notes:
- `vercel-build` is a placeholder used for static deployment.
- `rab:start` runs the local Python backend inside `tools/rab-auto-engine-local`.
- The RAB local engine is a local helper and is not part of the static Vercel deployment.

## Deployment

The connected Vercel project is `ics-office-tools-deploy`.

- No install step required
- Build step: `npm run vercel-build`
- Output directory: project root (`.`)

Deployment behavior is defined in `vercel.json`.

## Supabase

Supabase is wired through static browser helpers:
- `assets/supabase-env.js`: generated config for the browser
- `assets/supabase-client.js`: reusable Supabase browser client

The linked Supabase project is `crrtfddcnnqstxyoeoek`. Keep `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` in local/Vercel/GitHub environment variables.
