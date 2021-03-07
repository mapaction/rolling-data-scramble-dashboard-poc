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

```shell
$ python -m mapaction_rds_dashboard.app 
```

This will:

* produce a `export.json` file in the current directory (this can be ignored but is useful for debugging)
* update this [Google Spreadsheet](https://docs.google.com/spreadsheets/d/1MSXc-1mffyv_EtiXWvpu-cDc92UAutRkXVFV4ICILx8/)

### Adding a new operation/country

1. create the Crash Move Folder for the new operation
2. ensure the `operation_id` property is set in the CMF `event_description.json` file
3. add the name of the CMF directory to the `rds_operations_cmf_paths` [config](#application-configuration) option
4. update the dashboard

### Support

As a proof of concept, there isn't any formal support for this application. However if you're experimenting with it
and have a problem please contact @dsoares & @ffennell, or @asmith in the 
[#topic-rolling-data-scrambles](https://mapaction.slack.com/archives/C01DDCTAWG4) channel in the MapAction Slack.

## Setup

You will need [Google Drive for Desktop](https://support.google.com/a/answer/7491144?hl=en) (Google File Stream)
installed with suitable permissions to access shared drives.

You will need to generate a
[Google OAuth credential](https://df2gspread.readthedocs.io/en/latest/overview.html#access-credentials) with
suitable permissions to update the Google Sheets export. Save this credential as a file relative to where you run the
application, or, set an environment variable `APP_RDS_DASHBOARD_GOOGLE_SERVICE_CREDENTIAL_PATH` to its absolute path.

```shell
# install Python (min version 3.7.1)
$ python3 -m pip install mapaction-rds-dashboard
```

## Implementation

### Application

To allow future integration into other parts of the Rolling Data Scramble, and wider automation projects, the 
application for this project written in Python.

Classes and methods are contained in a package, [`mapaction_rds_dashboard`](src/mapaction_rds_dashboard).

In brief these classes and methods are used to:

1. for a set of operations, read their details from their Crash Move Folders
2. specifically, read the MapChef output about the layers in the 'MA9999' pseudo-product
3. if found, these layers are evaluated to see if they contain errors reported by MapChe
4. if not found (because MapChef hasn't run yet), layers from a definition file will be used and evaluated as failed
4. one or more [Exporters](#exporters) visualise these evaluations in different formats and services

These steps or tasks are intentionally split to allow for future integration into a workflow (such as Airflow).

### Python version

Python 3.7 is used for this project to ensure compatibility with ArcGIS' Python environment.

#### Application configuration

Configuration options for this application are defined in the `config.py` module. This uses a typed dictionary to
define the options available. Descriptions of what each config option does, and default values used for each, are 
provided in this dictionary's description.

These default values can optionally be overridden using environment variables in the form: 
`APP_RDS_DASHBOARD_{CONFIG-OPTION}`.

For example to override the `google_drive_base_path` config option to `/Foo`, set an environment variable:

```
APP_RDS_DASHBOARD_GOOGLE_DRIVE_BASE_PATH=/foo
```

**Note:** The `rds_operations_cmf_paths` config option cannot be overridden this way.

### Exporters

Exports are responsible for transforming the common [Export Format](#export-format) into a structure or configuration
specific to, and suitable for, a format or service.

#### Export format

To make it easier for exporters to access result information in the form they expect (e.g. organised as a flat list of
results, grouped by operation, by layer, or by result, etc.) a common export format is generated.

This format forms a stable interface between how data/results are generated, and how/where these results are visualised.

In brief, this format is a Python dict that can be easily serialised (e.g. to JSON). It has two top level members:

1. `data`, which contains information about:
    * affected countries from each operation
    * details of operations
    * results grouped by operation, layer and result
    * summary statistics (results for aggregated layers and totals for each result type)
2. `meta`, which contains information about:
    * when a specific export instance was generated
    * the version of the export format used in that instance
    * the version of the application that generated that instance
    * labels that can be used to more nice format things like:
        * aggregated layers (e.g. 'tran' can be shown as 'Transport' )
        * evaluation results (e.g. 'PASS_WITH_WARNINGS' can be shown as 'Warning')

#### Export format versions

The structure and keys used in this export format are guaranteed to stay the same within each version. Any new versions 
will include a deprecation policy for removing older versions.

Version 1 is the current export format version.

#### JSON exporter

A very simple JSON exporter is included to:

* persist the [Export Format](#export-format) into a file suitable for re-use in other tools if needed
* demonstrate what a minimal exporter looks like
* assist with debugging

#### Google Sheets exporter

A more complex and useful exporter, which uses a Panda's data frame as the source for a 
[Google Docs spreadsheet](https://docs.google.com/spreadsheets/d/1MSXc-1mffyv_EtiXWvpu-cDc92UAutRkXVFV4ICILx8/).

Tabs/sheets are included for:

1. aggregated layers per operation
2. details of each layer per operation
3. static sheets for the most recent run for each day

## Development

### Development environment

A local Python virtual environment managed by [Poetry](https://python-poetry.org) is used for development.

```shell
# install pyenv as per https://github.com/pyenv/pyenv#installation and/or install Python 3.7.x
# install Poetry as per https://python-poetry.org/docs/#installation
# install pre-commit as per https://pre-commit.com/
$ git clone https://github.com/mapaction/rolling-data-scramble-dashboard-poc.git
$ cd rolling-data-scramble-dashboard-poc/
$ poetry install
```

**Note:** Use the correct [Python Version](#python-version) for this project.

**Note:** To ensure the correct Python version is used, install Poetry using it's installer, not as a Pip package.

### Dependencies

Python dependencies are managed using [Poetry](https://python-poetry.org) which are recorded in `pyproject.toml`.

* use `poetry add` to add new dependencies (use `poetry add --dev` for development dependencies)
* use `poetry update` to update all dependencies to latest allowed versions

Ensure the `poetry.lock` file is included in the project repository.

Dependencies will be checked for vulnerabilities using [Safety](https://pyup.io/safety/) automatically in 
[Continuous Integration](#continuous-integration). Dependencies can also be checked manually:

```shell
$ poetry export --dev --format=requirements.txt --without-hashes | safety check --stdin
```

### Code standards

All files should exclude trailing whitespace and include an empty final line.

Python code should be linted using [Flake8](https://flake8.pycqa.org/en/latest/):

```shell
$ poetry run flake8 src tests
```

This will check various aspects including:

* type annotations (except tests)
* doc blocks (pep257 style)
* consistent import ordering
* code formatting (against Black)
* estimated code complexity
* python anti-patterns
* possibly insecure code (this targets long hanging fruit only)

Python code should follow PEP-8 (except line length), using the [Black](https://black.readthedocs.io) code formatter:

```shell
$ poetry run black src tests
```

Python code (except tests) should use static type hints, validated using the [MyPy](https://mypy.readthedocs.io) and 
[TypeGuard](https://typeguard.readthedocs.io) type checkers:

```shell
$ poetry run mypy src
$ poetry run pytest --typeguard-packages mapaction_rds_dashboard
```

These conventions and standards are enforced automatically using a combination of:

* local Git [pre-commit hooks](https://pre-commit.com/) hooks/scripts (Flake8 checks only)
* remote [Continuous Integration](#continuous-integration) (all checks)

### Tests

All code should be covered by appropriate tests (unit, integration, etc.). Tests for this project are contained in the
[`tests`](/tests) directory and ran using [Pytest](https://docs.pytest.org/en/stable/):

```shell
$ poetry run pytest
```

These tests are ran automatically in [Continuous Integration](#continuous-integration).

#### Test coverage

Test coverage can be checked using [Coverage](https://coverage.readthedocs.io/):

```shell
$ poetry run pytest --cov
```

**Note:** Test coverage cannot measure the quality, or meaningfulness of any tests written, however it can identify 
code without any tests.

### Continuous Integration

GitHub Actions are used to perform Continuous Integration tasks as defined in [`.github/workflows`](/.github/workflows).

CI tasks are performed on both Linux and Windows platforms to ensure per-platform compatibility.

## Deployment

This project is distributed as a Python package, available through 
[PyPi](https://pypi.org/project/...) and installable through Pip.

Both source and binary (Python wheel) packages are built during [Continuous Deployment](#continuous-deployment). 

**Note:** These packages are pure Python and compatible with all operating systems.

To build and publish packages manually:

```shell
$ poetry build
$ poetry publish --repository testpypi 
```

**Note:** You will need a PyPi registry API token to publish packages, set with `poetry config pypi-token.testpypi xxx`.

### Continuous Deployment

GitHub Actions are used to perform Continuous Deployment tasks as defined in [`.github/workflows`](/.github/workflows).

## Release procedure

For all releases:

1. create a release branch
2. bump the project version using [`poetry version`](https://python-poetry.org/docs/cli/#version)
3. close release in `CHANGELOG.md`
4. push changes and merge the release branch into `main`
5. create a tag and release through GitHub:
   * tags should match the package version
   * new tags will trigger [Continuous Deployment](#continuous-deployment)
   * attach the packages Continuous Deployment creates as assets in the release

## Feedback

Feedback of any kind is welcome.

For feedback on how this application works, please raise an issue in this [GitHub
repository](https://github.com/mapaction/rolling-data-scramble-dashboard-poc).

For feedback on the wider context of this project, please comment on this
[Jira issue](https://mapaction.atlassian.net/browse/PMVP-59).

## Licence

© MapAction, 2021.

[The MIT License](LICENSE)
