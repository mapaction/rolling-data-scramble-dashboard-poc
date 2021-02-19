# Rolling Data Scramble Dashboard - Change log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* [#38] Support for using Google File Stream on Windows 

### Changed

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
