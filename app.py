import logging
import sys
import json

from pathlib import Path
from typing import List, Dict

from pycountry import countries

from config import Config, config as app_config


class OperationInvalid(Exception):
    """
    Indicates an operation is invalid (for any reason)

    Currently this is a generic catch-all class, in future sub-classes could be added for specific circumstances.
    """

    pass


class Operation:
    """
    Represents an operational response

    In abstract terms, this class represents an activation for a given country (an operation).
    In concrete terms, this class represents properties of a Crash Move Folder (CMF) for a given activation.

    This class is currently minimal, with properties and methods needed for the Rolling Data Scramble dashboard.
    It's very likely there's a better way to do this, see [#13] for discussion. With the exception of the root to the
    Crash Move Folder, all class instance properties are loaded dynamically from the `event_description.json` or
    `cmf_description.json` configuration files.

    """

    def __init__(self, base_path: Path):
        """
        Loads operation properties from description files and performs minimal validation

        Validation is currently limited to whether the operation id is not an empty string. This is intended to prevent
        an unconfigured CMF being processed, as this will lead to errors later on.

        @todo: find a better of determining whether a CMF has not been configured [#9]

        :type base_path: Path
        :param base_path: path to the root of the Crash Move Folder representing the operation
        """
        self.base_path: Path = base_path
        self.event_description_path: Path = self.base_path.joinpath(
            "event_description.json"
        )
        self.crash_move_folder_description_path: Path = self.base_path.joinpath(
            Path(
                self._get_description_property(
                    description_path=self.event_description_path,
                    description_property="cmf_descriptor_path",
                )
            )
        )

        self.operation_id = self._get_description_property(
            description_path=self.event_description_path,
            description_property="operation_id",
        )
        self.operation_name = self._get_description_property(
            description_path=self.event_description_path,
            description_property="operation_name",
        )
        self.affected_country = countries.get(
            alpha_3=self._get_description_property(
                description_path=self.event_description_path,
                description_property="affected_country_iso3",
            )
        )

        if len(self.operation_id) == 0:
            raise OperationInvalid

    def __repr__(self) -> str:
        return f"<Operation id={self.operation_id}>"

    @staticmethod
    def _get_description_property(
        description_path: Path, description_property: str
    ) -> str:
        """
        Gets a property from the `event_description.json` or `cmf_description.json` configuration file

        @todo: error handling (invalid JSON decode, file does not exist, etc.) [#14]

        :type description_path: Path
        :param description_path: path to the event or CMF description file
        :type description_property: str
        :param description_property: key of the property to get
        :rtype str
        :return: value of the property to get
        """
        with open(description_path, mode="r") as description_file:
            description_data: Dict[str, str] = json.load(fp=description_file)
            return description_data[description_property]


def parse_operations(config: Config) -> List[Operation]:
    """
    Processes the configured list of operation IDs into a list of valid Operation class instances

    Minimal validation of each operation is performed, namely:
     - does the path to the operation/CMF exist?
     - can the operation/CMF be instantiated as an Operation class instance

    Basic validation
    :param config:
    :return:
    """
    operations: List[Operation] = list()

    for operation_path in config["rds_operations_cmf_paths"]:
        operation_path: Path = config["google_drive_base_path"].joinpath(
            config["google_drive_operations_path"], operation_path
        )
        try:
            operation_path.resolve(strict=True)
            operations.append(Operation(base_path=operation_path))
        except FileNotFoundError:
            logging.warning(
                f"Operation path '{operation_path}' does not appear to exist, ignoring operation."
            )
        except OperationInvalid:
            logging.warning(
                f"Operation path '{operation_path}' does not appear to be valid, ignoring operation."
            )

    return operations


def run() -> None:
    """
    Simple method to call functions and configure the application
    """
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    operations = parse_operations(config=app_config)

    # debug
    print(operations)


if __name__ == "__main__":
    run()
