# CODEX TASK BRIEF — ICS Office Tools Full Migration
**Generated:** 2026-05-23  
**Workspace:** `C:\Users\user\Documents\New project 5`  
**Target deploy:** `https://ics-office-tools.vercel.app`  
**Supabase project:** create new at https://supabase.com (free tier ok)

---

## CONTEXT

This is a **static HTML launcher + standalone tool suite** for IC Solution (ICS), an architecture/construction firm in Indonesia. The repo has no build step — every file is plain HTML/CSS/JS deployed directly to Vercel as static output.

The launcher (`index.html`) has already been rebuilt (Phase 1 complete — see `index.html`). The remaining work is connecting Supabase, fixing the RAB backend, and migrating report tools to cloud storage.

**Non-regression rules (MUST follow at all times):**
1. Do not rebuild any working module from scratch
2. Do not change storage keys without including a migration
3. Do not touch working UI/UX, routes, forms, or buttons unless fixing a specific bug
4. Keep each fix isolated to the failing module
5. Preserve Daily Report preview layout and PDF export behavior
6. Preserve all existing localStorage and IndexedDB keys (see Storage Map below)
7. Document every change and every file intentionally not touched

---

## REPO LAYOUT

```
C:\Users\user\Documents\New project 5
├── index.html                    ← ALREADY REBUILT (Phase 1 done)
├── package.json
├── vercel.json
├── assets/logo.png
├── supabase_schema_seed.sql      ← ALREADY WRITTEN, run this first
├── tools/
│   ├── absensi-karyawan/index.html    Firebase Auth + Firestore (DO NOT TOUCH)
│   ├── absensi-admin/index.html       Firebase Auth + Firestore (DO NOT TOUCH)
│   ├── daily-report/index.html        → Phase 2 target
│   ├── progress-report/index.html     → Phase 2 target
│   ├── survey-report/index.html       → Phase 2 target
│   ├── estimator/index.html           DO NOT TOUCH (large bundled file)
│   ├── kalkulator-pembesian/index.html DO NOT TOUCH
│   └── rab-auto-engine-local/
│       ├── backend/app.py             → Phase 3 target (SQLite bug)
│       ├── frontend/index.html
│       ├── frontend/app.js
│       ├── frontend/styles.css
│       └── data/rab_auto_engine.db
└── prototypes/
    └── rab-otomatis-review.html       (standalone prototype, read-only reference)
```

---

## STORAGE MAP (do not change these keys)

| Tool | Storage |
|---|---|
| Launcher | `localStorage: ICS_DASHBOARD_LAST_OPENED` |
| Daily Report | `localStorage: ics-daily-report-v1` |
| Weekly Report | `IndexedDB: ics-local-report-groundup-v2-indexed-storage` + `localStorage: ics-local-report-groundup-v2` |
| Survey Report | `IndexedDB: ics-local-survey-v1-indexed-storage` + `localStorage: ics-local-survey-v1` |
| Estimator | `localStorage: ics_v15_*` (multiple keys) |
| RAB Otomatis prototype | `localStorage: rab_otomatis_review_draft_v1` |
| RAB backend | SQLite: `tools/rab-auto-engine-local/data/rab_auto_engine.db` |
| Absensi | Firebase Auth + Firestore project `absensi-ics` |

---

## PHASE 2 — Report Suite → Supabase

### Goal
Add Supabase cloud sync to Daily Report, Weekly Report, and Survey Report — **without breaking existing localStorage/IndexedDB behavior**. Cloud sync is additive: local-first still works, cloud is a bonus layer.

### Pattern to follow for all 3 tools

```
1. Load from Supabase on init (if credentials exist)
2. Merge with local data (Supabase wins on conflict by updated_at)
3. All writes: write to local first, then async push to Supabase
4. If Supabase fails: continue local-only, show a subtle toast
5. On backup export: include both local and cloud data
```

### Supabase credentials
Insert into each tool file (same pattern as index.html):
```js
const SUPABASE_URL      = 'https://YOUR_PROJECT.supabase.co';
const SUPABASE_ANON_KEY = 'YOUR_ANON_KEY_HERE';
```

