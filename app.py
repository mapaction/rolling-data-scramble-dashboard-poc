import logging
import sys
import json
from enum import Enum, auto

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


class MapProductInvalid(Exception):
    """
    Indicates a map product is invalid (for any reason)

    Currently this is a generic catch-all class, in future sub-classes could be added for specific circumstances.
    """

    pass


class MapChefError(Enum):
    """
    An enumeration of possible error conditions reported by MapChef

    Errors are matched against the human readable error MapChef includes in layer output files.

    @todo: is this list complete? [#10]
    """

    LAYER_DATASOURCE_NONE = "Unable to find dataset for this layer"
    LAYER_DATASOURCE_MULTIPLE = "Found multiple datasets which match this layer"
    LAYER_SCHEMA_INVALID = "Data schema check failed"


class MapLayer:
    """
    Represents a layer with a Map Product

    For the purposes of the Rolling Data Scramble dashboard, layers represent the units that are evaluated.

    Note: this class does NOT directly represent cells in the dashboard, they are Evaluations, which effectively wrap
    around MapLayers with additional context.

    As with other classes, only methods and properties required for the Rolling Data Scramble dashboard are included.
    """

    def __init__(self, layer_id: str, error_messages: List[str]):
        """
        Loads layer properties parses MapChef error messages

        :type layer_id: str
        :param layer_id: layer ID
        :type error_messages: List[str]
        :param error_messages: MapChef error messages
        """
        self.layer_id: str = layer_id

        self.errors: List[MapChefError] = self._parse_error_messages(
            error_messages=error_messages
        )

    def __repr__(self) -> str:
        return f"<MapLayer id={self.layer_id}>"

    @staticmethod
    def _parse_error_messages(error_messages: List[str]) -> List[MapChefError]:
        """
        Matches MapChef Errors against the MapChefErrors enumeration

        For ease of reference when analysing and reporting errors.

        :type error_messages: List[str]
        :param error_messages: MapChef error messages
        :rtype: List[MapChefErrors]
        :return: MapChefError items corresponding to MapChef error messages
        """
        errors: List[MapChefError] = list()

        for error_message in error_messages:
            errors.append(MapChefError(error_message))

        return errors


class MapProduct:
    """
    Represents a product within a Map

    For the purposes of the Rolling Data Scramble dashboard, products represent the whole that is being evaluated. I.e.
    represents, and defines, the columns in the dashboard.

    Specifically, Products are based on the machine readable MapChef output/report files for each product. These output
    files are specific to each a MapChef run, meaning the state of a product can vary over time/iterations. Currently
    this is ignored and only the state of the latest iteration is considered.

    As with other classes, only methods and properties required for the Rolling Data Scramble dashboard are included.
    """

    def __init__(self, base_path: Path):
        """
        Loads product, and product iteration, properties from MapChef output files

        Limitations:
        * only the most recent product iteration is considered
        * only the primary data frame in a product iteration is considered

        :type base_path: Path
        :param base_path: path to the root of the folder representing this product within a Crash Move Folder
        """
        self.base_path: Path = base_path
        self.map_chef_description_path: Path = (
            self._get_latest_map_chef_description_path()
        )

        self.product_id: str = self._get_map_chef_description_property(
            description_property="mapnumber"
        )
        self.product_name: str = self._get_map_chef_description_property(
            description_property="product"
        )
        self.version: int = int(
            self._get_map_chef_description_property(description_property="version_num")
        )

        self.layers: List[MapLayer] = self._get_map_chef_primary_layers()

        if not self.base_path.is_dir():
            raise MapProductInvalid

    def __repr__(self) -> str:
        return f"<MapProduct id={self.product_id}>"

    def _get_latest_map_chef_description_path(self) -> Path:
        """
        Determines the MapChef description/output file for the latest product iteration

        Thankfully, because the naming convention used for these files is consistent we can rely on Python's built in
        `max()` method to determine the 'highest' value for a list of file names.

        These file names are determined by PathLib's `glob()` method, which returns a generator of values and therefore
        needs casting to a list for `max()` to work.

        :rtype Path
        :return: path to the latest MapChef description file
        """
        return max(list(self.base_path.glob("*.json")))

    def _get_map_chef_description_property(self, description_property: str) -> str:
        """
        Gets a property from MapChef description/output file

        @todo: error handling (invalid JSON decode, file does not exist, etc.) [#14]

        :type description_property: str
        :param description_property: key of the property to get
        :rtype str
        :return: value of the property to get
        """
        with open(self.map_chef_description_path, mode="r") as description_file:
            description_data: Dict[str, str] = json.load(fp=description_file)
            return description_data[description_property]

    def _get_map_chef_primary_layers(self) -> List[MapLayer]:
        """
        Gets layer information from the primary map frame in the MapChef description/output file

        Note: This method is not ideal in terms of duplicating code for reading the description file contents. See
        https://github.com/mapaction/rolling-data-scramble-dashboard-poc/issues/13#issuecomment-776567511.

        :rtype List[MapLayer]
        :return: layers in the primary map frame
        """
        with open(self.map_chef_description_path, mode="r") as description_file:
            description_data: dict = json.load(fp=description_file)
            primary_data_frame_id: str = description_data["principal_map_frame"]
            primary_data_frame: dict = dict()

            for map_frame in description_data["map_frames"]:
                if map_frame["name"] == primary_data_frame_id:
                    primary_data_frame = map_frame
                    break

            layers: List[MapLayer] = list()
            for layer in primary_data_frame["layers"]:
                layers.append(
                    MapLayer(
                        layer_id=layer["name"], error_messages=layer["error_messages"]
                    )
                )

            return layers


