from pathlib import Path
from typing import TypedDict, List


class Config(TypedDict):
    google_drive_base_path: Path
    google_drive_operations_path: Path
    rds_operations_cmf_paths: List[Path]
    all_products_product_id: str
    export_path: Path


config: Config = dict()

config["google_drive_base_path"] = Path("/Volumes/GoogleDrive")

config["google_drive_operations_path"] = config["google_drive_base_path"].joinpath(
    "Shared drives/country-responses"
)

config["rds_operations_cmf_paths"] = [
    Path("2021-bgd-001"),
    Path("2021-moz-001"),
    Path("rolling-data-scramble-south-sudan/2020ssd001"),
]

config["all_products_product_id"] = "MA9999"

config["export_path"] = Path("export.json")