### 2A — Daily Report (`tools/daily-report/index.html`)

**Existing storage key:** `ics-daily-report-v1`  
**Data shape (do not change):**
```json
{
  "projects": [...],
  "surveys": [...],
  "dailyReports": [...],
  "weeklyReports": [...]
}
```

**Supabase tables to create (add to supabase_schema_seed.sql):**
```sql
create table if not exists daily_reports (
  id           text primary key,
  project_id   text not null,
  report_date  date not null,
  data         jsonb not null,
  created_at   timestamptz default now(),
  updated_at   timestamptz default now()
);

create table if not exists projects (
  id          text primary key,
  name        text not null,
  data        jsonb,
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);
```

**What to add to the HTML file:**
- Supabase CDN script tag (same version as index.html: `@supabase/supabase-js@2`)
- `syncToSupabase()` async function — called after every local write
- `loadFromSupabase()` async function — called on init, merged into local
- DO NOT change: existing form logic, preview layout, PDF export, storage key

### 2B — Weekly Report (`tools/progress-report/index.html`)

**Existing storage keys:** `ics-local-report-groundup-v2` + IndexedDB  
**Reads daily data from:** `ics-daily-report-v1`

**Supabase table:**
```sql
create table if not exists weekly_reports (
  id          text primary key,
  project_id  text not null,
  week_start  date,
  data        jsonb not null,
  photos      jsonb,        -- store Supabase Storage URLs, not base64
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);
```

**Important:** Photos should be uploaded to Supabase Storage bucket `ics-reports`. Store URLs in `photos` jsonb, never base64 blobs in the DB. Local IndexedDB still holds full photos for offline use.

**What to add:** Same sync pattern as 2A. Do not change report snapshot immutability — old reports stay immutable after creation.

### 2C — Survey Report (`tools/survey-report/index.html`)

**Existing storage keys:** `ics-local-survey-v1` + IndexedDB  
**Syncs to:** `ics-daily-report-v1`

**Supabase table:**
```sql
create table if not exists survey_reports (
  id          text primary key,
  project_id  text,
  survey_date date,
  location    text,
  data        jsonb not null,
  photos      jsonb,         -- Supabase Storage URLs
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);
```

**Same photo strategy as 2B.** Cloudinary is also acceptable for photos if already integrated in survey tool — check existing code first before adding Supabase Storage.

### 2D — Supabase Storage bucket

Create bucket `ics-reports` in Supabase Storage with public read access. Upload photos as:
```
ics-reports/weekly/{project_id}/{report_id}/{filename}
ics-reports/survey/{project_id}/{survey_id}/{filename}
```

### 2E — RLS policies for Phase 2 tables

All Phase 2 tables: public read + public insert for now (auth comes in Phase 4).
```sql
alter table daily_reports  enable row level security;
alter table weekly_reports enable row level security;
alter table survey_reports enable row level security;
alter table projects       enable row level security;

-- repeat for each:
create policy "public read"   on daily_reports  for select using (true);
create policy "public insert" on daily_reports  for insert with check (true);
create policy "public update" on daily_reports  for update using (true);
```

---

## PHASE 3 — RAB Otomatis Backend Fix

### 3A — Fix SQLite INSERT bug

**File:** `tools/rab-auto-engine-local/backend/app.py`  
**Error log:**
```
sqlite3.OperationalError: table projects has 8 columns but 7 values were supplied
```

**Steps:**
1. Read the `projects` table schema from `data/rab_auto_engine.db`:
   ```python
   import sqlite3
   conn = sqlite3.connect('data/rab_auto_engine.db')
   print(conn.execute("PRAGMA table_info(projects)").fetchall())
   ```
2. Find the `INSERT INTO projects` statement in `app.py`
3. Fix: either add the missing column value, or rewrite using named columns:
   ```python
   # Use named columns — never positional for tables with many columns
   cursor.execute(
     "INSERT INTO projects (col1, col2, col3, col4, col5, col6, col7) VALUES (?,?,?,?,?,?,?)",
     (val1, val2, val3, val4, val5, val6, val7)
   )
   ```
