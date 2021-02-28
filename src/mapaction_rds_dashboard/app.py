from collections import OrderedDict
from datetime import datetime
from enum import auto, Enum
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from df2gspread import df2gspread as d2g
from oauth2client import service_account
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from pycountry import countries

from mapaction_rds_dashboard import __version__
from mapaction_rds_dashboard.config import Config, config as app_config


class OperationInvalid(Exception):
    """
    Indicates an operation is invalid (for any reason).

    Currently this is a generic catch-all class, in future sub-classes could be added for specific circumstances.
    """

    pass


class MapProductInvalid(Exception):
    """
    Indicates a map product is invalid (for any reason).

    Currently this is a generic catch-all class, in future sub-classes could be added for specific circumstances.
    """

    pass


class EvaluationResult(Enum):
    """
    An enumeration of possible states for the result for an Evaluation.

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
    An enumeration of possible error conditions reported by MapChef.

    Errors are matched against the human readable error MapChef includes in layer output files.

    @todo: is this list complete? [#10]
    """

    LAYER_DATASOURCE_NONE = "Unable to find dataset for this layer"
    LAYER_DATASOURCE_MULTIPLE = "Found multiple datasets which match this layer"
    LAYER_SCHEMA_INVALID = "Data schema check failed"
    MAPCHEF_OUTPUT_MISSING = "MAPCHEF_OUTPUT_MISSING"


