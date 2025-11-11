thonimport json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure local src directory is on the path when running directly
CURRENT_FILE = Path(__file__).resolve()
SRC_DIR = CURRENT_FILE.parent
PROJECT_ROOT = SRC_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from extractors.instagram_parser import fetch_profile  # type: ignore  # noqa: E402
from outputs.exporters import export_json, export_csv  # type: ignore  # noqa: E402

LOGGER = logging.getLogger("instagram_profile_scraper_pro")

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

def load_settings(config_path: Optional[Path] = None) -> Dict[str, Any]:
    if config_path is None:
        config_path = SRC_DIR / "config" / "settings.example.json"

    if not config_path.exists():
        LOGGER.warning(
            "Settings file %s not found. Falling back to default settings.", config_path
        )
        # Reasonable defaults
        return {
            "max_posts": 12,
            "request_timeout": 10,
            "user_agent": "Mozilla/5.0 (compatible; InstagramProfileScraperPro/1.0)",
            "concurrent_requests": 4,
            "output": {
                "json": "data/results.json",
                "csv": "data/results.csv",
            },
        }

    try:
        with config_path.open("r", encoding="utf-8") as f:
            settings = json.load(f)
        LOGGER.info("Loaded settings from %s", config_path)
        return settings
    except json.JSONDecodeError as exc:
        LOGGER.error("Failed to parse settings file %s: %s", config_path, exc)
        raise SystemExit(1) from exc

def load_usernames(input_path: Optional[Path] = None) -> List[str]:
    if input_path is None:
        input_path = PROJECT_ROOT / "data" / "input_usernames.txt"

    if not input_path.exists():
        LOGGER.error("Input usernames file %s does not exist.", input_path)
        raise SystemExit(1)

    usernames: List[str] = []
    with input_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            usernames.append(line)

    if not usernames:
        LOGGER.error("No usernames found in %s.", input_path)
        raise SystemExit(1)

    LOGGER.info("Loaded %d usernames from %s", len(usernames), input_path)
    return usernames

def scrape_profiles(usernames: List[str], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    max_workers = int(settings.get("concurrent_requests", 4)) or 1
    LOGGER.info(
        "Starting scraping for %d profiles using up to %d workers.",
        len(usernames),
        max_workers,
    )

    results: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_username = {
            executor.submit(fetch_profile, username, settings): username
            for username in usernames
        }

        for future in as_completed(future_to_username):
            username = future_to_username[future]
            try:
                profile = future.result()
                if profile is None:
                    LOGGER.warning("No data returned for username '%s'.", username)
                    continue
                results.append(profile)
                LOGGER.info("Successfully scraped '%s'.", username)
            except Exception as exc:  # noqa: BLE001
                LOGGER.error("Failed to scrape '%s': %s", username, exc)

    LOGGER.info("Scraping completed. Successfully scraped %d/%d profiles.", len(results), len(usernames))
    return results

def main() -> None:
    setup_logging()
    LOGGER.info("Instagram Profile Scraper Pro starting.")

    try:
        settings = load_settings()
        usernames = load_usernames()
    except SystemExit:
        # Errors already logged; just exit.
        return

    profiles = scrape_profiles(usernames, settings)

    if not profiles:
        LOGGER.warning("No profiles were successfully scraped; nothing to export.")
        return

    output_settings = settings.get("output", {})
    json_rel = output_settings.get("json", "data/results.json")
    csv_rel = output_settings.get("csv", "data/results.csv")

    json_path = PROJECT_ROOT / json_rel
    csv_path = PROJECT_ROOT / csv_rel

    try:
        export_json(profiles, json_path)
        LOGGER.info("Exported JSON results to %s", json_path)
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("Failed to export JSON results: %s", exc)

    try:
        export_csv(profiles, csv_path)
        LOGGER.info("Exported CSV results to %s", csv_path)
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("Failed to export CSV results: %s", exc)

    LOGGER.info("Instagram Profile Scraper Pro finished.")

if __name__ == "__main__":
    main()