4. Smoke test flow: diagnostics → create project → upload PDF → rasterize → detect/calibrate → generate/export

### 3B — Cloud backend option (optional, if 3A fixed and user wants cloud)

If the user wants RAB Otomatis to work without running the local FastAPI server, migrate `backend/app.py` to a **Supabase Edge Function** or deploy to **Railway** (free tier).

Supabase Edge Function approach:
- Convert each `@app.route` to a Deno handler
- Replace SQLite with Supabase PostgREST calls
- Update `frontend/app.js` to point to new endpoint URL
- Keep `start-rab-otomatis.ps1` working for local fallback

---

## PHASE 4 — Auth + RLS (do last)

### Goal
Add login so each karyawan/admin only sees their own data.

### Stack
- **Supabase Auth** (email + password, or Google OAuth)
- Absensi stays on Firebase — do not migrate
- All Phase 2 tables get user_id column + RLS update

### Steps
1. Create `tools/login/index.html` — simple email+password form using Supabase Auth JS
2. Add auth check to launcher (`index.html`) — redirect to login if not logged in
3. Add `user_id uuid references auth.users` column to all Phase 2 tables
4. Update RLS policies: `using (auth.uid() = user_id)`
5. Add user roles table:
   ```sql
   create table user_roles (
     user_id uuid references auth.users primary key,
     role    text default 'staff',   -- 'staff' | 'admin' | 'superadmin'
     name    text,
     nip     text
   );
   ```
6. Admin tools check `role = 'admin'` before rendering sensitive UI

---

## DEPLOYMENT CHECKLIST

Run these in order after each phase:

```powershell
# Static build check (must pass)
npm.cmd run vercel-build
# Expected: "Static HTML deployment ready"

# Deploy to Vercel
npx vercel deploy --prod

# Verify after deploy
# 1. Open https://ics-office-tools.vercel.app
# 2. Status chip shows "Online DB" (not "Static fallback")
# 3. All tool cards appear and launch correctly
# 4. Search and filter work
# 5. Recently opened persists across reload
```

**Vercel settings (do not change):**
```json
{
  "buildCommand": null,
  "installCommand": null,
  "outputDirectory": "."
}
```

**If Vercel misclassifies as Next.js:** set Framework to "Other" in Vercel project settings. Do not add `routes-manifest.json` or any build config.

---

## FILE TOUCH POLICY

| File | Allowed changes |
|---|---|
| `index.html` | Already done — only change SUPABASE_URL/KEY |
| `tools/daily-report/index.html` | Add Supabase sync only |
| `tools/progress-report/index.html` | Add Supabase sync only |
| `tools/survey-report/index.html` | Add Supabase sync only |
| `tools/rab-auto-engine-local/backend/app.py` | Fix INSERT bug only |
| `tools/estimator/index.html` | DO NOT TOUCH |
| `tools/kalkulator-pembesian/index.html` | DO NOT TOUCH |
| `tools/absensi-karyawan/index.html` | DO NOT TOUCH |
| `tools/absensi-admin/index.html` | DO NOT TOUCH |
| `prototypes/rab-otomatis-review.html` | DO NOT TOUCH |
| `vercel.json` | DO NOT TOUCH |

---

## KNOWN ISSUES / RISKS

1. RAB backend `/api/projects` has SQLite schema mismatch — fix in Phase 3A before testing
2. Report tools share browser storage per origin — data will not sync between `file://`, localhost, and Vercel
3. Daily Report localStorage can hit quota if large base64 photos are stored — move photos to IndexedDB or Supabase Storage
4. Absensi depends on Firebase CDN — do not add Supabase to those files
5. No git repo in this folder — make a backup copy of the whole folder before any phase

---

## RESOURCES

- Supabase JS v2 CDN: `https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js`
- Supabase dashboard: https://supabase.com/dashboard
- Vercel dashboard: https://vercel.com/dashboard
- Live URL: https://ics-office-tools.vercel.app
- Firebase project: `absensi-ics` (credentials already embedded in absensi files)