class Operation:
    """
    Represents an operational response

    In abstract terms, this class represents an activation for a given country (an operation).
    In concrete terms, this class represents properties of a Crash Move Folder (CMF) for a given activation.

    For the purposes of the Rolling Data Scramble dashboard, operations represent the rows in the dashboard.

    With the exception of the root to the Crash Move Folder, all class instance properties are loaded dynamically from
    the `event_description.json` or `cmf_description.json` configuration files.

    As with other classes, only methods and properties required for the Rolling Data Scramble dashboard are included.
    It's very likely there's a better way to do this, see [#13] for discussion.
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
        self.map_products_path: Path = self.base_path.joinpath(
            Path(
                self._get_description_property(
                    description_path=self.crash_move_folder_description_path,
                    description_property="map_projects",
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

    def get_map_product(self, map_product_id: str) -> MapProduct:
        map_product_path: Path = self.map_products_path.joinpath(map_product_id)
        return MapProduct(base_path=map_product_path)


def parse_operations(config: Config) -> List[Operation]:
    """
    Processes Operations for a set of operation IDs

    Minimal validation of each operation is performed, namely:
     - does the path to the operation/CMF exist?
     - can the operation/CMF be instantiated as an Operation class instance

    :type config: Config
    :param config: application configuration
    :rtype List[Operation]
    :return: parsed, valid, operations
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


def parse_operation_layers(
    config: Config, operations: List[Operation]
) -> Dict[str, List[MapLayer]]:
    """
    Processes MapLayers from the 'all layers' MapProduct, for and grouped by, a set of Operations

    MapLayers are returned in a list per Operation so that an association between a layer and it's operation can be
    inferred elsewhere as this can't be set within objects currently [#16].

    :type config: Config
    :param config: application configuration
    :type operations: List[Operation]
    :param operations: operations to get layers for
    :rtype Dict[str, List[MapLayer]]
    :return: layers grouped by Operation ID
    """
    layers: Dict[str, List[MapLayer]] = dict()

    for operation in operations:
        layers[operation.operation_id] = operation.get_map_product(
            map_product_id=config["all_products_product_id"]
        ).layers

    return layers


def run() -> None:
    """
    Simple method to call functions and configure the application
    """
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    operations = parse_operations(config=app_config)
    operation_layers = parse_operation_layers(operations=operations)

    # debug
    print(operations)


if __name__ == "__main__":
    run()
