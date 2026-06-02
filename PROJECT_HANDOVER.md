# Project Handover - IC Solution Office Tools

Generated: 2026-05-23 14:02:08 +07:00  
Workspace: `C:\Users\user\Documents\New project 5`  
Type: static HTML launcher plus standalone local tools  
Git status: this folder is not a git repository

## Executive Summary

This project is a static, local-first IC Solution Office Tools launcher. The root source of truth is `index.html` plus the `tools/` folder. Do not treat this as a Next.js/React app unless the repo shape changes later.

The launcher currently exposes these working surfaces:

- Absensi Karyawan
- Admin Absensi
- Weekly Report / Progress Report
- Daily Report
- Survey Report
- ICS Estimator
- Kalkulator Pembesian
- ROI Simulator by HuniOS, linked to external Vercel app
- Backup / Restore Guide launcher card
- RAB Otomatis, currently linked to the local FastAPI-backed module

There is also a separate standalone prototype:

- `prototypes/rab-otomatis-review.html`, a newer RAB Otomatis PDF-to-budget prototype with multi-page Sheet Analyzer and Symbol Layers flow.

## Non-Regression Rules

Follow these rules before making any future change:

1. Do not rebuild this project from scratch.
2. Do not replace working modules with new versions.
3. Do not change working UI, UX, routes, forms, buttons, storage keys, or data flows unless required by a specific bug.
4. Keep fixes isolated to the failing module.
5. Preserve Daily Report preview. If PDF export is wrong, make export match preview, not the reverse.
6. Preserve ROI Simulator calculation logic. Only performance or access changes are allowed unless explicitly requested.
7. Preserve existing dashboard navigation. Add tools as additional tiles/routes only.
8. Keep report tools local-first and same-origin where possible.
9. Avoid changing localStorage/IndexedDB keys unless migration/backward compatibility is included.
10. Document what changed, what was intentionally left unchanged, and why.

## Repository Layout

