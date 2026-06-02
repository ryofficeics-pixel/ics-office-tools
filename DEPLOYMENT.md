# Deployment

## Vercel

Production tool URL:
- https://ics-office-tools-deploy.vercel.app/tools/daily-report

Connected Vercel project:
- `ics-office-tools-deploy`

This repository is deployed as a static site.

Configuration:
- Install command: none
- Build command: `npm run vercel-build`
- Output directory: `.`

The root `vercel.json` keeps deployment static, with a small build step to generate the browser-readable Supabase config:

```json
{
  "buildCommand": "npm run vercel-build",
  "installCommand": null,
  "outputDirectory": "."
}
```

## Supabase

Connected Supabase project:
- `crrtfddcnnqstxyoeoek`
- URL: `https://crrtfddcnnqstxyoeoek.supabase.co`
- Region: `ap-southeast-1`

Required deployment environment variables:

```text
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
```

Local development can copy `.env.example` to `.env.local`. The build script writes `assets/supabase-env.js`, and browser tools can import `assets/supabase-client.js` when they are ready to use Supabase.

## GitHub Actions

`.github/workflows/deploy-vercel.yml` deploys `main` to Vercel and injects Supabase env from GitHub Secrets.

Required GitHub repository secrets:

```text
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
VERCEL_TOKEN
VERCEL_ORG_ID
VERCEL_PROJECT_ID
```

## Local Preview

You can open the HTML files directly in a browser, or serve the repo with any static file server.

Optional npm commands:

```bash
npm run vercel-build
npm run rab:install
npm run rab:start
```

## Local RAB Engine

`tools/rab-auto-engine-local` contains a separate local Python workflow helper.

- It is intended for local use only
- It is not part of the static Vercel deployment
- Python dependencies are installed with `npm run rab:install`
- The local backend starts with `npm run rab:start`
