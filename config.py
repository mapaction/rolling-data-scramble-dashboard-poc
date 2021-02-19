from pathlib import Path
from typing import TypedDict, List


class Config(TypedDict):
    """
    Application configuration options

    These options do not change on a per-instance/environment basis, and with the exception of
    `rds_operations_cmf_paths`, are not designed to be modified (i.e. they are constants).

    == google_drive_base_path ==

    Description: Absolute path to the root of the Google Drive for Desktop (Google File Stream) drive.

    Value: Hardcoded to the default location used on Windows or macOS.

    == google_drive_operations_path ==

    Description: Relative path to the directory containing `rds_operations_cmf_paths`, relative to
                `google_drive_base_path`.

    Value: Hardcoded to conventional location.

    == rds_operations_cmf_paths ==

    Description: Relative paths to Crash Move Folders for each operation to be reported on by this application,
                 relative to `google_drive_operations_path`.

    Value: Varies based on current reporting needs.

    == all_products_product_id ==

    Description: Name of the map product who's layers should be evaluated for this dashboard.

    Value: MapChef Pseudo 'all layers' product.

    == export_path ==

    Description: Path to the exported file produced by the JSON exporter, relative to `app.py`.

    Value: conventional/arbitrary value.

    == google_service_credential_path ==

    Description: Path to the Google apps/auth credential file for the Google Sheets exporter, created when registering
                 a service principle (see README), relative to `app.py`.

    Value: conventional/arbitrary value.

    == google_service_credential_scopes ==

    Description: Google auth OAuth scopes used by the Google Sheets exporter, these scopes be granted to the service
                 principle set by `google_service_credential_path`.

    Value: Required scopes for Google Sheets exporter

    == google_sheets_key ==

    Description: Identifier of the spreadsheet used by the Google Sheets exporter.

    Value: Identifier to relevant spreadsheet

    == google_sheets_summary_sheet_name ==

    Description: Name for the summary/aggregated results sheet in the spreadsheet used by the Google Sheets exporter.

    Value: Conventional value

    == google_sheets_detail_sheet_name ==

    Description: Name for the detailed results sheet in the spreadsheet used by the Google Sheets exporter.

    Value: Conventional value

    """

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


def google_drive_base_path() -> Path:
    """
    Determine the root of the Google Drive based on the OS platform

    Supports Windows and macOS (which are the only platforms supported currently)

    :return: path to the root of the Google Drive
    """
    google_drive_base_path_windows = Path("G:")
    google_drive_base_path_macos = Path("/Volumes/GoogleDrive")

    if google_drive_base_path_windows.exists():
        return google_drive_base_path_windows

    if google_drive_base_path_macos.exists():
        return google_drive_base_path_macos

    raise FileNotFoundError


config: Config = dict()

config["google_drive_base_path"] = google_drive_base_path()

config["google_drive_operations_path"] = config["google_drive_base_path"].joinpath(
    "Shared drives/country-responses"
)

config["rds_operations_cmf_paths"] = [
    Path("2021-dom-001"),
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
