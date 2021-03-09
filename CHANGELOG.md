# Rolling Data Scramble Dashboard - Change log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

* [#81] Updating project dependencies

### Fixed

* [#82] Removed hard-coded `country-responses` CMF path to support operations in `prepared-country-data`

## [0.3.0] - 2021-03-08

### Changed [BREAKING!]

* [#70] Renamed package from `mapaction_rds_dashboard` to `mapy_rds_dashboard`
* [#50] Renamed `app_version` to `__version__` to follow convention and moved to base of new package
* [#51] `update-dashboard` Poetry script, replacing `app.py`/entrypoint.py` scripts

### Removed [BREAKING!]

* [#52] Removing `requirements.txt`

### Added

* [#50] local pre-commit hooks
* [#50] Testing and coverage support
* [#50] Linting and type checking tools
* [#50] Continuous Integration using GitHub Actions
* [#50] Continuous Deployment using GitHub Actions
* [#50] Python dependency security checking with `safety` package
* [#55] Pyenv support for local development environments
* [#69] PyPi packaging support

### Fixed

* [#75] Removing overly strict directory checks for Operation paths
* [#47] Inconsistent element ordering for dictionaries in Google Sheets exporter
* [#8] App version variable now sourced from package, rather than duplicated

### Changed

* [#50] Switching to `src/` package layout to define a project package

## [0.2.0] - 2021-02-20

### Added

* [#38] Support for using Google File Stream on Windows

### Changed

* [#45] Improving release procedures
* [#40] Downgrading to Python 3.7 (for compatibility with GoCD / ArcGIS Pro)
* [#39] Configuration options can now be set using environment variables

## [0.1.0] - 2021-02-19

### Added

* [#1] Initial application skeleton
* [#2] Processing step to gather files from Crash Move Folders into Operations, Map Products and Map Layers
* [#3] Processing step to parse and evaluate data from each Operation's Map Layers from MapChef output files
* [#20] Processing step to use Map Layer definitions where MapChef output files are unavailable
* [#4] Processing step to summarise the results for each Operation's Map Layers
* [#5] Processing step to structure results and summaries into an export format
* [#6] Processing step to publish results and summarises to a Google Spreadsheet
* [#19] Initial project documentation
