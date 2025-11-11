thonimport json
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from .formatters import profiles_to_table

LOGGER = logging.getLogger("instagram_profile_scraper_pro.exporters")

def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def export_json(profiles: List[Dict[str, Any]], path: Path) -> None:
    _ensure_parent_dir(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

def export_csv(profiles: List[Dict[str, Any]], path: Path) -> None:
    _ensure_parent_dir(path)
    df = profiles_to_table(profiles)
    # If no profiles, create an empty file with only headers
    if df.empty:
        LOGGER.warning("No profiles to export to CSV; creating an empty CSV with no rows.")
    df.to_csv(path, index=False, encoding="utf-8")

def export_excel(profiles: List[Dict[str, Any]], path: Path) -> None:
    _ensure_parent_dir(path)
    df = profiles_to_table(profiles)
    df.to_excel(path, index=False, engine="openpyxl")