```text
C:\Users\user\Documents\New project 5
|-- index.html
|-- package.json
|-- vercel.json
|-- .vercelignore
|-- assets/
|   `-- logo.png
|-- prototypes/
|   `-- rab-otomatis-review.html
|-- tools/
|   |-- absensi-admin/index.html
|   |-- absensi-karyawan/index.html
|   |-- daily-report/index.html
|   |-- estimator/index.html
|   |-- kalkulator-pembesian/index.html
|   |-- progress-report/index.html
|   |-- survey-report/index.html
|   `-- rab-auto-engine-local/
|       |-- README.md
|       |-- requirements.txt
|       |-- start-rab-otomatis.ps1
|       |-- backend/app.py
|       |-- frontend/index.html
|       |-- frontend/app.js
|       |-- frontend/styles.css
|       |-- data/rab_auto_engine.db
|       |-- backend.log
|       |-- backend.err.log
|       `-- test-denah.pdf
|-- daily-report.html
|-- report-standalone.html
|-- survey.html
`-- ics-report-html.zip
```

Root-level `daily-report.html`, `report-standalone.html`, and `survey.html` are standalone copies. The launcher points to the `tools/*/index.html` versions.

## Launcher

Main file: `index.html`

Launcher cards are defined in the `tools` JavaScript array. Current routes:

| Card | Route / URL | Status in launcher |
| --- | --- | --- |
| Absensi Karyawan | `./tools/absensi-karyawan/index.html` | STABLE |
| Admin Absensi | `./tools/absensi-admin/index.html` | STABLE |
| Weekly Report | `./tools/progress-report/index.html` | STABLE |
| Daily Report | `./tools/daily-report/index.html` | NEW |
| Survey Report | `./tools/survey-report/index.html` | STABLE |
| ICS Estimator | `./tools/estimator/index.html` | STABLE |
| Kalkulator Pembesian | `./tools/kalkulator-pembesian/index.html` | STABLE |
| ROI Simulator by HuniOS | `https://roi-simulator-by-hunios.vercel.app` | LIVE |
| Backup / Restore Guide | no URL, informational card | ONLINE |
| RAB Otomatis | `./tools/rab-auto-engine-local/frontend/index.html` | BETA |

Launcher storage:

- `ICS_DASHBOARD_LAST_OPENED`

This only stores quick-launch history. It is not the source of operational data.

## Report Suite

The report suite is local-first. It relies on same-origin browser storage for sync between tools. Do not expect data sync between `file://`, localhost, and deployed Vercel origins.

### Daily Report

Primary file:

- `tools/daily-report/index.html`

Standalone copy:

- `daily-report.html`

Storage key:

- `ics-daily-report-v1`

Important behavior:

- Stores projects, surveys, daily reports, and weekly reports in localStorage.
- Includes project identity normalization and duplicate weekly-project migration.
- Weekly reports must stay tied to existing `projectId` values.
- Backup exports JSON named like `ics-report-backup-YYYY-MM-DD.json`.
- Restore replaces local browser report data after confirmation.

Do not change:

- Correct Daily Report preview layout.
- Existing project sync behavior unless fixing a project identity bug.
- Existing storage key without migration.

Known risk:

- localStorage quota can be exceeded if large photos/base64 payloads end up in `ics-daily-report-v1`.
- Preferred direction is to keep localStorage lightweight and store large assets in IndexedDB.

### Weekly Report / Progress Report

Primary file:

- `tools/progress-report/index.html`

Standalone copy:

- `report-standalone.html`

Storage keys:

- `ics-local-report-groundup-v2`
- old fallback key: `ics-local-report-groundup-v1`
- reads Daily data from `ics-daily-report-v1`

IndexedDB:

- database name: `ics-local-report-groundup-v2-indexed-storage`

Important behavior:

- Stores full report DB in IndexedDB.
- Writes lightweight localStorage metadata copy with empty `photos` and `reports` arrays.
- Syncs Daily Report projects/reports into Weekly context.
- Supports project profiles, photos, plans, reports, preview, PDF/print-style report pages, backup/restore.

Do not change:

- IndexedDB-first storage strategy.
- Daily sync parser unless fixing a sync bug.
- Report snapshot behavior. Old reports should stay immutable.

### Survey Report

Primary file:

- `tools/survey-report/index.html`

Standalone copy:

- `survey.html`

Storage keys:

- `ics-local-survey-v1`
- old/fallback source: `ics-local-report-groundup-v2`
- sync target/source: `ics-daily-report-v1`

IndexedDB:

- database name: `ics-local-survey-v1-indexed-storage`

Important behavior:

- Stores survey profiles, photos, and reports in IndexedDB.
- Writes lightweight localStorage metadata copy.
- Can sync survey project/report/photo summaries into Daily Report storage.

Do not change:

- Survey-to-Daily sync without preserving existing project matching.
- Photo/report snapshot behavior.

## Absensi

### Absensi Karyawan

File:

- `tools/absensi-karyawan/index.html`

Backend/service:

- Firebase project: `absensi-ics`
- Firebase Auth
- Firestore
- External time checks include Firebase/WorldTime logic.

Important behavior:

- Employee login.
- GPS/location capture.
- Camera/liveness flow.
- Attendance submission for masuk/siang/pulang.
- Biometric capability checks when available.
- Has fallback UI if Firebase CDN fails.

Do not change:

- Login, GPS, camera, liveness, and submit flows unless the request specifically targets them.
- Firebase config unless the deployment/account is intentionally changed.

### Admin Absensi

File:

- `tools/absensi-admin/index.html`

Backend/service:

- Firebase project: `absensi-ics`
- Firebase Auth
- Firestore
- Uses SheetJS CDN for Excel export.

Important behavior:

- Admin dashboard.
- User creation through secondary Firebase app.
- Attendance monitoring.
- Daily/monthly recap.
- Status classification for tepat waktu, terlambat, pulang awal, pulang terlambat.
- Export/reporting tools.
- Firestore rules helper text is embedded in the UI.

Do not change:

- Dashboard monitoring and export behavior unless directly fixing admin flow.
- Status rules without business approval.

## Estimation / Engineering Tools

### ICS Estimator

File:

- `tools/estimator/index.html`

Purpose:

- Estimasi biaya konstruksi.
- Konverter RAB Excel.
- Document output with ICS-style header/footer/signature.
- Includes bundled SheetJS logic.

Notable storage keys:

- `ics_v15_pa_price_survey`
- `ics_v15_pa_price_rab`
- `ics_v15_pa_price_design`
- `ics_v15_pa_qty_survey`
- `ics_v15_pa_qty_rab`
- `ics_v15_pa_qty_design`
- `ics_v15_pa_type_survey`
- `ics_v15_pa_type_rab`
- `ics_v15_pa_type_design`
- `ics_v15_nama_proyek`
- `ics_v15_scope_data_v1`

Do not change:

- Calculation model or Excel parsing behavior without targeted test coverage.
- Generated document header/footer styling unless the request is specifically output formatting.

### Kalkulator Pembesian

File:

- `tools/kalkulator-pembesian/index.html`

Dependencies:

- React 18 UMD CDN
- ReactDOM UMD CDN
- Babel standalone CDN
- SheetJS CDN

Purpose:

- Calculates rebar/wiremesh/concrete quantities.
- Includes export/table outputs.

Do not change:

- Structural quantity formulas unless the user explicitly requests formula changes.

## ROI Simulator

Launcher route:

- `https://roi-simulator-by-hunios.vercel.app`

Important context:

- ROI Simulator is external to this workspace.
- Previous validated behavior says its rental/appreciation calculation logic should be preserved.
- If touching launcher integration, only verify the link and category/filter behavior in `index.html`.

Do not change:

- ROI calculation logic from this workspace.
- External deployment settings unless the user requests ROI deployment work.

## RAB Otomatis - Integrated Local Backend Module

Launcher route:

- `./tools/rab-auto-engine-local/frontend/index.html`

Folder:

- `tools/rab-auto-engine-local/`

Important files:

- `README.md`
- `requirements.txt`
- `start-rab-otomatis.ps1`
- `backend/app.py`
- `frontend/index.html`
- `frontend/app.js`
- `frontend/styles.css`
- `data/rab_auto_engine.db`

Run command:

```powershell
cd "C:\Users\user\Documents\New project 5\tools\rab-auto-engine-local"
.\start-rab-otomatis.ps1
```

Expected local URL:

```text
http://127.0.0.1:8787
```

Package scripts:

```powershell
npm.cmd run rab:install
npm.cmd run rab:start
```

Known environment issue:

- The default Windows `python` on this machine was previously incomplete and missed standard library pieces like `tempfile`.
- The helper script was intended to use the bundled Codex Python fallback when needed.

Known backend issue:

- `tools/rab-auto-engine-local/backend.err.log` shows `/api/projects` failing:

```text
sqlite3.OperationalError: table projects has 8 columns but 7 values were supplied
```

Likely next fix:

- Inspect the `projects` table schema in `data/rab_auto_engine.db`.
- Fix the `INSERT INTO projects VALUES(?,?,?,?,?,?,?)` call in `backend/app.py` to either name columns explicitly or provide the correct number of values.
- Then rerun smoke flow: diagnostics -> create project -> upload PDF -> rasterize -> detect/calibrate -> generate/export.

Do not confuse this integrated backend module with the standalone prototype below.

## RAB Otomatis - Standalone Prototype

File:

- `prototypes/rab-otomatis-review.html`

Storage key:

- `rab_otomatis_review_draft_v1`

Current status:

- Most recent work was completed only in this prototype file.
- It is a standalone vanilla HTML prototype for PDF-to-budget workflow.
- It does not replace the launcher-linked backend module.

Completed features:

- Upload PDF/image flow.
- Auto Detect Workspace with canvas preview.
- Two-point scale calibration.
- Scale presets.
- Heuristic image analysis for bounds, wall pixels, room boxes, openings, and MEP symbol counts.
- Measurement view.
- Formula-driven RAB generation.
- Summary and audit.
- Print preview.
- Multi-page Sheet Analyzer / PDF Pages UI.
- Page classification helpers.
- Role override selects.
- Analyze selected pages flow.
- Symbol Layers Panel.
- Fallback acceptance buttons.
- Combined measurement apply.
- Generate RAB from combined detection.
- Symbol library export.

Current QA:

- Embedded JS syntax check passed.
- `window.__rabQaChecklist()` passed 36/36 checks under DOM stub.
- `npm.cmd run vercel-build` passed.

Known limitations:

- Detection is heuristic image processing, not real vector PDF takeoff.
- PDF rendering depends on PDF.js CDN.
- Browser plugin local URL validation was blocked by `net::ERR_BLOCKED_BY_CLIENT`.
- Standalone Playwright fallback via `npx` timed out during prior run.

Recommended next manual validation:

1. Open `prototypes/rab-otomatis-review.html` through a browser that can load local/static files.
2. Upload a multi-page PDF.
3. Confirm Sheet Analyzer renders page cards.
4. Review/correct page roles.
5. Calibrate scale.
6. Run Analyze Selected Pages.
7. Apply Combined Detection.
8. Generate RAB.
9. Check Summary, Audit, and Print Preview.

## Deployment

Static deployment config:

- `vercel.json`

```json
{
  "buildCommand": null,
  "installCommand": null,
  "outputDirectory": "."
}
```

Build check:

```powershell
npm.cmd run vercel-build
```

Expected output:

```text
Static HTML deployment ready
```

Important Vercel guidance:

- This workspace should be deployed as static output.
- If Vercel reports missing `routes-manifest.json`, it is probably misclassifying the workspace as Next.js.
- Fix Vercel framework/build/output settings instead of rewriting app code.
- Prior validated public alias from memory: `https://ics-office-tools.vercel.app`.
- Verify public route accessibility after any deploy, not only build success.

`.vercelignore` currently excludes:

```text
.vercel/output
*.zip
verification-*.png
```

## Verification Commands

Run these from:

```powershell
cd "C:\Users\user\Documents\New project 5"
```

Static build:

```powershell
npm.cmd run vercel-build
```

Prototype embedded script syntax:

```powershell
@'
const fs = require('fs');
const html = fs.readFileSync('prototypes/rab-otomatis-review.html', 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
new Function(scripts);
console.log('embedded script syntax OK');
'@ | node
```

Search for stale RAB hardcoded values:

```powershell
Select-String -LiteralPath 'prototypes\rab-otomatis-review.html' -Pattern '325\.5|533560020|533,560,020|533\.560\.020'
```

RAB backend logs:

```powershell
Get-Content -LiteralPath 'tools\rab-auto-engine-local\backend.err.log' -Tail 80
Get-Content -LiteralPath 'tools\rab-auto-engine-local\backend.log' -Tail 40
```

## Data / Storage Map

| Surface | Storage |
| --- | --- |
| Launcher | localStorage `ICS_DASHBOARD_LAST_OPENED` |
| Daily Report | localStorage `ics-daily-report-v1` |
| Weekly Report | IndexedDB `ics-local-report-groundup-v2-indexed-storage`, localStorage `ics-local-report-groundup-v2` |
| Survey Report | IndexedDB `ics-local-survey-v1-indexed-storage`, localStorage `ics-local-survey-v1` |
| Weekly/Survey sync | Reads/writes `ics-daily-report-v1` |
| Estimator | multiple `ics_v15_*` localStorage keys |
| RAB prototype | localStorage `rab_otomatis_review_draft_v1` |
| RAB backend | SQLite `tools/rab-auto-engine-local/data/rab_auto_engine.db` |
| Absensi | Firebase Auth + Firestore project `absensi-ics` |

## Known Issues / Risks

1. RAB backend `/api/projects` currently has a SQLite insert/schema mismatch.
2. RAB prototype still needs manual rendered browser QA because automated Browser was blocked.
3. Report tools share browser storage only on the same origin. Data will not automatically sync between file, localhost, and deployed domains.
4. Daily Report localStorage can hit quota if large base64 blobs are stored there.
5. Absensi depends on Firebase/CDN/network availability.
6. Kalkulator Pembesian depends on external React/Babel/SheetJS CDNs.
7. Estimator is a large single HTML file with bundled libraries; avoid broad refactors.
8. No git repository exists in this folder, so there is no commit history/diff safety net.

## Recommended Next Work Order

1. Create a backup copy of the whole folder before major changes.
2. Fix RAB backend `/api/projects` SQLite insert mismatch if the integrated launcher RAB module is needed.
3. Manually QA the standalone RAB prototype PDF flow in a normal browser.
4. If deploying, verify `https://ics-office-tools.vercel.app` route accessibility after deployment.
5. If working on reports, first export backups from Daily, Weekly, and Survey tools in-browser.
6. If fixing storage quota, move large photo/base64 payloads away from `ics-daily-report-v1` into IndexedDB while preserving migration.
7. If touching absensi, scope changes only to requested subsystem such as GPS/address; do not disturb login/camera/liveness/export unless requested.

## Files Intentionally Not Touched In Latest Handover

This handover document creation does not modify working app logic. The current handover adds only:

- `PROJECT_HANDOVER.md`

Existing app files, launcher routes, storage keys, and modules are intentionally left unchanged.

