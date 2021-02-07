# Rolling Data Scramble Dashboard

Proof of concept dashboard for the status of MapAction Rolling Data Scrambles

## Purpose

To provide a concise overview of the status of each rolling data scramble, in terms of whether MapChef is happy with 
each layer used in the *MA9999 All Layers* pseudo map product.

This project is part of the Data Pipeline MVP, see this [Jira Issue](https://mapaction.atlassian.net/browse/PMVP-59) 
for further information.

## Status

This is a Proof of Concept / alpha application. Its availability or correctness it should not be replied upon.

## Usage

**Note:** Follow the steps in the [Setup](#setup) section first.

```
$ cd rolling-data-scramble-dashboard-poc/
$ python3 app.py
```

## Setup

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

To allow future integration into other parts of the Rolling Data Scramble and wider automation projects, this 
project is written in Python.


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

## Feedback

Feedback of any kind is welcome. 

For feedback on how this application works, please raise an issue in this [GitHub 
repository](https://github.com/mapaction/rolling-data-scramble-dashboard-poc). 

For feedback on where this application sits in relation to other automation projects, please comment on the 
[Jira issue](https://mapaction.atlassian.net/browse/PMVP-59) for this project.

## Licence

© MapAction, 2021.

[The MIT License](LICENSE)
