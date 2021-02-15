from pathlib import Path
from typing import TypedDict, List


class Config(TypedDict):
    google_drive_base_path: Path
    google_drive_operations_path: Path
    rds_operations_cmf_paths: List[Path]
    all_products_product_id: str
    export_path: Path
    google_service_credential_path: Path
    google_service_credential_scopes: List[str]
    google_sheets_key: str
    google_sheets_summary_sheet_name: str
    google_sheets_detail_sheet_name: str


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

config["google_service_credential_path"] = Path("google-application-credentials.json")
config["google_service_credential_scopes"] = ["https://spreadsheets.google.com/feeds"]
config["google_sheets_key"] = "1MSXc-1mffyv_EtiXWvpu-cDc92UAutRkXVFV4ICILx8"
config["google_sheets_summary_sheet_name"] = "Summary"
config["google_sheets_detail_sheet_name"] = "All layers"
