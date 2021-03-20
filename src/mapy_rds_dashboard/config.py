import os
from pathlib import Path
from typing import List

from typing_extensions import TypedDict


class Config(TypedDict, total=False):
    """
    Application configuration options.

    All options have a default value which can optionally be overridden using environment variables.

    == google_drive_base_path ==

    Description: Absolute path to the root of the Google Drive for Desktop (Google File Stream) drive.

    Default value: Hardcoded to the default location used on Windows or macOS.

    Allowed value: Valid OS file path.

    == rds_operations_cmf_paths ==

    Description: Relative paths to Crash Move Folders for each operation to be reported on by this application,
                 relative to `google_drive_base_path`.

    Default value: Varies based on current reporting needs.

    Allowed value: List of valid OS file paths.

    == all_products_product_id ==

    Description: Name of the map product who's layers should be evaluated for this dashboard.

    Default value: MapChef Pseudo 'all layers' product.

    Allowed value: Valid OS file path representing a valid map product.

    == export_path ==

    Description: Path to the exported file produced by the JSON exporter, relative to `app.py`.

    Default value: Conventional/arbitrary value.

     Allowed value: Valid OS file path (will be overwritten on each run).

    == google_service_credential_path ==

    Description: Path to the Google apps/auth credential file for the Google Sheets exporter, created when registering
                 a service principle (see README), relative to `app.py`.

    Default value: Conventional/arbitrary value.

    Allowed value: Valid OS file to a Google service credential file.

    == google_service_credential_scopes ==

    Description: Google auth OAuth scopes used by the Google Sheets exporter, these scopes be granted to the service
                 principle set by `google_service_credential_path`. Expressed as a comma separated list (no spaces).

    Default value: Required scopes for Google Sheets exporter

    Allowed value: Valid

    == google_sheets_key ==

    Description: Identifier of the spreadsheet used by the Google Sheets exporter.

    Default value: Identifier to relevant spreadsheet

    Allowed value: Valid Google Sheets document ID

    == google_sheets_summary_sheet_name ==

    Description: Name for the summary/aggregated results sheet in the spreadsheet used by the Google Sheets exporter.

    Default value: Conventional value

    Allowed value: String

    == google_sheets_detail_sheet_name ==

    Description: Name for the detailed results sheet in the spreadsheet used by the Google Sheets exporter.

    Default value: Conventional value

    Allowed value: String

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
    Determine the root of the Google Drive based on the OS platform.

    Supports Windows and macOS (which are the only platforms supported currently)

    :raises FileNotFoundError: path to the root of the Google Drive does not exist
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

config["google_drive_base_path"] = Path(
    os.getenv(
        "APP_RDS_DASHBOARD_GOOGLE_DRIVE_BASE_PATH", default=google_drive_base_path()
    )
)

config["rds_operations_cmf_paths"] = [
    Path("Shared drives/prepared-country-data/bangladesh"),
    Path("Shared drives/prepared-country-data/cameroon"),
    Path("Shared drives/prepared-country-data/dominica"),
    Path("Shared drives/prepared-country-data/dominican-republic"),
    Path("Shared drives/prepared-country-data/fiji"),
    Path("Shared drives/prepared-country-data/guatemala"),
    Path("Shared drives/prepared-country-data/haiti"),
    Path("Shared drives/prepared-country-data/honduras"),
    Path("Shared drives/prepared-country-data/indonesia"),
    Path("Shared drives/prepared-country-data/kenya"),
    Path("Shared drives/prepared-country-data/malawi"),
    Path("Shared drives/prepared-country-data/mali"),
    Path("Shared drives/prepared-country-data/myanmar"),
    Path("Shared drives/prepared-country-data/nepal"),
    Path("Shared drives/prepared-country-data/pakistan"),
    Path("Shared drives/prepared-country-data/philippines"),
    Path("Shared drives/prepared-country-data/south-sudan"),
    Path("Shared drives/prepared-country-data/sri-lanka"),
    Path("Shared drives/prepared-country-data/vanuatu"),
    Path("Shared drives/country-responses/2021-moz-001"),
]

config["all_products_product_id"] = os.getenv(
    "APP_RDS_DASHBOARD_ALL_PRODUCTS_ID",
    default="MA9999",
)

config["export_path"] = Path(
    os.getenv(
        "APP_RDS_DASHBOARD_EXPORT_PATH",
        default="export.json",
    )
)

config["google_service_credential_path"] = Path(
    os.getenv(
        "APP_RDS_DASHBOARD_GOOGLE_SERVICE_CREDENTIAL_PATH",
        default="google-application-credentials.json",
    )
)

config["google_service_credential_scopes"] = str(
    os.getenv(
        "APP_RDS_DASHBOARD_GOOGLE_SERVICE_CREDENTIAL_SCOPES",
        default="https://spreadsheets.google.com/feeds",
    )
).split(",")

config["google_sheets_key"] = os.getenv(
    "APP_RDS_DASHBOARD_GOOGLE_SHEETS_KEY",
    default="1MSXc-1mffyv_EtiXWvpu-cDc92UAutRkXVFV4ICILx8",
)

config["google_sheets_summary_sheet_name"] = os.getenv(
    "APP_RDS_DASHBOARD_SUMMARY_SHEET_NAME",
    default="Summary",
)

config["google_sheets_detail_sheet_name"] = os.getenv(
    "APP_RDS_DASHBOARD_DETAIL_SHEET_NAME",
    default="All layers",
)
