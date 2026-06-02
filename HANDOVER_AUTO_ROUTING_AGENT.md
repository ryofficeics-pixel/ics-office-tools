# Handover: IC Solution Tools Hub

## Purpose

This document summarizes the standalone IC Solution Tools Hub for future automation work, especially an auto-routing agent that can direct users across multiple accounts, projects, and operational tools.

## Live Assets

- Production app: https://ics-tools-hub.vercel.app
- GitHub repository: https://github.com/ryofficeics-pixel/ICS-Hub
- Local workspace: `C:\Users\user\Documents\ics-tools-hub`
- Vercel project: `estora-v1/ics-tools-hub`
- Current branch: `main`

## Current App Summary

The hub is a lightweight operational launcher for IC Solution tools.

Stack:
- Vite
- HTML
- CSS
- Vanilla JavaScript
- Supabase-backed public tool registry
- No auth
- No external UI library

Core features:
- Header for IC Solution / Operational Tools Dashboard
- Search tools by name, description, category, type, or status
- Category filter chips
- Responsive tile grid
- Tool cards with metadata and launch URLs
- Disabled handling for maintenance tools
- Recently opened tracking through browser `localStorage`
- Empty state for no search results
- Backend status chip: `Online DB`, `Static fallback`, or `Backend error`
- Routing event insert attempts on successful launches

## File Map

- `index.html`: app shell and DOM targets
- `src/main.js`: Supabase loading, fallback handling, rendering, search, filters, launch actions, recent tracking
- `src/lib/supabase.js`: frontend Supabase client using only `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`
- `src/tools-data.js`: static fallback for tool cards and routing URLs
- `src/styles.css`: IC Solution visual system and responsive tile layout
- `supabase/schema.sql`: tool registry schema, RLS, grants, and policies
- `supabase/seed-tools.sql`: seed/upsert data matching current tool cards
- `README.md`: basic repo overview and commands
- `PROJECT_STATUS.md`: operational status
- `CHANGELOG.md`: release notes
- `CODEX_RESUME.md`: continuation notes
- `docs/DEPLOYMENT.md`: Vercel deployment notes
- `docs/UI_REFERENCE_SUMMARY.md`: UI design summary

## Tool Data Contract

Each tool entry in `src/tools-data.js` uses this shape:

```js
{
  id: "stable-machine-id",
  name: "Human readable tool name",
  description: "Short user-facing description",
  category: "Reports",
  type: "Online",
  status: "Live",
  url: "https://example.com/tool",
  disabled: false
}
```

Rules:
- `id` should be stable and unique.
- `name`, `description`, `category`, `type`, and `status` are searchable.
- `url` is opened in a new tab.
- `disabled: true` prevents launch and shows maintenance behavior.
- Avoid exposing internal IDs, tokens, or private environment data in these objects.

## Current Tool Categories

- Attendance
- Reports
- Projects
- Documentation
- Finance
- Operations
- Utilities

## Current Tool List

- Absensi Online
- Auto Report Progress
- Survey Report
- Weekly Report
- Project Database
- Photo Documentation
- RAB Helper
- Staff Task Tracker
- Backup Restore
- Utilities

## UI System Summary

The UI follows the IC Solution reference direction:

- Off-white background
- White card surfaces
- Soft grey borders
- Subtle shadows
- Rounded black icon blocks
- Black primary launch buttons
- Compact uppercase status pills
- Metro-inspired card/tile layout
- Mobile-first responsive grid
- No fixed card height on mobile
- No overlapping buttons or badges

## Deployment Notes

Vercel settings:
- Framework: Vite
- Install command: `npm install`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variables: none required

Useful commands:

```bash
npm install
npm run build
npx vercel deploy --prod
```

## Auto-Routing Agent Intent

The future auto-routing agent should use this hub as the central directory for operational tools. The agent can read Supabase `tools` / `tool_aliases`, or mirror `src/tools-data.js` as fallback, then route users based on:

- user role
- account identity
- project assignment
- requested workflow
- tool status
- online/local availability
- maintenance state
- preferred account or deployment target

Suggested routing logic:

1. Normalize the user request.
2. Match intent against tool names, descriptions, categories, and aliases.
3. Check user/account eligibility outside this static app.
4. Check tool status.
5. Return the correct URL and instructions.
6. If a tool is disabled or in maintenance, return fallback route or status message.
7. Track account-aware routing events in the agent layer. The static hub only records basic anonymous launch events.

## Multi-Account Routing Considerations

This hub owns only a public tool registry and anonymous routing event inserts. Multi-account routing should live in a separate agent/service layer.

Recommended external routing registry fields:

```js
{
  accountId: "account-key",
  accountName: "Account display name",
  toolId: "auto-report-progress",
  environment: "production",
  url: "https://...",
  allowedRoles: ["admin", "project_manager", "field_user"],
  status: "live",
  priority: 10
}
```

Recommended separation:
- Static hub: public directory, launcher UI, and public Supabase tool registry
- Routing agent: account-aware decision maker
- Auth provider: identity and role source
- Data services: tool-specific systems such as Supabase, Vercel, Cloudinary, or local tools

## Security Boundaries

Do not add secrets to this app.

Never store these in the repository or browser bundle:
- API tokens
- Supabase service role keys
- Cloudinary API secrets
- GitHub tokens
- Vercel tokens
- user credentials

The hub can contain public URLs and public labels only. Account-specific access control must happen in the destination app or the routing agent.

## Recommended Next Work

1. Add optional aliases per tool for better routing matches.
2. Add optional account/environment mappings in a separate JSON file if still public-safe.
3. Add an agent-readable export endpoint or static JSON file if another service needs to consume the tool registry.
4. Add Vercel Git integration checks for automatic redeploy on every push.
5. Keep the static hub independent from auth and private database code unless a future requirement explicitly changes the architecture.

## Current Known Limitations

- No built-in authentication.
- No per-account filtering inside the UI.
- No backend route for a machine-readable registry yet.
- Recently opened tools are stored only in each browser through `localStorage`.
- Supabase routing events are anonymous and intentionally minimal.
- Tool URLs currently point to the existing deployed ICS Office Tools routes and placeholder/fallback routes where applicable.
