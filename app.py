import logging
import sys
import json
from datetime import datetime
from enum import Enum, auto

from pathlib import Path
from typing import List, Dict, Optional

from pycountry import countries

from config import Config, config as app_config
from app_rich import (
    columns1,
    columns2,
    tree1,
    table1,
    progress1,
    progress2,
    progress3,
    table_progress1,
    table2,
    table3,
)

# @todo: read from future package / pyproject.toml
app_version = "0.1.0"


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


class EvaluationResult(Enum):
    """
    An enumeration of possible states for the result for an Evaluation

    Includes 'resolved' states, where an Evaluation successfully took place (e.g. pass, fail, etc.) and 'unresolved'
    states, where an Evaluation could not, or has not, taken place (e.g. because it hasn't happened yet, or an error
    occurred in the evaluation logic itself).

    Integer values for these these enumerated states are assigned automatically using the `auto()` method. The first
    state will `0`, the second `1` etc. This means the order statues are defined in matters.

    In this case, statues should be ordered from least to most significant (i.e. an Evaluation that fails is said to be
    more significant than one that has passed). This is to support situations where evaluations may examine multiple
    factors, which when taken together, should be based on the most significant evaluation.

    E.g. If an evaluation has three factors, the first a PASS, the second, a FAIL and the third a PASS, the FAIL
    evaluation should be used as the overall evaluation because it's the most significant.

    By assigning a higher numerical value to more significant statuses, we can use logical comparisons in a for loop to
    check if the current evaluation status is more or less significant than the most significant previous status. This
    logic is probably easiest to understand in context rather than as a verbose description.
    """

    NOT_EVALUATED = auto()
    PASS = auto()
    PASS_WITH_WARNINGS = auto()
    FAIL = auto()
    ERROR = auto()


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
        if not self.base_path.is_dir():
            raise MapProductInvalid

        self.map_chef_description_path: Optional[
            Path
        ] = self._get_latest_map_chef_description_path()
        if self.map_chef_description_path is None:
            raise MapProductInvalid

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

    def __repr__(self) -> str:
        return f"<MapProduct id={self.product_id}>"

    def _get_latest_map_chef_description_path(self) -> Optional[Path]:
        """
        Determines the MapChef description/output file for the latest product iteration

        Thankfully, because the naming convention used for these files is consistent we can rely on Python's built in
        `max()` method to determine the 'highest' value for a list of file names.

        These file names are determined by PathLib's `glob()` method, which returns a generator of values and therefore
        needs casting to a list for `max()` to work.

        Where there isn't a matching file (in cases where MapChef hasn't yet completed an iteration successfully for
        example) None is returned.

        :rtype Path or None
        :return: path to the latest MapChef description file or None
        """
        try:
            return max(list(self.base_path.glob("*.json")))
        except ValueError:
            return None

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
        if len(self.operation_id) == 0:
            raise OperationInvalid

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
        try:
            map_product_path: Path = self.map_products_path.joinpath(map_product_id)
            return MapProduct(base_path=map_product_path)
        except MapProductInvalid:
            raise OperationInvalid

    def export(self) -> Dict[str, str]:
        return {
            "affected_country_iso3": self.affected_country.alpha_3,
            "affected_country_name": self.affected_country.name,
            "id": self.operation_id,
            "name": self.operation_name,
        }


