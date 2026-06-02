from __future__ import annotations

import ast
import csv
import json
import math
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = BASE_DIR / "data"
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
PAGES_DIR = STORAGE_DIR / "pages"
THUMBS_DIR = STORAGE_DIR / "thumbs"
DATASET_DIR = BASE_DIR / "datasets" / "mep_symbols"
MODEL_PATH = BASE_DIR / "models" / "mep_symbols.pt"
DB_PATH = DATA_DIR / "rab_auto_engine.db"

for folder in [DATA_DIR, UPLOAD_DIR, PAGES_DIR, THUMBS_DIR, DATASET_DIR / "images", DATASET_DIR / "labels"]:
    folder.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="RAB Auto Engine Local", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    out = dict(row)
    for key in ["files", "pages", "pointA", "pointB", "boundingBox", "polyline", "polygon", "centerPoint", "parameters", "variables", "defaultValues", "assumptions", "before", "after"]:
        if key in out:
            out[key] = loads(out[key], [] if key.endswith("s") or key in {"polyline", "polygon", "variables", "assumptions"} else {})
    for key in ["locked", "manualOverride", "confirmed"]:
        if key in out:
            out[key] = bool(out[key])
    return out


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects(
  id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT, location TEXT,
  createdAt TEXT, updatedAt TEXT, files TEXT DEFAULT '[]', pages TEXT DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS files(
  id TEXT PRIMARY KEY, projectId TEXT, name TEXT, originalPath TEXT, storedPath TEXT,
  fileType TEXT, category TEXT, pageCount INTEGER DEFAULT 0, uploadDate TEXT, status TEXT
);
CREATE TABLE IF NOT EXISTS pages(
  id TEXT PRIMARY KEY, projectId TEXT, fileId TEXT, pageNumber INTEGER, category TEXT,
  imagePath TEXT, thumbnailPath TEXT, widthPx INTEGER, heightPx INTEGER, rotation REAL DEFAULT 0,
  scale TEXT, calibration TEXT, status TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS calibrations(
  id TEXT PRIMARY KEY, projectId TEXT, pageId TEXT, method TEXT, drawingScaleText TEXT,
  pointA TEXT, pointB TEXT, realDistanceM REAL, pixelDistance REAL, pixelToMeterRatio REAL,
  confirmed INTEGER DEFAULT 0, createdAt TEXT
);
CREATE TABLE IF NOT EXISTS ocr_results(
  id TEXT PRIMARY KEY, projectId TEXT, pageId TEXT, text TEXT, boundingBox TEXT,
  confidence TEXT, numericConfidence REAL, type TEXT, source TEXT, status TEXT
);
CREATE TABLE IF NOT EXISTS walls(
  id TEXT PRIMARY KEY, projectId TEXT, pageId TEXT, wallType TEXT, polyline TEXT,
  lengthM REAL, thicknessM REAL, source TEXT, confidence TEXT, status TEXT, confirmed INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS rooms(
  id TEXT PRIMARY KEY, projectId TEXT, pageId TEXT, roomName TEXT, polygon TEXT,
  areaM2 REAL, perimeterM REAL, source TEXT, confidence TEXT, status TEXT, confirmed INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS openings(
  id TEXT PRIMARY KEY, projectId TEXT, pageId TEXT, type TEXT, widthM REAL, heightM REAL,
  areaM2 REAL, count INTEGER, boundingBox TEXT, source TEXT, confidence TEXT, status TEXT
);
CREATE TABLE IF NOT EXISTS mep_symbols(
  id TEXT PRIMARY KEY, projectId TEXT, pageId TEXT, className TEXT, label TEXT, boundingBox TEXT,
  centerPoint TEXT, source TEXT, confidence TEXT, numericConfidence REAL, status TEXT, confirmed INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS routes(
  id TEXT PRIMARY KEY, projectId TEXT, pageId TEXT, routeType TEXT, polyline TEXT,
  lengthM REAL, diameterOrSpec TEXT, assignedItemId TEXT, source TEXT, confidence TEXT, status TEXT
);
CREATE TABLE IF NOT EXISTS structural_inputs(
  id TEXT PRIMARY KEY, projectId TEXT, category TEXT, itemName TEXT, lengthM REAL, widthM REAL,
  heightM REAL, thicknessM REAL, areaM2 REAL, volumeM3 REAL, count REAL, diameterMm REAL,
  spacingMm REAL, notes TEXT, source TEXT, confidence TEXT, status TEXT
);
CREATE TABLE IF NOT EXISTS formulas(
  id TEXT PRIMARY KEY, name TEXT, category TEXT, unit TEXT, expression TEXT, variables TEXT,
  defaultValues TEXT, wasteFactor REAL, assumptions TEXT, notes TEXT, version TEXT, createdAt TEXT, updatedAt TEXT
);
CREATE TABLE IF NOT EXISTS rab_items(
  id TEXT PRIMARY KEY, projectId TEXT, category TEXT, itemName TEXT, description TEXT, unit TEXT,
  formulaId TEXT, parameters TEXT, volume REAL, unitPrice REAL, totalPrice REAL, source TEXT,
  confidence TEXT, status TEXT, notes TEXT, locked INTEGER DEFAULT 0, manualOverride INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS price_items(
  id TEXT PRIMARY KEY, itemName TEXT, normalizedName TEXT, category TEXT, unit TEXT, brand TEXT,
  spec TEXT, region TEXT, supplier TEXT, approvedPrice REAL, lowPrice REAL, medianPrice REAL,
  highPrice REAL, lastUpdated TEXT, volatility TEXT, status TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS audit_logs(
  id TEXT PRIMARY KEY, projectId TEXT, timestamp TEXT, action TEXT, entityType TEXT,
  entityId TEXT, before TEXT, after TEXT, note TEXT
);
"""


STARTER_FORMULAS = [
    ("Pembersihan lokasi", "Pekerjaan Persiapan", "m2", "floor_area", ["floor_area"]),
    ("Bowplank", "Pekerjaan Persiapan", "m", "total_wall_length * waste_factor", ["total_wall_length"]),
    ("Galian pondasi", "Pekerjaan Tanah", "m3", "excavation_length * excavation_width * excavation_depth", ["excavation_length", "excavation_width", "excavation_depth"]),
    ("Urugan kembali", "Pekerjaan Tanah", "m3", "foundation_length * excavation_width * excavation_depth * 0.35", ["foundation_length", "excavation_width", "excavation_depth"]),
    ("Urugan pasir bawah lantai", "Pekerjaan Tanah", "m3", "floor_area * sand_thickness", ["floor_area", "sand_thickness"]),
    ("Pondasi batu kali", "Pekerjaan Pondasi", "m3", "foundation_length * foundation_cross_section_area * waste_factor", ["foundation_length", "foundation_cross_section_area"]),
    ("Beton sloof", "Pekerjaan Beton", "m3", "sloof_length * sloof_width * sloof_height * waste_factor", ["sloof_length", "sloof_width", "sloof_height"]),
    ("Beton kolom", "Pekerjaan Beton", "m3", "column_count * column_width * column_depth * column_height * waste_factor", ["column_count", "column_width", "column_depth", "column_height"]),
    ("Beton balok", "Pekerjaan Beton", "m3", "beam_length * beam_width * beam_height * waste_factor", ["beam_length", "beam_width", "beam_height"]),
    ("Beton plat lantai", "Pekerjaan Beton", "m3", "slab_area * slab_thickness * waste_factor", ["slab_area", "slab_thickness"]),
    ("Besi sloof", "Pekerjaan Pembesian", "kg", "rebar_weight * waste_factor", ["rebar_weight"]),
    ("Wiremesh", "Pekerjaan Pembesian", "m2", "wiremesh_area * waste_factor", ["wiremesh_area"]),
    ("Bekisting sloof", "Pekerjaan Bekisting", "m2", "sloof_length * (sloof_height * 2) * waste_factor", ["sloof_length", "sloof_height"]),
    ("Pasangan bata ringan", "Pekerjaan Dinding", "m2", "(total_wall_length * wall_height - opening_area) * waste_factor", ["total_wall_length", "wall_height", "opening_area"]),
    ("Pasangan bata merah", "Pekerjaan Dinding", "m2", "(total_wall_length * wall_height - opening_area) * waste_factor", ["total_wall_length", "wall_height", "opening_area"]),
    ("Plester dinding", "Pekerjaan Plester Aci", "m2", "(total_wall_length * wall_height - opening_area) * side_count * waste_factor", ["total_wall_length", "wall_height", "opening_area", "side_count"]),
    ("Aci dinding", "Pekerjaan Plester Aci", "m2", "plaster_area", ["plaster_area"]),
    ("Keramik lantai", "Pekerjaan Lantai", "m2", "floor_area * waste_factor", ["floor_area"]),
    ("Plint keramik", "Pekerjaan Lantai", "m", "room_perimeter * waste_factor", ["room_perimeter"]),
    ("Rangka plafon", "Pekerjaan Plafon", "m2", "ceiling_area * waste_factor", ["ceiling_area"]),
    ("Penutup plafon gypsum/PVC", "Pekerjaan Plafon", "m2", "ceiling_area * waste_factor", ["ceiling_area"]),
    ("Rangka atap", "Pekerjaan Atap", "m2", "roof_area * waste_factor", ["roof_area"]),
    ("Kusen", "Pekerjaan Kusen/Pintu/Jendela", "unit", "opening_count", ["opening_count"]),
    ("Cat dinding dalam", "Pekerjaan Cat", "m2", "wall_paint_area * coat_factor", ["wall_paint_area", "coat_factor"]),
    ("Cat plafon", "Pekerjaan Cat", "m2", "ceiling_area * coat_factor", ["ceiling_area", "coat_factor"]),
    ("Closet", "Pekerjaan Sanitair", "unit", "count_CLOSET", ["count_CLOSET"]),
    ("Wastafel", "Pekerjaan Sanitair", "unit", "count_WASTAFEL", ["count_WASTAFEL"]),
    ("Floor drain", "Pekerjaan Sanitair", "unit", "count_FLOOR_DRAIN", ["count_FLOOR_DRAIN"]),
    ("Pipa air bersih", "Pekerjaan Plumbing", "m", "clean_water_pipe_length * waste_factor", ["clean_water_pipe_length"]),
    ("Pipa air kotor", "Pekerjaan Plumbing", "m", "waste_water_pipe_length * waste_factor", ["waste_water_pipe_length"]),
    ("Pipa vent", "Pekerjaan Plumbing", "m", "vent_pipe_length * waste_factor", ["vent_pipe_length"]),
    ("Titik lampu", "Pekerjaan Listrik", "titik", "count_LAMP_POINT", ["count_LAMP_POINT"]),
    ("Titik saklar", "Pekerjaan Listrik", "titik", "count_SWITCH", ["count_SWITCH"]),
    ("Titik stop kontak", "Pekerjaan Listrik", "titik", "count_SOCKET", ["count_SOCKET"]),
    ("Titik AC", "Pekerjaan Listrik", "titik", "count_AC_POINT", ["count_AC_POINT"]),
    ("Conduit", "Pekerjaan Listrik", "m", "electrical_conduit_length * waste_factor", ["electrical_conduit_length"]),
]


def init_db() -> None:
    with db() as conn:
        conn.executescript(SCHEMA)
        count = conn.execute("SELECT COUNT(*) FROM formulas").fetchone()[0]
        if count == 0:
            for name, category, unit, expression, variables in STARTER_FORMULAS:
                fid = new_id("formula")
                defaults = {v: 0 for v in variables}
                defaults["waste_factor"] = 1.05
                conn.execute(
                    "INSERT INTO formulas VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (fid, name, category, unit, expression, dumps(variables), dumps(defaults), 1.05, dumps(["Formula starter, wajib review estimator."]), "", "1.0", now_iso(), now_iso()),
                )


init_db()


class Payload(BaseModel):
    data: dict[str, Any] = {}


class SafeEval(ast.NodeVisitor):
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name, ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.Call)
    funcs = {"min": min, "max": max, "round": round, "ceil": math.ceil, "floor": math.floor}

    def __init__(self, params: dict[str, Any]):
        self.params = params

    def visit(self, node: ast.AST) -> Any:
        if not isinstance(node, self.allowed):
            raise ValueError(f"Operator tidak diizinkan: {type(node).__name__}")
        return super().visit(node)

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Hanya angka yang diizinkan")

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id not in self.params or self.params[node.id] in (None, ""):
            raise KeyError(node.id)
        return float(self.params[node.id])

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        value = self.visit(node.operand)
        return -value if isinstance(node.op, ast.USub) else value

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left, right = self.visit(node.left), self.visit(node.right)
        if isinstance(node.op, ast.Add): return left + right
        if isinstance(node.op, ast.Sub): return left - right
        if isinstance(node.op, ast.Mult): return left * right
        if isinstance(node.op, ast.Div): return left / right if right else 0
        raise ValueError("Operator tidak didukung")

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name) or node.func.id not in self.funcs:
            raise ValueError("Fungsi tidak diizinkan")
        return self.funcs[node.func.id](*[self.visit(arg) for arg in node.args])


def safe_calculate(expression: str, params: dict[str, Any]) -> tuple[float | None, str | None]:
    try:
        tree = ast.parse(expression, mode="eval")
        return float(SafeEval(params).visit(tree)), None
    except KeyError as exc:
        return None, f"Parameter hilang: {exc.args[0]}"
    except Exception as exc:
        return None, str(exc)


def audit(project_id: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    with db() as conn:
        pages = [row_to_dict(r) for r in conn.execute("SELECT * FROM pages WHERE projectId=?", (project_id,))]
        for page in pages:
            if not loads(page.get("calibration"), {}).get("pixelToMeterRatio"):
                issues.append(issue("Kalibrasi skala belum ada", "BLOCKER", page["id"], "Page", "Kalibrasi halaman sebelum menghitung volume."))
        for table, label in [("walls", "Dinding"), ("rooms", "Ruang"), ("mep_symbols", "Simbol MEP")]:
            rows = conn.execute(f"SELECT * FROM {table} WHERE projectId=? AND status!='USER_CONFIRMED'", (project_id,)).fetchall()
            for row in rows:
                issues.append(issue(f"{label} belum dikonfirmasi", "MEDIUM", row["id"], table, "Review overlay dan confirm jika benar."))
        for row in conn.execute("SELECT * FROM rab_items WHERE projectId=?", (project_id,)):
            item = row_to_dict(row)
            if item["status"] == "MISSING_DATA":
                issues.append(issue("Item RAB kekurangan parameter", "HIGH", item["id"], "RAB", "Lengkapi parameter atau isi manual override."))
            if not item.get("unitPrice"):
                issues.append(issue("Harga satuan belum ada", "HIGH", item["id"], "Harga", "Isi database harga atau harga manual."))
            if item.get("confidence") == "LOW":
                issues.append(issue("Item memakai sumber confidence rendah", "MEDIUM", item["id"], "RAB", "Validasi sumber dan konfirmasi manual."))
        for row in conn.execute("SELECT * FROM routes WHERE projectId=? AND (diameterOrSpec IS NULL OR diameterOrSpec='')", (project_id,)):
            issues.append(issue("Jalur belum punya diameter/spec", "MEDIUM", row["id"], "Route", "Isi diameter pipa atau spesifikasi conduit/kabel."))
    return issues


def issue(text: str, severity: str, related: str, source: str, action: str) -> dict[str, str]:
    return {"id": new_id("audit"), "issue": text, "severity": severity, "relatedItem": related, "source": source, "recommendedAction": action, "status": "OPEN"}


def get_page(page_id: str) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute("SELECT * FROM pages WHERE id=?", (page_id,)).fetchone()
    page = row_to_dict(row)
    if not page:
        raise HTTPException(404, "Halaman tidak ditemukan")
    return page


def pixel_ratio(page: dict[str, Any]) -> float | None:
    cal = loads(page.get("calibration"), {})
    return cal.get("pixelToMeterRatio")


def image_fs_path(image_path: str) -> Path:
    return BASE_DIR / image_path.lstrip("/").replace("/", os.sep).replace("storage" + os.sep, "storage" + os.sep)


def classify_ocr(text: str) -> str:
    t = text.lower()
    if "skala" in t or "scale" in t: return "SCALE_TEXT"
    if any(unit in t for unit in [" mm", " cm", " m", "x"]) and any(ch.isdigit() for ch in t): return "DIMENSION"
    if any(word in t for word in ["kamar", "ruang", "dapur", "teras", "wc", "toilet"]): return "ROOM_NAME"
    if any(word in t for word in ["pvc", "ppr", "kabel", "lampu", "saklar", "stop kontak"]): return "MEP_NOTE"
    if any(word in t for word in ["kolom", "balok", "sloof", "pondasi", "besi"]): return "STRUCTURAL_NOTE"
    return "UNKNOWN_TEXT"


@app.get("/")
def root() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/diagnostics")
def diagnostics() -> dict[str, Any]:
    def import_check(name: str) -> dict[str, str]:
        try:
            __import__(name)
            return {"status": "OK", "message": f"{name} tersedia"}
        except Exception as exc:
            return {"status": "Missing", "message": str(exc)}

    def cmd_check(cmd: str, optional: bool = False) -> dict[str, str]:
        path = shutil.which(cmd)
        if not path:
            return {"status": "Optional Missing" if optional else "Missing", "message": f"{cmd} tidak ditemukan di PATH"}
        try:
            out = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=4)
            return {"status": "OK", "message": (out.stdout or out.stderr).splitlines()[0] if (out.stdout or out.stderr) else path}
        except Exception:
            return {"status": "OK", "message": path}

    return {
        "python": {"status": "OK", "message": sys.version.split()[0]},
        "node": cmd_check("node", optional=True),
        "opencv": import_check("cv2"),
        "pymupdf": import_check("fitz"),
        "pytesseract": import_check("pytesseract"),
        "tesseract": cmd_check("tesseract", optional=False),
        "sqlite": {"status": "OK", "message": sqlite3.sqlite_version},
        "ultralytics": import_check("ultralytics") if shutil.which("yolo") else {"status": "Optional Missing", "message": "Ultralytics/YOLO opsional belum tersedia"},
        "yoloModel": {"status": "OK" if MODEL_PATH.exists() else "Optional Missing", "message": str(MODEL_PATH)},
        "ollama": cmd_check("ollama", optional=True),
        "storageWritable": {"status": "OK" if os.access(STORAGE_DIR, os.W_OK) else "Error", "message": str(STORAGE_DIR)},
    }


@app.get("/api/projects")
def list_projects() -> list[dict[str, Any]]:
    with db() as conn:
        return [row_to_dict(r) for r in conn.execute("SELECT * FROM projects ORDER BY updatedAt DESC")]


@app.post("/api/projects")
def create_project(payload: Payload) -> dict[str, Any]:
    data = payload.data
    project = {
        "id": new_id("project"),
        "name": data.get("name") or "Proyek RAB Baru",
        "type": data.get("type") or "Bangunan",
        "location": data.get("location") or "",
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }
    with db() as conn:
        conn.execute(
            "INSERT INTO projects(id,name,type,location,createdAt,updatedAt,files,pages) VALUES(?,?,?,?,?,?,?,?)",
            (project["id"], project["name"], project["type"], project["location"], project["createdAt"], project["updatedAt"], "[]", "[]"),
        )
    return project


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    with db() as conn:
        project = row_to_dict(conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
    if not project:
        raise HTTPException(404, "Proyek tidak ditemukan")
    project["pages"] = pages(project_id)
    project["files"] = files(project_id)
    return project


@app.put("/api/projects/{project_id}")
def update_project(project_id: str, payload: Payload) -> dict[str, Any]:
    data = payload.data
    with db() as conn:
        before = row_to_dict(conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
        if not before: raise HTTPException(404, "Proyek tidak ditemukan")
        merged = {**before, **data, "updatedAt": now_iso()}
        conn.execute("UPDATE projects SET name=?, type=?, location=?, updatedAt=? WHERE id=?", (merged["name"], merged["type"], merged["location"], merged["updatedAt"], project_id))
    return get_project(project_id)


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str) -> dict[str, str]:
    with db() as conn:
        for table in ["files", "pages", "calibrations", "ocr_results", "walls", "rooms", "openings", "mep_symbols", "routes", "structural_inputs", "rab_items", "audit_logs"]:
            conn.execute(f"DELETE FROM {table} WHERE projectId=?", (project_id,))
        conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
    return {"status": "deleted"}


def files(project_id: str) -> list[dict[str, Any]]:
    with db() as conn:
        return [row_to_dict(r) for r in conn.execute("SELECT * FROM files WHERE projectId=? ORDER BY uploadDate DESC", (project_id,))]


def pages(project_id: str) -> list[dict[str, Any]]:
    with db() as conn:
        return [row_to_dict(r) for r in conn.execute("SELECT * FROM pages WHERE projectId=? ORDER BY pageNumber", (project_id,))]


@app.post("/api/projects/{project_id}/upload-pdf")
async def upload_pdf(project_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Hanya file PDF yang didukung")
    file_id = new_id("file")
    stored = UPLOAD_DIR / f"{file_id}.pdf"
    with stored.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    rec = {"id": file_id, "projectId": project_id, "name": file.filename, "storedPath": f"/storage/uploads/{file_id}.pdf", "status": "UPLOADED"}
    with db() as conn:
        conn.execute("INSERT INTO files VALUES(?,?,?,?,?,?,?,?,?,?)", (file_id, project_id, file.filename, file.filename, str(stored), "PDF", "DRAWING", 0, now_iso(), "UPLOADED"))
    return {"file": rec, "message": "PDF tersimpan. Jalankan rasterize untuk konversi halaman."}


@app.post("/api/projects/{project_id}/rasterize")
def rasterize(project_id: str, payload: Payload | None = None) -> dict[str, Any]:
    try:
        import fitz
        from PIL import Image
    except Exception as exc:
        raise HTTPException(503, f"PyMuPDF/Pillow belum tersedia: {exc}")
    dpi = int((payload.data if payload else {}).get("dpi", 180))
    created = []
    with db() as conn:
        file_rows = conn.execute("SELECT * FROM files WHERE projectId=? AND status IN ('UPLOADED','RASTERIZE_ERROR')", (project_id,)).fetchall()
        for f in file_rows:
            try:
                doc = fitz.open(f["storedPath"])
                conn.execute("UPDATE files SET pageCount=?, status=? WHERE id=?", (doc.page_count, "RASTERIZED", f["id"]))
                for i, page in enumerate(doc, start=1):
                    page_id = new_id("page")
                    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
                    image_file = PAGES_DIR / f"{page_id}.png"
                    pix.save(str(image_file))
                    thumb_file = THUMBS_DIR / f"{page_id}.jpg"
                    img = Image.open(image_file)
                    img.thumbnail((280, 220))
                    img.save(thumb_file, quality=78)
                    image_path = f"/storage/pages/{page_id}.png"
                    thumb_path = f"/storage/thumbs/{page_id}.jpg"
                    conn.execute("INSERT INTO pages VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (page_id, project_id, f["id"], i, "UNKNOWN", image_path, thumb_path, pix.width, pix.height, 0, "", "{}", "RASTERIZED", ""))
                    created.append({"id": page_id, "pageNumber": i, "imagePath": image_path, "thumbnailPath": thumb_path, "widthPx": pix.width, "heightPx": pix.height})
            except Exception as exc:
                conn.execute("UPDATE files SET status=? WHERE id=?", ("RASTERIZE_ERROR", f["id"]))
                return {"status": "ERROR", "message": str(exc), "pages": created}
    return {"status": "OK", "pages": created}


@app.get("/api/projects/{project_id}/pages")
def api_pages(project_id: str) -> list[dict[str, Any]]:
    return pages(project_id)


@app.put("/api/pages/{page_id}/category")
def update_category(page_id: str, payload: Payload) -> dict[str, Any]:
    with db() as conn:
        conn.execute("UPDATE pages SET category=? WHERE id=?", (payload.data.get("category", "UNKNOWN"), page_id))
    return get_page(page_id)


@app.put("/api/pages/{page_id}/calibration")
def update_calibration(page_id: str, payload: Payload) -> dict[str, Any]:
    page = get_page(page_id)
    data = payload.data
    method = data.get("method", "MANUAL_SCALE")
    ratio = data.get("pixelToMeterRatio")
    pixel_distance = data.get("pixelDistance")
    if method == "TWO_POINT":
        a, b = data.get("pointA") or {}, data.get("pointB") or {}
        pixel_distance = math.dist([a.get("x", 0), a.get("y", 0)], [b.get("x", 0), b.get("y", 0)])
        real = float(data.get("realDistanceM") or 0)
        ratio = real / pixel_distance if pixel_distance and real else None
    elif method == "MANUAL_SCALE":
        denominator = float(str(data.get("drawingScaleText") or "1:100").split(":")[-1] or 100)
        # approximate screen ratio until user performs two-point calibration
        ratio = float(data.get("pixelToMeterRatio") or denominator / 3779.5275591)
    if not ratio:
        raise HTTPException(400, "Kalibrasi butuh pixelToMeterRatio atau dua titik dengan jarak nyata")
    cal = {**data, "method": method, "pixelDistance": pixel_distance, "pixelToMeterRatio": ratio, "confirmed": bool(data.get("confirmed", True)), "createdAt": now_iso()}
    cal_id = new_id("cal")
    with db() as conn:
        conn.execute("INSERT INTO calibrations VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (cal_id, page["projectId"], page_id, method, data.get("drawingScaleText", ""), dumps(data.get("pointA", {})), dumps(data.get("pointB", {})), data.get("realDistanceM"), pixel_distance, ratio, 1 if cal["confirmed"] else 0, cal["createdAt"]))
        conn.execute("UPDATE pages SET calibration=?, scale=?, status=? WHERE id=?", (dumps(cal), data.get("drawingScaleText", ""), "CALIBRATED", page_id))
    return get_page(page_id)


@app.post("/api/pages/{page_id}/detect-walls")
def detect_walls(page_id: str) -> dict[str, Any]:
    page = get_page(page_id)
    ratio = pixel_ratio(page)
    try:
        import cv2
        import numpy as np
    except Exception as exc:
        raise HTTPException(503, f"OpenCV belum tersedia: {exc}")
    img = cv2.imread(str(image_fs_path(page["imagePath"])))
    if img is None: raise HTTPException(404, "Image halaman tidak ditemukan")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    edges = cv2.Canny(gray, 60, 160, apertureSize=3)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=1)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=90, minLineLength=60, maxLineGap=14)
    output = []
    if lines is not None:
        for line in lines[:500]:
            x1, y1, x2, y2 = [int(v) for v in line[0]]
            pix_len = math.dist([x1, y1], [x2, y2])
            if pix_len < 60: continue
            length_m = pix_len * ratio if ratio else None
            conf = "HIGH" if pix_len > 400 and ratio else "MEDIUM" if pix_len > 160 else "LOW"
            item = {"id": new_id("wall"), "projectId": page["projectId"], "pageId": page_id, "wallType": "UNKNOWN_WALL", "polyline": [{"x": x1, "y": y1}, {"x": x2, "y": y2}], "lengthM": length_m, "thicknessM": None, "source": "OpenCV", "confidence": conf if ratio else "LOW", "status": "NEEDS_REVIEW", "confirmed": False}
            output.append(item)
    with db() as conn:
        conn.execute("DELETE FROM walls WHERE pageId=? AND source='OpenCV' AND confirmed=0", (page_id,))
        for w in output:
            conn.execute("INSERT INTO walls VALUES(?,?,?,?,?,?,?,?,?,?,?)", (w["id"], w["projectId"], page_id, w["wallType"], dumps(w["polyline"]), w["lengthM"], w["thicknessM"], w["source"], w["confidence"], w["status"], 0))
    return {"status": "OK", "walls": output, "note": "Hasil OpenCV adalah kandidat dan wajib review."}


@app.post("/api/pages/{page_id}/detect-rooms")
def detect_rooms(page_id: str) -> dict[str, Any]:
    page = get_page(page_id)
    ratio = pixel_ratio(page)
    try:
        import cv2
    except Exception as exc:
        raise HTTPException(503, f"OpenCV belum tersedia: {exc}")
    img = cv2.imread(str(image_fs_path(page["imagePath"])), cv2.IMREAD_GRAYSCALE)
    if img is None: raise HTTPException(404, "Image halaman tidak ditemukan")
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 7)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rooms_out = []
    img_area = img.shape[0] * img.shape[1]
    for contour in contours[:300]:
        area = cv2.contourArea(contour)
        if area < img_area * 0.002 or area > img_area * 0.65: continue
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.015 * peri, True)
        if len(approx) < 4 or len(approx) > 30: continue
        poly = [{"x": int(p[0][0]), "y": int(p[0][1])} for p in approx]
        item = {"id": new_id("room"), "projectId": page["projectId"], "pageId": page_id, "roomName": "Ruang perlu review", "polygon": poly, "areaM2": area * ratio * ratio if ratio else None, "perimeterM": peri * ratio if ratio else None, "source": "OpenCV", "confidence": "MEDIUM" if ratio else "LOW", "status": "NEEDS_REVIEW", "confirmed": False}
        rooms_out.append(item)
    with db() as conn:
        conn.execute("DELETE FROM rooms WHERE pageId=? AND source='OpenCV' AND confirmed=0", (page_id,))
        for r in rooms_out:
            conn.execute("INSERT INTO rooms VALUES(?,?,?,?,?,?,?,?,?,?,?)", (r["id"], r["projectId"], page_id, r["roomName"], dumps(r["polygon"]), r["areaM2"], r["perimeterM"], r["source"], r["confidence"], r["status"], 0))
    return {"status": "OK", "rooms": rooms_out}


@app.post("/api/pages/{page_id}/run-ocr")
def run_ocr(page_id: str) -> dict[str, Any]:
    page = get_page(page_id)
    try:
        import pytesseract
        from PIL import Image
    except Exception as exc:
        raise HTTPException(503, f"pytesseract/Pillow belum tersedia: {exc}")
    if not shutil.which("tesseract"):
        return {"status": "MISSING_DEPENDENCY", "message": "OCR tidak tersedia: executable Tesseract belum ada di PATH.", "results": []}
    image = Image.open(image_fs_path(page["imagePath"]))
    try:
        data = pytesseract.image_to_data(image, lang="ind+eng", output_type=pytesseract.Output.DICT)
    except Exception as exc:
        return {"status": "ERROR", "message": f"OCR gagal: {exc}", "results": []}
    results = []
    for i, text in enumerate(data.get("text", [])):
        text = (text or "").strip()
        if len(text) < 2: continue
        numeric = float(data.get("conf", [0])[i] or 0)
        if numeric < 15: continue
        bbox = {"x": data["left"][i], "y": data["top"][i], "w": data["width"][i], "h": data["height"][i]}
        conf = "HIGH" if numeric >= 75 else "MEDIUM" if numeric >= 45 else "LOW"
        row = {"id": new_id("ocr"), "projectId": page["projectId"], "pageId": page_id, "text": text, "boundingBox": bbox, "confidence": conf, "numericConfidence": numeric, "type": classify_ocr(text), "source": "OCR", "status": "OCR_EXTRACTED" if conf != "LOW" else "NEEDS_REVIEW"}
        results.append(row)
    with db() as conn:
        conn.execute("DELETE FROM ocr_results WHERE pageId=? AND status!='USER_CONFIRMED'", (page_id,))
        for r in results:
            conn.execute("INSERT INTO ocr_results VALUES(?,?,?,?,?,?,?,?,?,?)", (r["id"], r["projectId"], page_id, r["text"], dumps(r["boundingBox"]), r["confidence"], r["numericConfidence"], r["type"], r["source"], r["status"]))
    return {"status": "OK", "results": results}


@app.post("/api/pages/{page_id}/detect-mep-yolo")
def detect_mep_yolo(page_id: str) -> dict[str, Any]:
    if not MODEL_PATH.exists():
        return {"status": "MODEL_MISSING", "message": "Model YOLO MEP belum tersedia", "detections": []}
    try:
        from ultralytics import YOLO
    except Exception as exc:
        return {"status": "MISSING_DEPENDENCY", "message": f"Ultralytics belum tersedia: {exc}", "detections": []}
    page = get_page(page_id)
    model = YOLO(str(MODEL_PATH))
    results = model(str(image_fs_path(page["imagePath"])), verbose=False)
    detections = []
    names = model.names
    for res in results:
        for box in res.boxes:
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            cls = names[int(box.cls[0])]
            conf = float(box.conf[0])
            detections.append({"id": new_id("mep"), "projectId": page["projectId"], "pageId": page_id, "className": cls, "label": cls, "boundingBox": {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1}, "centerPoint": {"x": (x1 + x2) / 2, "y": (y1 + y2) / 2}, "source": "YOLO", "confidence": "HIGH" if conf > 0.75 else "MEDIUM" if conf > 0.45 else "LOW", "numericConfidence": conf, "status": "NEEDS_REVIEW", "confirmed": False})
    with db() as conn:
        for d in detections:
            conn.execute("INSERT INTO mep_symbols VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (d["id"], d["projectId"], page_id, d["className"], d["label"], dumps(d["boundingBox"]), dumps(d["centerPoint"]), d["source"], d["confidence"], d["numericConfidence"], d["status"], 0))
    return {"status": "OK", "detections": detections}


ENTITY_TABLES = {"walls": "walls", "rooms": "rooms", "mep-symbols": "mep_symbols", "routes": "routes", "openings": "openings", "structural-inputs": "structural_inputs"}


@app.get("/api/projects/{project_id}/entities")
def get_entities(project_id: str) -> dict[str, Any]:
    with db() as conn:
        return {
            "walls": [row_to_dict(r) for r in conn.execute("SELECT * FROM walls WHERE projectId=?", (project_id,))],
            "rooms": [row_to_dict(r) for r in conn.execute("SELECT * FROM rooms WHERE projectId=?", (project_id,))],
            "ocrResults": [row_to_dict(r) for r in conn.execute("SELECT * FROM ocr_results WHERE projectId=?", (project_id,))],
            "mepSymbols": [row_to_dict(r) for r in conn.execute("SELECT * FROM mep_symbols WHERE projectId=?", (project_id,))],
            "routes": [row_to_dict(r) for r in conn.execute("SELECT * FROM routes WHERE projectId=?", (project_id,))],
            "openings": [row_to_dict(r) for r in conn.execute("SELECT * FROM openings WHERE projectId=?", (project_id,))],
            "structuralInputs": [row_to_dict(r) for r in conn.execute("SELECT * FROM structural_inputs WHERE projectId=?", (project_id,))],
        }


@app.post("/api/pages/{page_id}/{entity_type}")
def create_entity(page_id: str, entity_type: str, payload: Payload) -> dict[str, Any]:
    if entity_type not in ENTITY_TABLES: raise HTTPException(404, "Entity tidak didukung")
    page = get_page(page_id); data = payload.data; eid = data.get("id") or new_id(entity_type.rstrip("s").replace("-", "_"))
    with db() as conn:
        if entity_type == "mep-symbols":
            bbox = data.get("boundingBox", {"x": 0, "y": 0, "w": 24, "h": 24}); center = data.get("centerPoint") or {"x": bbox.get("x", 0) + bbox.get("w", 0)/2, "y": bbox.get("y", 0) + bbox.get("h", 0)/2}
            conn.execute("INSERT INTO mep_symbols VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (eid, page["projectId"], page_id, data.get("className", "UNKNOWN"), data.get("label", ""), dumps(bbox), dumps(center), data.get("source", "Manual"), data.get("confidence", "HIGH"), data.get("numericConfidence"), data.get("status", "MANUAL_TAGGED"), 1 if data.get("confirmed") else 0))
        elif entity_type == "routes":
            ratio = pixel_ratio(page); poly = data.get("polyline", [])
            pix = sum(math.dist([poly[i-1]["x"], poly[i-1]["y"]], [poly[i]["x"], poly[i]["y"]]) for i in range(1, len(poly))) if len(poly) > 1 else 0
            length = data.get("lengthM") or (pix * ratio if ratio else None)
            conn.execute("INSERT INTO routes VALUES(?,?,?,?,?,?,?,?,?,?,?)", (eid, page["projectId"], page_id, data.get("routeType", "UNKNOWN_ROUTE"), dumps(poly), length, data.get("diameterOrSpec", ""), data.get("assignedItemId", ""), data.get("source", "Manual"), data.get("confidence", "HIGH" if ratio else "LOW"), data.get("status", "MANUAL_MEASURED" if ratio else "NEEDS_REVIEW")))
        elif entity_type == "openings":
            area = (float(data.get("widthM") or 0) * float(data.get("heightM") or 0) * float(data.get("count") or 1)) or data.get("areaM2")
            conn.execute("INSERT INTO openings VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (eid, page["projectId"], page_id, data.get("type", "UNKNOWN_OPENING"), data.get("widthM"), data.get("heightM"), area, data.get("count", 1), dumps(data.get("boundingBox", {})), data.get("source", "Manual"), data.get("confidence", "HIGH"), data.get("status", "MANUAL_TAGGED")))
        elif entity_type == "structural-inputs":
            volume = data.get("volumeM3") or ((float(data.get("lengthM") or 0) * float(data.get("widthM") or 0) * float(data.get("heightM") or data.get("thicknessM") or 0) * float(data.get("count") or 1)) or None)
            conn.execute("INSERT INTO structural_inputs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (eid, page["projectId"], data.get("category", "STRUKTUR"), data.get("itemName", "Item struktur"), data.get("lengthM"), data.get("widthM"), data.get("heightM"), data.get("thicknessM"), data.get("areaM2"), volume, data.get("count"), data.get("diameterMm"), data.get("spacingMm"), data.get("notes", ""), data.get("source", "Manual"), data.get("confidence", "HIGH"), data.get("status", "MANUAL_TAGGED")))
        else:
            raise HTTPException(400, "Gunakan endpoint deteksi atau tipe manual lain")
    return {"id": eid, "status": "saved"}


@app.put("/api/entities/{entity_type}/{entity_id}")
def update_entity(entity_type: str, entity_id: str, payload: Payload) -> dict[str, Any]:
    table = ENTITY_TABLES.get(entity_type)
    if not table: raise HTTPException(404, "Entity tidak didukung")
    data = payload.data
    allowed = {
        "walls": ["wallType", "polyline", "lengthM", "thicknessM", "confidence", "status", "confirmed"],
        "rooms": ["roomName", "polygon", "areaM2", "perimeterM", "confidence", "status", "confirmed"],
        "mep_symbols": ["className", "label", "boundingBox", "centerPoint", "confidence", "status", "confirmed"],
        "routes": ["routeType", "polyline", "lengthM", "diameterOrSpec", "assignedItemId", "confidence", "status"],
        "openings": ["type", "widthM", "heightM", "areaM2", "count", "boundingBox", "confidence", "status"],
        "structural_inputs": ["category", "itemName", "lengthM", "widthM", "heightM", "thicknessM", "areaM2", "volumeM3", "count", "diameterMm", "spacingMm", "notes", "confidence", "status"],
    }[table]
    sets, vals = [], []
    for k in allowed:
        if k in data:
            sets.append(f"{k}=?")
            vals.append(dumps(data[k]) if isinstance(data[k], (dict, list)) else (1 if data[k] is True else 0 if data[k] is False else data[k]))
    if not sets: return {"status": "no-change"}
    vals.append(entity_id)
    with db() as conn:
        conn.execute(f"UPDATE {table} SET {', '.join(sets)} WHERE id=?", vals)
    return {"status": "updated"}


@app.delete("/api/entities/{entity_type}/{entity_id}")
def delete_entity(entity_type: str, entity_id: str) -> dict[str, str]:
    table = ENTITY_TABLES.get(entity_type)
    if not table: raise HTTPException(404, "Entity tidak didukung")
    with db() as conn:
        conn.execute(f"DELETE FROM {table} WHERE id=?", (entity_id,))
    return {"status": "deleted"}


@app.get("/api/formulas")
def get_formulas() -> list[dict[str, Any]]:
    with db() as conn:
        return [row_to_dict(r) for r in conn.execute("SELECT * FROM formulas ORDER BY category,name")]


@app.post("/api/formulas")
def create_formula(payload: Payload) -> dict[str, Any]:
    data = payload.data; fid = new_id("formula")
    with db() as conn:
        conn.execute("INSERT INTO formulas VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (fid, data.get("name", "Formula baru"), data.get("category", "Manual"), data.get("unit", "unit"), data.get("expression", "manual_input"), dumps(data.get("variables", ["manual_input"])), dumps(data.get("defaultValues", {})), data.get("wasteFactor", 1), dumps(data.get("assumptions", [])), data.get("notes", ""), data.get("version", "1.0"), now_iso(), now_iso()))
    return {"id": fid, "status": "saved"}


@app.post("/api/formulas/calculate")
def calculate_formula(payload: Payload) -> dict[str, Any]:
    value, error = safe_calculate(payload.data.get("expression", "0"), payload.data.get("parameters", {}))
    return {"value": value, "error": error}


def collect_parameters(project_id: str) -> dict[str, float]:
    with db() as conn:
        wall_length = sum([r["lengthM"] or 0 for r in conn.execute("SELECT lengthM FROM walls WHERE projectId=?", (project_id,))])
        room_area = sum([r["areaM2"] or 0 for r in conn.execute("SELECT areaM2 FROM rooms WHERE projectId=?", (project_id,))])
        room_peri = sum([r["perimeterM"] or 0 for r in conn.execute("SELECT perimeterM FROM rooms WHERE projectId=?", (project_id,))])
        opening_area = sum([r["areaM2"] or 0 for r in conn.execute("SELECT areaM2 FROM openings WHERE projectId=?", (project_id,))])
        params = {"total_wall_length": wall_length, "floor_area": room_area, "ceiling_area": room_area, "room_area": room_area, "room_perimeter": room_peri, "opening_area": opening_area, "wall_height": 3, "side_count": 2, "waste_factor": 1.05, "coat_factor": 2}
        for r in conn.execute("SELECT className, COUNT(*) c FROM mep_symbols WHERE projectId=? GROUP BY className", (project_id,)):
            params[f"count_{r['className']}"] = r["c"]
        route_map = {"CLEAN_WATER_PIPE": "clean_water_pipe_length", "WASTE_WATER_PIPE": "waste_water_pipe_length", "VENT_PIPE": "vent_pipe_length", "ELECTRICAL_CONDUIT": "electrical_conduit_length", "MAIN_CABLE_ROUTE": "main_cable_route_length"}
        for r in conn.execute("SELECT routeType, SUM(lengthM) s FROM routes WHERE projectId=? GROUP BY routeType", (project_id,)):
            params[route_map.get(r["routeType"], r["routeType"].lower() + "_length")] = r["s"] or 0
        for s in conn.execute("SELECT * FROM structural_inputs WHERE projectId=?", (project_id,)):
            key = (s["itemName"] or "").lower().replace(" ", "_")
            if s["lengthM"]: params[f"{key}_length"] = s["lengthM"]
            if s["volumeM3"]: params[f"{key}_volume"] = s["volumeM3"]
    return params


@app.post("/api/projects/{project_id}/generate-rab")
def generate_rab(project_id: str) -> dict[str, Any]:
    params = collect_parameters(project_id)
    items = []
    with db() as conn:
        formulas = [row_to_dict(r) for r in conn.execute("SELECT * FROM formulas ORDER BY category,name")]
        for f in formulas:
            fparams = {**loads(f.get("defaultValues"), {}), **params, "waste_factor": f.get("wasteFactor") or 1}
            value, error = safe_calculate(f["expression"], fparams)
            status = "MISSING_DATA" if error else "NEEDS_REVIEW"
            confidence = "LOW" if error else "MEDIUM"
            price = conn.execute("SELECT approvedPrice FROM price_items WHERE normalizedName=? OR itemName=? ORDER BY lastUpdated DESC LIMIT 1", (f["name"].lower(), f["name"])).fetchone()
            unit_price = float(price["approvedPrice"]) if price and price["approvedPrice"] else 0
            item = {"id": new_id("rab"), "projectId": project_id, "category": f["category"], "itemName": f["name"], "description": f["name"], "unit": f["unit"], "formulaId": f["id"], "parameters": fparams, "volume": value, "unitPrice": unit_price, "totalPrice": (value or 0) * unit_price, "source": "Formula + Takeoff", "confidence": confidence, "status": status, "notes": error or "Draft, wajib review.", "locked": False, "manualOverride": False}
            conn.execute("INSERT INTO rab_items VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (item["id"], project_id, item["category"], item["itemName"], item["description"], item["unit"], item["formulaId"], dumps(item["parameters"]), item["volume"], item["unitPrice"], item["totalPrice"], item["source"], item["confidence"], item["status"], item["notes"], 0, 0))
            items.append(item)
    return {"status": "OK", "items": items}


@app.get("/api/projects/{project_id}/rab")
def get_rab(project_id: str) -> list[dict[str, Any]]:
    with db() as conn:
        return [row_to_dict(r) for r in conn.execute("SELECT * FROM rab_items WHERE projectId=? ORDER BY category,itemName", (project_id,))]


@app.put("/api/rab/{item_id}")
def update_rab(item_id: str, payload: Payload) -> dict[str, Any]:
    data = payload.data
    with db() as conn:
        row = row_to_dict(conn.execute("SELECT * FROM rab_items WHERE id=?", (item_id,)).fetchone())
        if not row: raise HTTPException(404, "Item RAB tidak ditemukan")
        merged = {**row, **data}
        if data.get("manualOverride") or data.get("volume") is not None:
            merged["manualOverride"] = True
        if not merged.get("locked") and not merged.get("manualOverride") and merged.get("formulaId"):
            f = row_to_dict(conn.execute("SELECT * FROM formulas WHERE id=?", (merged["formulaId"],)).fetchone())
            if f:
                val, err = safe_calculate(f["expression"], loads(merged.get("parameters"), merged.get("parameters") or {}))
                merged["volume"] = val
                merged["status"] = "MISSING_DATA" if err else merged.get("status", "NEEDS_REVIEW")
                merged["notes"] = err or merged.get("notes", "")
        merged["totalPrice"] = (float(merged.get("volume") or 0) * float(merged.get("unitPrice") or 0))
        conn.execute("UPDATE rab_items SET category=?, itemName=?, description=?, unit=?, formulaId=?, parameters=?, volume=?, unitPrice=?, totalPrice=?, source=?, confidence=?, status=?, notes=?, locked=?, manualOverride=? WHERE id=?", (merged["category"], merged["itemName"], merged["description"], merged["unit"], merged["formulaId"], dumps(merged.get("parameters", {})), merged["volume"], merged["unitPrice"], merged["totalPrice"], merged["source"], merged["confidence"], merged["status"], merged["notes"], 1 if merged.get("locked") else 0, 1 if merged.get("manualOverride") else 0, item_id))
        conn.execute("INSERT INTO audit_logs VALUES(?,?,?,?,?,?,?,?,?)", (new_id("auditlog"), row["projectId"], now_iso(), "UPDATE_RAB", "RABItem", item_id, dumps(row), dumps(merged), "Edit item RAB"))
    return {"status": "updated", "item": merged}


@app.post("/api/rab/{item_id}/confirm")
def confirm_rab(item_id: str) -> dict[str, str]:
    with db() as conn:
        conn.execute("UPDATE rab_items SET status='USER_CONFIRMED', confidence='HIGH' WHERE id=?", (item_id,))
    return {"status": "confirmed"}


@app.post("/api/rab/{item_id}/lock")
def lock_rab(item_id: str, payload: Payload | None = None) -> dict[str, str]:
    locked = bool((payload.data if payload else {}).get("locked", True))
    with db() as conn:
        conn.execute("UPDATE rab_items SET locked=? WHERE id=?", (1 if locked else 0, item_id))
    return {"status": "locked" if locked else "unlocked"}


@app.get("/api/prices")
def prices() -> list[dict[str, Any]]:
    with db() as conn:
        return [row_to_dict(r) for r in conn.execute("SELECT * FROM price_items ORDER BY category,itemName")]


@app.post("/api/prices")
def create_price(payload: Payload) -> dict[str, Any]:
    d = payload.data; pid = d.get("id") or new_id("price")
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO price_items VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (pid, d.get("itemName", "Item harga"), d.get("normalizedName", d.get("itemName", "")).lower(), d.get("category", ""), d.get("unit", ""), d.get("brand", ""), d.get("spec", ""), d.get("region", ""), d.get("supplier", ""), d.get("approvedPrice", 0), d.get("lowPrice"), d.get("medianPrice"), d.get("highPrice"), d.get("lastUpdated", now_iso()[:10]), d.get("volatility", "MEDIUM"), d.get("status", "MANUAL"), d.get("notes", "")))
    return {"id": pid, "status": "saved"}


@app.post("/api/prices/import-csv")
async def import_prices_csv(file: UploadFile = File(...)) -> dict[str, Any]:
    content = (await file.read()).decode("utf-8-sig")
    rows = list(csv.DictReader(content.splitlines()))
    saved = 0
    with db() as conn:
        for r in rows:
            pid = new_id("price")
            name = r.get("itemName") or r.get("Uraian") or r.get("name") or "Item"
            conn.execute("INSERT INTO price_items VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (pid, name, name.lower(), r.get("category", ""), r.get("unit", r.get("Satuan", "")), r.get("brand", ""), r.get("spec", ""), r.get("region", ""), r.get("supplier", ""), float(r.get("approvedPrice") or r.get("Harga") or 0), None, None, None, r.get("lastUpdated", now_iso()[:10]), r.get("volatility", "MEDIUM"), r.get("status", "MANUAL"), r.get("notes", "")))
            saved += 1
    return {"status": "OK", "saved": saved}


@app.get("/api/prices/export-csv")
def export_prices_csv() -> PlainTextResponse:
    rows = prices()
    cols = ["itemName", "category", "unit", "brand", "spec", "region", "supplier", "approvedPrice", "lastUpdated", "volatility", "status", "notes"]
    lines = [",".join(cols)]
    for r in rows:
        lines.append(",".join([json.dumps(r.get(c, ""), ensure_ascii=False)[1:-1] for c in cols]))
    return PlainTextResponse("\n".join(lines), media_type="text/csv")


@app.get("/api/projects/{project_id}/audit")
@app.post("/api/projects/{project_id}/run-audit")
def run_audit(project_id: str) -> dict[str, Any]:
    return {"issues": audit(project_id)}


@app.get("/api/projects/{project_id}/export/rab-json")
def export_rab_json(project_id: str) -> JSONResponse:
    return JSONResponse({"projectId": project_id, "items": get_rab(project_id)})


@app.get("/api/projects/{project_id}/export/rab-csv")
def export_rab_csv(project_id: str) -> PlainTextResponse:
    rows = get_rab(project_id)
    cols = ["No", "Uraian Pekerjaan", "Satuan", "Volume", "Harga Satuan", "Jumlah Harga", "Keterangan"]
    lines = [",".join(cols)]
    for i, r in enumerate(rows, start=1):
        vals = [i, r["itemName"], r["unit"], r.get("volume") or "", r.get("unitPrice") or "", r.get("totalPrice") or "", r.get("notes") or ""]
        lines.append(",".join(json.dumps(v, ensure_ascii=False) for v in vals))
    return PlainTextResponse("\n".join(lines), media_type="text/csv")


@app.get("/api/projects/{project_id}/export/printable-html")
def printable_html(project_id: str) -> HTMLResponse:
    rows = get_rab(project_id)
    trs = "".join(f"<tr><td>{i}</td><td>{r['itemName']}</td><td>{r['unit']}</td><td>{r.get('volume') or ''}</td><td>{r.get('unitPrice') or 0:,.0f}</td><td>{r.get('totalPrice') or 0:,.0f}</td><td>{r.get('notes') or ''}</td></tr>" for i, r in enumerate(rows, 1))
    return HTMLResponse(f"<!doctype html><html><head><meta charset='utf-8'><title>RAB</title><style>body{{font-family:Arial;margin:28px}}table{{width:100%;border-collapse:collapse}}td,th{{border:1px solid #999;padding:6px;font-size:12px}}th{{background:#eee}}</style></head><body><h1>Draft RAB</h1><table><thead><tr><th>No</th><th>Uraian</th><th>Satuan</th><th>Volume</th><th>Harga Satuan</th><th>Jumlah</th><th>Keterangan</th></tr></thead><tbody>{trs}</tbody></table><p>Draft sampai user konfirmasi.</p></body></html>")


@app.get("/api/projects/{project_id}/export/audit")
def export_audit(project_id: str) -> JSONResponse:
    return JSONResponse({"projectId": project_id, "issues": audit(project_id)})


@app.get("/api/projects/{project_id}/export/mep-dataset")
def export_mep_dataset(project_id: str) -> dict[str, Any]:
    classes = ["LAMP_POINT", "DOWNLIGHT", "WALL_LAMP", "SWITCH", "SOCKET", "AC_POINT", "EXHAUST_FAN", "PANEL", "MCB", "GROUNDING_POINT", "FLOOR_DRAIN", "CLOSET", "WASTAFEL", "SHOWER", "KRAN", "CLEAN_OUT", "ROOF_DRAIN", "SEPTIC_TANK", "WATER_TANK", "PUMP", "PIPE_CLEAN_WATER", "PIPE_WASTE_WATER", "PIPE_VENT"]
    with db() as conn:
        symbols = [row_to_dict(r) for r in conn.execute("SELECT * FROM mep_symbols WHERE projectId=?", (project_id,))]
        page_map = {r["id"]: row_to_dict(r) for r in conn.execute("SELECT * FROM pages WHERE projectId=?", (project_id,))}
    copied = set()
    for s in symbols:
        page = page_map.get(s["pageId"])
        if not page: continue
        src = image_fs_path(page["imagePath"])
        img_name = f"{page['id']}.png"
        if img_name not in copied and src.exists():
            shutil.copy2(src, DATASET_DIR / "images" / img_name); copied.add(img_name)
        label_path = DATASET_DIR / "labels" / f"{page['id']}.txt"
        bbox = s.get("boundingBox") or {}; cls_idx = classes.index(s["className"]) if s["className"] in classes else 0
        x = (bbox.get("x", 0) + bbox.get("w", 0)/2) / max(page["widthPx"], 1); y = (bbox.get("y", 0) + bbox.get("h", 0)/2) / max(page["heightPx"], 1)
        w = bbox.get("w", 0) / max(page["widthPx"], 1); h = bbox.get("h", 0) / max(page["heightPx"], 1)
        with label_path.open("a", encoding="utf-8") as f:
            f.write(f"{cls_idx} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")
    (DATASET_DIR / "data.yaml").write_text("path: .\ntrain: images\nval: images\nnames:\n" + "\n".join([f"  {i}: {c}" for i, c in enumerate(classes)]), encoding="utf-8")
    (DATASET_DIR / "mep_symbols.json").write_text(dumps(symbols), encoding="utf-8")
    return {"status": "OK", "datasetPath": str(DATASET_DIR), "symbols": len(symbols), "classes": classes}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8787, reload=True)
