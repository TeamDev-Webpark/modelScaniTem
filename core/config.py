"""
Configuration module for modelScaniTem backend & database.
"""
import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parents[1]  # project root (core/ -> ..)

# Load environment variables from .env
load_dotenv(BASE_DIR / ".env")

# Raw Database URL from environment
RAW_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:1234@localhost:5432/model_stcan_item"
).strip()

def normalize_db_url(url: str) -> str:
    """
    Normalizes PostgreSQL URL for SQLAlchemy compatibility:
    1. Replaces postgres:// or postgresql:// with postgresql+psycopg2:// (or postgresql+psycopg://)
    2. Handles missing slash between port and database name (e.g. :5432dbname -> :5432/dbname)
    """
    # Detect available driver
    driver_prefix = "postgresql+psycopg2://"
    try:
        import psycopg2
        driver_prefix = "postgresql+psycopg2://"
    except ImportError:
        try:
            import psycopg
            driver_prefix = "postgresql+psycopg://"
        except ImportError:
            driver_prefix = "postgresql+psycopg2://"

    # Fix schema prefix
    if url.startswith("postgres://"):
        url = driver_prefix + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = driver_prefix + url[len("postgresql://"):]

    # Fix port without trailing slash: e.g. localhost:5432model_stcan_item -> localhost:5432/model_stcan_item
    url = re.sub(r':(\d{2,5})([a-zA-Z_][a-zA-Z0-9_]*)', r':\1/\2', url)
    return url

DATABASE_URL = normalize_db_url(RAW_DB_URL)

# Admin authentication defaults
SECRET_KEY = os.getenv("SECRET_KEY", "tool_scanner_secret_key_2026")
ADMIN_DEFAULT_USER = os.getenv("ADMIN_DEFAULT_USER", "admin")
ADMIN_DEFAULT_PASS = os.getenv("ADMIN_DEFAULT_PASS", "admin1234")

# Admin app uploads: training images, trained models, dataset exports
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "admin_data")
IMAGES_DIR = DATA_DIR / "images"
MODELS_DIR = DATA_DIR / "models"
EXPORTS_DIR = DATA_DIR / "exports"

# Master data: tray templates, tool catalog, checklist and reference photos (tracked in git)
MASTER_DATA_DIR = BASE_DIR / "data"
TRAY_TEMPLATES_DIR = MASTER_DATA_DIR / "tray_templates"
CATALOG_PATH = MASTER_DATA_DIR / "data.json"                     # รายการเครื่องมือ + ภาพตัวอย่าง
CHECKLIST_PATH = MASTER_DATA_DIR / "merchandise_checklist.json"  # Excel Merchandise Visit Checklist
CHECKLIST_MAPPING_PATH = MASTER_DATA_DIR / "checklist_slot_mapping.json"
CLASSES_70_PATH = MASTER_DATA_DIR / "classes_ya1_2_70_tools.json"
TRAY_REFS_DIR = MASTER_DATA_DIR / "tray_refs"   # ภาพถาดต้นแบบ (<tray_id>.jpg) และถาดว่าง (<tray_id>_empty.jpg)
SAMPLE_IMAGES_DIR = MASTER_DATA_DIR / "sample_images"

# Test / evaluation outputs (json/csv tracked, images ignored)
REPORTS_DIR = BASE_DIR / "reports"
CHECKLIST_MATCH_DIR = REPORTS_DIR / "checklist_match"
SCAN_SIMULATION_DIR = REPORTS_DIR / "scan_simulation"
REAL_PHOTO_TEST_DIR = REPORTS_DIR / "real_photo_test"
TRAY_REFS_CHECK_DIR = REPORTS_DIR / "tray_refs_check"
BENCHMARK_PATH = REPORTS_DIR / "benchmark_3_trays_results.json"
BLUEPRINTS_DIR = REPORTS_DIR / "blueprints"

# Raw Yamaha photos outside the repo (optional), e.g. C:/MyProject/Webpark/dataYamaha
# Scripts use it as the default for --photos / --images when it is set.
_ext = os.getenv("YAMAHA_DATA_DIR", "").strip()
YAMAHA_DATA_DIR = Path(_ext) if _ext else None
TRAY_PHOTOS_DIR = YAMAHA_DATA_DIR / "Merchecklist" / "Tools" / "tian" if YAMAHA_DATA_DIR else None

# Ensure required directories exist
for path in [DATA_DIR, IMAGES_DIR, MODELS_DIR, EXPORTS_DIR]:
    path.mkdir(parents=True, exist_ok=True)
