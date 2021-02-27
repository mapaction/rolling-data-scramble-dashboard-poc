# Rolling Data Scramble Dashboard

Proof of concept dashboard for the status of MapAction Rolling Data Scrambles.

[View Dashboard in Google Sheets](https://docs.google.com/spreadsheets/d/1MSXc-1mffyv_EtiXWvpu-cDc92UAutRkXVFV4ICILx8/).

## Purpose

To provide a concise overview of the status of each rolling data scramble, in terms of whether MapChef is happy with
each layer used in the *MA9999 All Layers* pseudo map product.

This project is part of the Data Pipeline MVP, see this [Jira Issue](https://mapaction.atlassian.net/browse/PMVP-59)
for further information.

## Status

This is a Proof of Concept / alpha application. Its availability or correctness it should not be replied upon.

## Usage

**Note:** Follow the steps in the [Setup](#setup) section first.

**Note**: This application uses a hard coded base path to shared drives, meaning it will only work on macOS (see #8).

```
$ cd rolling-data-scramble-dashboard-poc/
$ poetry run update-dashboard
```

This will:

* produce a local file `export.json`
* update this [Google Spreadsheet](https://docs.google.com/spreadsheets/d/1MSXc-1mffyv_EtiXWvpu-cDc92UAutRkXVFV4ICILx8/)

### Add a new operation/country

Once the Crash Move Folder for the relevant operation(s) has been created in Google Drive, the CMF / Operation ID needs
to be added to the `rds_operations_cmf_paths` [config](#application-configuration) option.

## Setup

You will need [Google Drive for Desktop](https://support.google.com/a/answer/7491144?hl=en) (Google File Stream)
installed with suitable permissions to access shared drives.

You will need to generate a
[Google OAuth credential](https://df2gspread.readthedocs.io/en/latest/overview.html#access-credentials) with
suitable permissions to update the Google Sheets export. Save this file as `./google-application-credentials.json`
relative to `entrypoint.py`.

```
$ brew install python
$ python3 -m pip install poetry
$ git clone https://github.com/mapaction/rolling-data-scramble-dashboard-poc.git
$ cd rolling-data-scramble-dashboard-poc/
$ poetry install --no-dev
```

### Support

As a proof of concept there isn't any formal support for this application. However if you're experimenting with it
and have a problem please contact @dsoares & @ffennell, or @asmith in the [#topic-rolling-data-scrambles]
(https://mapaction.slack.com/archives/C01DDCTAWG4) channel in the MapAction Slack.

## Implementation

### Application

To allow future integration into other parts of the Rolling Data Scramble and wider automation projects, this
project is written in Python.

The application for this project is written in Python as a set of classes and functions contained in a 
[`mapaction_rds_dashboard`](src/mapaction_rds_dashboard) package.

A `run()` method calls and passes data between the steps needed to:

1. for a set of operations, read their details from their Crash Move Folders
2. specifically, read the MapChef output about the layers in the 'MA9999' pseudo-product
3. if found, these layers are evaluated to see if they contain errors reported by MapChef
4. one or more [Exporters](#exporters) visualise these evaluations in different formats and services

This sequence of method calls is designed to allow each step to be run as part of a workflow for the Rolling Data
Scramble, and in wider automation projects.

The `update-dashboard` Poetry script is used to run this method.

#### Application configuration

Configuration options for this application are defined in the `config.py` module. This uses a typed dictionary to
define the options available. Descriptions of what each config option does, and default values used for each, are 
provided in this dictionary's description.

These default values can optionally be overridden using environment variables in the form: 
`APP_RDS_DASHBOARD_{CONFIG-OPTION}`.

**Note:** The `rds_operations_cmf_paths` config option cannot be overridden this way.

For example to override the `google_drive_base_path` config option to `/Foo`, set an environment variable:

```
APP_RDS_DASHBOARD_GOOGLE_DRIVE_BASE_PATH=/foo
```

See the notes in the `config.py` module for valid values for configuration options.

### Exporters

Exports are responsible for transforming a common [Export Format](#export-format) into a structure or configuration
specific to, and suitable for, a format or service.

This common export format is therefore intended as stable interface between how data/results are generated, and
how/where these results are visualised.

#### Export format

To make it easier for exporters to access results information in the form they expect (e.g. organised as a flat list of
results, or grouped by operation, or by layer, or result, etc.) a common export format is generated.

In brief, this export consists of a Python dict that can be easily serialised (e.g. to JSON). It has two top level
members:

* `data`, which contains information about:
  * affected countries from each operation
  * details of operations
  * results grouped by operation, layer and result
  * summary statistics (results for aggregated layers and totals for each result type)
* `meta`, which contains information about:
  * when a specific export instance was generated
  * the version of the export format used in that instance
  * the version of the application that generated that instance
  * labels that can be used to more nice format things like:
    * aggregated layers (e.g. 'tran' can be shown as 'Transport' )
    * evaluation results (e.g. 'PASS_WITH_WARNINGS' can be shown as 'Warning')

The structure and keys used in this export are guaranteed to stay the same within the same export format version.

If changes are made, a new format version will be added and a deprecation policy agreed for removing older versions.

#### JSON exporter

A very simple JSON exporter is included to:

* persist the [Export Format](#export-format) into a file suitable for re-use in other tools if needed
* demonstrate what a minimal exporter looks like

#### Google Sheets exporter

A more complex and useful exporter which uses a Panda's data frame as the source for a Google Docs spreadsheet.

Two dynamic tabs/sheets are included using results from the most recent run of the application:

* a summary of aggregated layers per operation
* details of each layer per operation

Additional, static, sheets are also created with the most recent run for each day.

## Development

### Development environment

A local Python virtual environment managed by [Poetry](https://python-poetry.org) is used for development.

```
$ brew install python
$ python3 -m pip install poetry
$ git clone https://github.com/mapaction/rolling-data-scramble-dashboard-poc.git
$ cd rolling-data-scramble-dashboard-poc/
$ poetry install
```

### Dependencies

Python dependencies are managed using [Poetry](https://python-poetry.org) which are recorded in `pyproject.toml`.

* use `poetry add` to add new dependencies (use `poetry add --dev` for development dependencies)
* use `poetry update` to update all dependencies to latest allowed versions

After changing dependencies, run `poetry export -f requirements.txt --output requirements.txt` to create a requirements
file. This will be resolved when this project is released as a package.

Ensure the `poetry.lock` file is included in the project repository.

### Code standards

Python code should follow PEP-8 and use the [Black](https://black.readthedocs.io) code formatter.

### Tests

All code should be covered by appropriate tests (unit, integration, etc.). Tests for this project are contained in the
[`tests`](/tests) directory and ran using [Pytest](https://docs.pytest.org/en/stable/):

```shell
$ poetry run pytest
```

#### Test coverage

Test coverage can be checked using [Coverage](https://coverage.readthedocs.io/):

```shell
$ poetry run pytest --cov
```

**Note:** Test coverage cannot measure the quality, or meaningfulness of any tests written, however it can identify 
code without any tests.

## Release procedure

For all releases:

1. create a release branch
2. bump the project version using [`poetry version`](https://python-poetry.org/docs/cli/#version)
3. update `__version__` variable in [`__init__.py`](src/mapaction_rds_dashboard/__init__.py) 
   (needed until project is distributed as a package)
4. close release in `CHANGELOG.md`
5. push changes and merge the release branch into `main`
6. create a tag and release through GitHub (tags should match the package version)

## Feedback

Feedback of any kind is welcome.

For feedback on how this application works, please raise an issue in this [GitHub
repository](https://github.com/mapaction/rolling-data-scramble-dashboard-poc).

For feedback on where this application sits in relation to other automation projects, please comment on the
[Jira issue](https://mapaction.atlassian.net/browse/PMVP-59) for this project.

## Licence

© MapAction, 2021.

[The MIT License](LICENSE)