class MapLayer:
    """
    Represents a layer with a Map Product.

    For the purposes of the Rolling Data Scramble dashboard, layers represent the units that are evaluated.

    Note: this class does NOT directly represent cells in the dashboard, they are Evaluations, which effectively wrap
    around MapLayers with additional context.

    As with other classes, only methods and properties required for the Rolling Data Scramble dashboard are included.
    """

    def __init__(self, layer_id: str, error_messages: List[str]) -> None:
        """
        Load layer properties and parse MapChef error messages.

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
        Match MapChef Errors against the MapChefErrors enumeration.

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
    Represents a product within a Map.

    For the purposes of the Rolling Data Scramble dashboard, products represent the whole that is being evaluated. I.e.
    represents, and defines, the columns in the dashboard.

    Specifically, Products are based on the machine readable MapChef output/report files for each product. These output
    files are specific to each a MapChef run, meaning the state of a product can vary over time/iterations. Currently
    this is ignored and only the state of the latest iteration is considered.

    As with other classes, only methods and properties required for the Rolling Data Scramble dashboard are included.
    """

    def __init__(self, base_path: Path) -> None:
        """
        Load product, and product iteration, properties from MapChef output files.

        Limitations:
        * only the most recent product iteration is considered
        * only the primary data frame in a product iteration is considered

        :raises MapProductInvalid: If the path to map product does not existing it is considered invalid.

        :type base_path: Path
        :param base_path: path to the root of the folder representing this product within a Crash Move Folder
        """
        self.base_path: Path = base_path
        if not self.base_path.is_dir():
            raise MapProductInvalid

        self.map_chef_description_path: Optional[Path]
        self.map_chef_description_path = self._get_latest_map_chef_description_path()
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
        Determine MapChef description/output file for the latest product iteration.

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
        Get a property from MapChef description/output file.

        :type description_property: str
        :param description_property: key of the property to get
        :rtype str
        :return: value of the property to get
        """
        with open(str(self.map_chef_description_path), mode="r") as description_file:
            description_data: Dict[str, str] = json.load(fp=description_file)
            return description_data[description_property]

    def _get_map_chef_primary_layers(self) -> List[MapLayer]:
        """
        Get layer information from the primary map frame in the MapChef description/output file.

        Note: This method is not ideal in terms of duplicating code for reading the description file contents. See
        https://github.com/mapaction/rolling-data-scramble-dashboard-poc/issues/13#issuecomment-776567511.

        :rtype List[MapLayer]
        :return: layers in the primary map frame
        """
        with open(str(self.map_chef_description_path), mode="r") as description_file:
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
    Represents an operational response.

    In abstract terms, this class represents an activation for a given country (an operation).
    In concrete terms, this class represents properties of a Crash Move Folder (CMF) for a given activation.

    For the purposes of the Rolling Data Scramble dashboard, operations represent the rows in the dashboard.

    With the exception of the root to the Crash Move Folder, all class instance properties are loaded dynamically from
    the `event_description.json` or `cmf_description.json` configuration files.

    As with other classes, only methods and properties required for the Rolling Data Scramble dashboard are included.
    It's very likely there's a better way to do this, see [#13] for discussion.
    """

    def __init__(self, base_path: Path) -> None:
        """
        Load operation properties from description files and perform minimal validation.

        Validation is currently limited to whether the operation ID is not an empty string. This is intended to prevent
        an unconfigured CMF being processed, as this will lead to errors later on.

        @todo: find a better of determining whether a CMF has not been configured [#9]
        :raises OperationInvalid: If the operation ID is an empty string, the operation is considered invalid.

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
        self.layer_properties_path: Path = self.base_path.joinpath(
            Path(
                self._get_description_property(
                    description_path=self.crash_move_folder_description_path,
                    description_property="layer_properties",
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
        Get a property from the `event_description.json` or `cmf_description.json` configuration file.

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
        """
        Get a specified map product.

        :type map_product_id: str
        :param map_product_id: map product ID
        :rtype MapProduct
        :return: Specified map product
        """
        map_product_path: Path = self.map_products_path.joinpath(map_product_id)
        return MapProduct(base_path=map_product_path)

    def get_layer_properties(self) -> List[MapLayer]:
        """
        Get layers used in MapChef automation.

        Intended where a required MapProduct does not exist but information about the layers it would contain is
        necessary.

        This information taken from the `layerProperties.json` file, included as part of the MapChef configuration, and
        representing the layers used in the MA9999 (all layers) product. This is useful in situations where there
        MapChef has not yet been run (new operations for example), meaning no products have been generated, meaning
        there are no output files that can be processed.

        ;:rtype List[MapLayer]
        :return: layers used in MapChef automation
        """
        layers: List[MapLayer] = []
        layer_definitions: List[Dict[str, Any]] = list()
        with open(self.layer_properties_path, mode="r") as layers_properties_file:
            layers_properties_data: Dict[str, List[Dict[str, Any]]]
            layers_properties_data = json.load(fp=layers_properties_file)
            layer_definitions = layers_properties_data["layerProperties"]

        for layer in layer_definitions:
            layers.append(
                MapLayer(
                    layer_id=layer["name"], error_messages=["MAPCHEF_OUTPUT_MISSING"]
                )
            )

        return layers

    def export(self) -> Dict[str, str]:
        """
        Return information about an Operation for use in exports.

        :return: Operation information
        :rtype Dict[str, str]
        """
        return {
            "affected_country_iso3": self.affected_country.alpha_3,
            "affected_country_name": self.affected_country.name,
            "id": self.operation_id,
            "name": self.operation_name,
        }


class Evaluation:
    """
    Represents the status of a layer for a operation.

    I.e. the cells in the dashboard.

    Evaluations are effectively key value pairs, where the key is a composite of an operation and a layer, and the
    value is whether that layer for that operation has any errors reported by MapChef.

    Evaluations are stateful, in that evaluations are initially unevaluated then later evaluated by calling the
    `evaluate()` method.

    The `error_mapping` dict is used to determine which result to use for each error, the most severe of which will
    be the overall evaluation result.
    """

    error_mapping: Dict[MapChefError, EvaluationResult] = {
        MapChefError.MAPCHEF_OUTPUT_MISSING: EvaluationResult.FAIL,
        MapChefError.LAYER_DATASOURCE_NONE: EvaluationResult.FAIL,
        MapChefError.LAYER_DATASOURCE_MULTIPLE: EvaluationResult.PASS_WITH_WARNINGS,
        MapChefError.LAYER_SCHEMA_INVALID: EvaluationResult.PASS_WITH_WARNINGS,
    }

    def __init__(self, operation_id: str, layer: MapLayer) -> None:
        """
        Set Operation and Map Layer properties.

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
        Evaluate a layer by checking whether it has any errors.

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
    Process Operations for a set of operation IDs.

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
        full_operation_path: Path = config["google_drive_base_path"].joinpath(
            config["google_drive_operations_path"], operation_path
        )
        try:
            # operation_path.resolve(strict=True)
            operations.append(Operation(base_path=full_operation_path))
        except FileNotFoundError:
            logging.warning(
                f"Operation path '{full_operation_path}' does not appear to exist, ignoring operation."
            )
        except OperationInvalid:
            logging.warning(
                f"Operation path '{full_operation_path}' does not appear to be valid, ignoring operation."
            )

    return operations