class Evaluation:
    """
    Represents the status of a layer for a operation

    I.e. the cells in the dashboard.

    Evaluations are effectively key value pairs, where the key is a composite of an operation and a layer, and the
    value is whether that layer for that operation has any errors reported by MapChef.

    Evaluations are stateful, in that evaluations are initially unevaluated then later evaluated by calling the
    `evaluate()` method.

    The `error_mapping` dict is used to determine which result to use for each error, the most severe of which will
    be the overall evaluation result.
    """

    error_mapping: Dict[MapChefError, EvaluationResult] = {
        MapChefError.LAYER_DATASOURCE_NONE: EvaluationResult.FAIL,
        MapChefError.LAYER_DATASOURCE_MULTIPLE: EvaluationResult.PASS_WITH_WARNINGS,
        MapChefError.LAYER_SCHEMA_INVALID: EvaluationResult.PASS_WITH_WARNINGS,
    }

    def __init__(self, operation_id: str, layer: MapLayer):
        """
        :type operation_id: str
        :param operation_id: operation ID
        :type layer: MapLayer
        :param layer: layer
        """
        self.operation_id: str = operation_id
        self.layer: MapLayer = layer

        self.result: EvaluationResult = EvaluationResult.NOT_EVALUATED

    def __repr__(self) -> str:
        return f"<Evaluation operation_id={self.operation_id} layer_id={self.layer.layer_id} result={self.result.name}>"

    def evaluate(self) -> None:
        """
        Evaluates a layer by checking whether it has any errors

        If not, the layer is considered to pass.

        Otherwise each error is mapped to a result ('pass with warnings' or fail) based on the error mapping. This
        result is then checked to see whether it is more significant than other results (i.e. more severe). See the
        notes in the EvaluationResult class for more information.
        """
        if len(self.layer.errors) == 0:
            self.result = EvaluationResult.PASS

        for error in self.layer.errors:
            result = self.error_mapping[error]
            if result.value > self.result.value:
                self.result = result


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

    Operations that do not include the relevant map product are not included as keys in the returned dict. Operations
    without this product should be considered invalid and filtered out using the `filter_valid_operations` method [#20].

    :type config: Config
    :param config: application configuration
    :type operations: List[Operation]
    :param operations: operations to get layers for
    :rtype Dict[str, List[MapLayer]]
    :return: layers grouped by Operation ID
    """
    layers: Dict[str, List[MapLayer]] = dict()

    for operation in operations:
        try:
            layers[operation.operation_id] = operation.get_map_product(
                map_product_id=config["all_products_product_id"]
            ).layers
        except OperationInvalid:
            logging.warning(
                f"Operation ID '{operation.operation_id}' does not appear to be valid, ignoring operation."
            )

    return layers


def filter_valid_operations(
    operations: List[Operation], operation_layers: Dict[str, List[MapLayer]]
) -> List[Operation]:
    """
    Filters a set of Operations to only return those with MapLayers from the 'all layers' MapProduct

    Operations without MapLayers are considered invalid (because they can't be evaluated), however as operations aren't
    related to their layers [#16], it's not possible to determine valid operations by themselves.

    This method checks to see if an operation has corresponding layers, those that don't are not returned. This is
    considered a workaround for [#20] and isn't ideal.

    :type operations: List[Operation]
    :param operations: operations to filter
    :type operation_layers: Dict[str, List[MapLayer]]
    :return: layers grouped by Operation ID
    :rtype operations: List[Operation]
    :return: filtered operations
    """
    valid_operations: List[Operation] = list()
    for operation in operations:
        if operation.operation_id in operation_layers.keys():
            valid_operations.append(operation)

    return valid_operations


def generate_evaluations(
    operation_layers: Dict[str, List[MapLayer]]
) -> List[Evaluation]:
    """
    Initialises Evaluations for a set of Operations and MapLayers

    As MapLayers are not linked to their operations [#16], this method uses additional context to set this for each
    operation:layer composite.

    Note: this method only initialises evaluations, rather than perform them.

    :type operation_layers: Dict[str, List[MapLayer]]
    :param operation_layers: layers grouped by Operation ID
    :rtype List[Evaluation]
    :return: initialised evaluations
    """
    evaluations: List[Evaluation] = list()

    for operation_id, operation_layers in operation_layers.items():
        for operation_layer in operation_layers:
            evaluations.append(
                Evaluation(operation_id=operation_id, layer=operation_layer)
            )

    return evaluations


def process_evaluations(evaluations: List[Evaluation]) -> None:
    """
    :type evaluations: List[Evaluation]
    :param evaluations: evaluations to process
    """
    for evaluation in evaluations:
        evaluation.evaluate()


def generate_export(evaluations: List[Evaluation], operations: List[Operation]) -> dict:
    """
    WIP - Structures data results of evaluations for use in an export

    The intention of this method is to structure information in a way that makes it easy to use in reporting tools
    (i.e. exports), as a result there is lots f duplication and simplification of data types for example.

    Note: The structure and contents of this data have not yet been discussed or agreed.

    :type evaluations: List[Evaluation]
    :param evaluations: list of evaluations
    :type operations: List[Operation]
    :param operations: list of operations
    :rtype dict
    :return: processes data ready for use in exports
    """
    export_version: int = 1

    _operations = []
    for operation in operations:
        _operations.append(operation.export())

    _results_by_operation: Dict[str, dict] = dict()
    _results_by_layer: Dict[str, dict] = dict()
    _results_by_result: Dict[str, List[Dict[str, str]]] = {
        EvaluationResult.NOT_EVALUATED.name: [],
        EvaluationResult.PASS.name: [],
        EvaluationResult.PASS_WITH_WARNINGS.name: [],
        EvaluationResult.FAIL.name: [],
        EvaluationResult.ERROR.name: [],
    }
    _ungrouped_results: List[Dict[str, str]] = list()
    for evaluation in evaluations:
        if evaluation.operation_id not in _results_by_operation.keys():
            _results_by_operation[evaluation.operation_id]: Dict[str, str] = dict()
        _results_by_operation[evaluation.operation_id][
            evaluation.layer.layer_id
        ] = evaluation.result.name

        if evaluation.layer.layer_id not in _results_by_layer.keys():
            _results_by_layer[evaluation.layer.layer_id]: Dict[str, str] = dict()
        _results_by_layer[evaluation.layer.layer_id][
            evaluation.operation_id
        ] = evaluation.result.name

        _results_by_result[evaluation.result.name].append(
            {
                "operation_id": evaluation.operation_id,
                "layer_id": evaluation.layer.layer_id,
            }
        )

        _ungrouped_results.append(
            {
                "operation_id": evaluation.operation_id,
                "layer_id": evaluation.layer.layer_id,
                "result": evaluation.result.name,
            }
        )

    _summary_statistics: Dict[str, dict] = dict()
    _summary_statistics["results"]: Dict[str, int] = {
        EvaluationResult.NOT_EVALUATED.name: len(
            _results_by_result[EvaluationResult.NOT_EVALUATED.name]
        ),
        EvaluationResult.PASS.name: len(_results_by_result[EvaluationResult.PASS.name]),
        EvaluationResult.PASS_WITH_WARNINGS.name: len(
            _results_by_result[EvaluationResult.PASS_WITH_WARNINGS.name]
        ),
        EvaluationResult.FAIL.name: len(_results_by_result[EvaluationResult.FAIL.name]),
        EvaluationResult.ERROR.name: len(
            _results_by_result[EvaluationResult.ERROR.name]
        ),
    }

    return {
        "meta": {
            "app_version": app_version,
            "export_version": export_version,
            "export_datetime": datetime.utcnow().isoformat(timespec="milliseconds"),
        },
        "data": {
            "operations": _operations,
            "results_by_operation": _results_by_operation,
            "results_by_layer": _results_by_layer,
            "results_by_result": _results_by_result,
            "ungrouped_results": _ungrouped_results,
            "summary_statistics": _summary_statistics,
        },
    }


def export_json(export_data: dict, export_path: Path) -> None:
    """
    WIP - JSON exporter

    Minimal example of an exporter.

    :type export_data: dict
    :param export_data: data generated by `generate_export()`
    :type export_path: Path
    :param export_path: path to destination export
    """
    with open(export_path, mode="w") as export_file:
        json.dump(obj=export_data, fp=export_file, indent=4, sort_keys=True)


def export_rich(export_data: dict) -> None:
    """
    Exp - Rich exporter

    Experimental terminal exporter

    :type export_data: dict
    :param export_data: data generated by `generate_export()`
    """
    columns1(export_data=export_data)
    print("")
    print("")
    columns2(export_data=export_data)
    print("")
    print("")
    tree1(export_data=export_data)
    print("")
    print("")
    table1(export_data=export_data)
    print("")
    print("")
    table2(export_data=export_data)
    print("")
    print("")
    table3(export_data=export_data)
    print("")
    print("")
    progress1(export_data=export_data)
    print("")
    print("")
    progress2(export_data=export_data)
    print("")
    print("")
    progress3(export_data=export_data)
    print("")
    print("")
    table_progress1(export_data=export_data)


def run() -> None:
    """
    Simple method to call functions and configure the application
    """
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    operations = parse_operations(config=app_config)
    operation_layers = parse_operation_layers(config=app_config, operations=operations)
    operations = filter_valid_operations(
        operations=operations, operation_layers=operation_layers
    )
    evaluations = generate_evaluations(operation_layers=operation_layers)
    process_evaluations(evaluations=evaluations)
    export_data = generate_export(evaluations=evaluations, operations=operations)
    export_json(export_data=export_data, export_path=app_config["export_path"])
    export_rich(export_data=export_data)


if __name__ == "__main__":
    run()
