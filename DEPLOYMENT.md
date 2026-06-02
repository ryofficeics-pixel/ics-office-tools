# Deployment

## Vercel

Production tool URL:
- https://ics-office-tools-deploy.vercel.app/tools/daily-report

Connected Vercel project:
- `ics-office-tools-deploy`

This repository is deployed as a static site.

Configuration:
- Install command: none
- Build command: none
- Output directory: `.`

The root `vercel.json` intentionally keeps deployment simple:

```json
{
  "buildCommand": null,
  "installCommand": null,
  "outputDirectory": "."
}
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