def parse_operation_layers(
    config: Config, operations: List[Operation]
) -> Dict[str, List[MapLayer]]:
    """
    Process MapLayers from the 'all layers' MapProduct, for and grouped by, a set of Operations.

    MapLayers are returned in a list per Operation so that an association between a layer and it's operation can be
    inferred elsewhere as this can't be set within objects currently [#16].

    Where an operation does not include the 'all layers' product (because MapChef has not yet been run for example),
    the layers that this export will contain are used instead [#20]..

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
        except MapProductInvalid:
            layers[operation.operation_id] = operation.get_layer_properties()

    return layers


def filter_valid_operations(
    operations: List[Operation], operation_layers: Dict[str, List[MapLayer]]
) -> List[Operation]:
    """
    Filter a set of Operations to those with a set of MapLayers.

    Operations without MapLayers are considered invalid (because they can't be evaluated), however as operations aren't
    related to their layers [#16], it's not possible to determine valid operations by themselves.

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
    Initialise Evaluations for a set of Operations and MapLayers.

    As MapLayers are not linked to their operations [#16], this method uses additional context to set this for each
    operation:layer composite.

    Note: this method only initialises evaluations, rather than perform them.

    :type operation_layers: Dict[str, List[MapLayer]]
    :param operation_layers: layers grouped by Operation ID
    :rtype List[Evaluation]
    :return: initialised evaluations
    """
    evaluations: List[Evaluation] = list()

    for operation_id, operations_layers in operation_layers.items():
        for operation_layer in operations_layers:
            evaluations.append(
                Evaluation(operation_id=operation_id, layer=operation_layer)
            )

    return evaluations


def process_evaluations(evaluations: List[Evaluation]) -> None:
    """
    Process each evaluation's evaluate method.

    :type evaluations: List[Evaluation]
    :param evaluations: evaluations to process
    """
    for evaluation in evaluations:
        evaluation.evaluate()


def summarise_evaluations(evaluations: List[Evaluation]) -> Dict[str, dict]:
    """
    Aggregate and summarise evaluation results for use in exports.

    Summarises evaluations by:
        1. totalling each result type, across all operations and layers
        2. totalling each result type, by each operation
        3. aggregating results for each operation and layer

    For (3), the most significant (serve) result in each aggregation is used as the aggregated result (e.g. if the
    results in an aggregation are [PASS, FAIL, PASS_WITH_WARNINGS] the aggregated result will be FAIL. See the
    EvaluationResult enumeration for more information on the significance of each result type. The aggregations are
    based on the MapAction Data Naming Conventions [1], specifically the Category clause [2].

    [1] https://mapaction.atlassian.net/wiki/spaces/datacircle/pages/10137499820
    [2] https://mapaction.atlassian.net/wiki/spaces/datacircle/pages/10294491254

    :type evaluations: List[Evaluation]
    :param evaluations: list of evaluations
    :rtype summary_evaluations: Dict
    :return: summarised evaluations
    """
    _totals_by_result: Dict[str, int] = {
        EvaluationResult.NOT_EVALUATED.name: 0,
        EvaluationResult.PASS.name: 0,
        EvaluationResult.PASS_WITH_WARNINGS.name: 0,
        EvaluationResult.FAIL.name: 0,
        EvaluationResult.ERROR.name: 0,
    }
    _totals_by_result_by_operation: Dict[str, Dict[str, int]] = {}
    _aggregated_layer_results_by_operation: Dict[str, Dict[str, str]] = {}

    for evaluation in evaluations:
        if evaluation.operation_id not in _totals_by_result_by_operation.keys():
            _totals_by_result_by_operation[evaluation.operation_id] = {
                EvaluationResult.NOT_EVALUATED.name: 0,
                EvaluationResult.PASS.name: 0,
                EvaluationResult.PASS_WITH_WARNINGS.name: 0,
                EvaluationResult.FAIL.name: 0,
                EvaluationResult.ERROR.name: 0,
            }
        _totals_by_result[evaluation.result.name] += 1
        _totals_by_result_by_operation[evaluation.operation_id][
            evaluation.result.name
        ] += 1

        layer_category = evaluation.layer.layer_id.split(sep="-")[1]
        if evaluation.operation_id not in _aggregated_layer_results_by_operation.keys():
            _aggregated_layer_results_by_operation[evaluation.operation_id] = dict()
        if (
            layer_category
            not in _aggregated_layer_results_by_operation[
                evaluation.operation_id
            ].keys()
        ):
            _aggregated_layer_results_by_operation[evaluation.operation_id][
                layer_category
            ] = EvaluationResult.NOT_EVALUATED.name
        if (
            evaluation.result.value
            > EvaluationResult[
                _aggregated_layer_results_by_operation[evaluation.operation_id][
                    layer_category
                ]
            ].value
        ):
            _aggregated_layer_results_by_operation[evaluation.operation_id][
                layer_category
            ] = evaluation.result.name

    return {
        "totals_by_result": _totals_by_result,
        "totals_by_result_by_operation": _totals_by_result_by_operation,
        "aggregated_layer_results_by_operation": _aggregated_layer_results_by_operation,
    }


def prepare_export(
    evaluations: List[Evaluation],
    summary_evaluations: Dict[str, dict],
    operations: List[Operation],
) -> dict:
    """
    Structures data results of evaluations for use in an export.

    The intention of this method is to structure information in a way that makes it easy to use in reporting tools
    (i.e. exports), as a result there is lots f duplication and simplification of data types for example.

    Note: The structure and contents of this data have not yet been discussed or agreed.

    :type evaluations: List[Evaluation]
    :param evaluations: list of evaluations
    :type summary_evaluations: Dict
    :param summary_evaluations: summarised evaluations
    :type operations: List[Operation]
    :param operations: list of operations
    :rtype dict
    :return: processes data ready for use in exports
    """
    export_version: int = 1

    _operations: List[dict] = list()
    _operations_by_id: Dict[str, dict] = dict()
    _countries: Dict[str, str] = dict()
    for operation in operations:
        _operations.append(operation.export())
        _operations_by_id[operation.operation_id] = operation.export()
        _countries[operation.affected_country.alpha_3] = operation.affected_country.name

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
            _results_by_operation[evaluation.operation_id] = dict()
        _results_by_operation[evaluation.operation_id][
            evaluation.layer.layer_id
        ] = evaluation.result.name

        if evaluation.layer.layer_id not in _results_by_layer.keys():
            _results_by_layer[evaluation.layer.layer_id] = dict()
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

    return {
        "meta": {
            "app_version": __version__,
            "export_version": export_version,
            "export_datetime": datetime.utcnow().isoformat(timespec="milliseconds"),
            "display_labels": {
                "result_types": {
                    EvaluationResult.NOT_EVALUATED.name: "Not Evaluated",
                    EvaluationResult.PASS.name: "Pass",
                    EvaluationResult.PASS_WITH_WARNINGS.name: "Warning",
                    EvaluationResult.FAIL.name: "Fail",
                    EvaluationResult.ERROR.name: "Error",
                },
                "layer_aggregation_categories": {
                    "admn": "Admin",
                    "carto": "Cartographic",
                    "elev": "Elevation",
                    "phys": "Physical features",
                    "stle": "Settlements",
                    "tran": "Transport",
                },
            },
        },
        "data": {
            "operations": _operations,
            "operations_by_id": _operations_by_id,
            "countries": _countries,
            "results_by_operation": _results_by_operation,
            "results_by_layer": _results_by_layer,
            "results_by_result": _results_by_result,
            "ungrouped_results": _ungrouped_results,
            "summary_statistics": summary_evaluations,
        },
    }


def export_json(export_data: dict, export_path: Path) -> None:
    """
    JSON exporter.

    Minimal example of an exporter.

    :type export_data: dict
    :param export_data: data generated by `generate_export()`
    :type export_path: Path
    :param export_path: path to destination export
    """
    with open(export_path, mode="w") as export_file:
        json.dump(obj=export_data, fp=export_file, indent=4, sort_keys=True)


def export_google_sheets(config: Config, export_data: dict) -> None:
    """
    Google Sheets exporter.

    More complex example of an exporter using a Google Sheets spreadsheet.

    Spreadsheet link: https://docs.google.com/spreadsheets/d/1MSXc-1mffyv_EtiXWvpu-cDc92UAutRkXVFV4ICILx8/

    Three sheets are created:
        1. a summary of results from the current run (layers per operation/country, aggregated by category)
        2. detailed results from the current run (layers per operation/country)
        3. detailed results from the last run of each day (adds one sheet every new day this app is run)

    Each dict of summary or detail results needs to be ordered so that values in each row match the right column header.

    Normally this would be fine as items are used as key:value pairs, but here they're split and we need to rely on
    element order to set the right position.

    :type config: Config
    :param config: application configuration
    :type export_data: dict
    :param export_data: data generated by `generate_export()`
    """
    summary_data: dict = {}
    for operation, aggregated_country_results in export_data["data"][
        "summary_statistics"
    ]["aggregated_layer_results_by_operation"].items():
        aggregated_country_results = OrderedDict(
            sorted(aggregated_country_results.items())
        )
        summary_data[
            export_data["data"]["operations_by_id"][operation]["affected_country_name"]
        ] = aggregated_country_results.values()
    summary_dataframe: pd.DataFrame = pd.DataFrame.from_dict(
        summary_data,
        orient="index",
        columns=sorted(
            export_data["meta"]["display_labels"]["layer_aggregation_categories"].keys()
        ),
    )
    summary_dataframe.rename(
        export_data["meta"]["display_labels"]["layer_aggregation_categories"],
        axis="columns",
        inplace=True,
    )
    summary_dataframe.replace(
        to_replace=export_data["meta"]["display_labels"]["result_types"], inplace=True
    )
    summary_dataframe = summary_dataframe.transpose()

    data: dict = {}
    for operation, country_results in export_data["data"][
        "results_by_operation"
    ].items():
        country_results = OrderedDict(sorted(country_results.items()))
        data[
            export_data["data"]["operations_by_id"][operation]["affected_country_name"]
        ] = country_results.values()
    detail_dataframe: pd.DataFrame = pd.DataFrame.from_dict(
        data,
        orient="index",
        columns=sorted(export_data["data"]["results_by_layer"].keys()),
    )
    detail_dataframe.replace(
        to_replace=export_data["meta"]["display_labels"]["result_types"], inplace=True
    )
    detail_dataframe = detail_dataframe.transpose()

    google_credentials: service_account = (
        ServiceAccountCredentials.from_json_keyfile_name(
            filename=config["google_service_credential_path"],
            scopes=config["google_service_credential_scopes"],
        )
    )

    d2g.upload(
        df=summary_dataframe,
        gfile=config["google_sheets_key"],
        wks_name=config["google_sheets_summary_sheet_name"],
        credentials=google_credentials,
        row_names=True,
        col_names=True,
    )
    d2g.upload(
        df=detail_dataframe,
        gfile=config["google_sheets_key"],
        wks_name=config["google_sheets_detail_sheet_name"],
        credentials=google_credentials,
        row_names=True,
        col_names=True,
    )
    d2g.upload(
        df=detail_dataframe,
        gfile=config["google_sheets_key"],
        wks_name=f"output-{datetime.utcnow().date().isoformat()}",
        credentials=google_credentials,
        row_names=True,
        col_names=True,
    )


def run() -> None:
    """Chain functions together and configure the application."""
    logging.basicConfig(stream=sys.stdout, level=logging.WARNING)

    operations = parse_operations(config=app_config)
    operation_layers = parse_operation_layers(config=app_config, operations=operations)
    operations = filter_valid_operations(
        operations=operations, operation_layers=operation_layers
    )
    evaluations = generate_evaluations(operation_layers=operation_layers)
    process_evaluations(evaluations=evaluations)
    summary_evaluations = summarise_evaluations(evaluations=evaluations)
    export_data = prepare_export(
        evaluations=evaluations,
        summary_evaluations=summary_evaluations,
        operations=operations,
    )
    export_json(export_data=export_data, export_path=app_config["export_path"])
    export_google_sheets(config=app_config, export_data=export_data)
