import json
from pathlib import Path

from dagster import (
    execute_pipeline,
    pipeline,
    solid,
    DagsterType,
    AssetMaterialization,
    EventMetadataEntry,
    Output,
)

from mapaction_rds_dashboard.config import config as app_config
from mapaction_rds_dashboard.app import (
    parse_operations as _parse_operations,
    parse_operation_layers as _parse_operation_layers,
    filter_valid_operations as _filter_valid_operations,
    generate_evaluations as _generate_evaluations,
    process_evaluations as _process_evaluations,
    summarise_evaluations as _summarise_evaluations,
    prepare_export as _prepare_export,
)

AppConfigDagsterType = DagsterType(
    name="AppConfigDagsterType",
    type_check_fn=lambda _, value: isinstance(value, dict),
    description="Application configuration options.",
)

OperationsDagsterType = DagsterType(
    name="OperationsDagsterType",
    type_check_fn=lambda _, value: isinstance(value, list),
    description="Operation instances.",
)

OperationLayersDagsterType = DagsterType(
    name="OperationLayersDagsterType",
    type_check_fn=lambda _, value: isinstance(value, dict),
    description="Layers for each operation indexed by operation ID.",
)


EvaluationsDagsterType = DagsterType(
    name="EvaluationsDagsterType",
    type_check_fn=lambda _, value: isinstance(value, list),
    description="Evaluations for each layer in each operation.",
)


@solid
def get_config(_) -> AppConfigDagsterType:
    return app_config


@solid
def get_operations(context, _config: AppConfigDagsterType) -> OperationsDagsterType:
    return _parse_operations(config=_config)


@solid
def get_operation_layers(
    context, _config: AppConfigDagsterType, operations: OperationsDagsterType
) -> OperationLayersDagsterType:
    return _parse_operation_layers(config=_config, operations=operations)


@solid
def filter_operations(
    context,
    operations: OperationsDagsterType,
    operation_layers: OperationLayersDagsterType,
) -> OperationsDagsterType:
    return _filter_valid_operations(
        operations=operations, operation_layers=operation_layers
    )


@solid
def generate_evaluations(
    context, operation_layers: OperationLayersDagsterType
) -> EvaluationsDagsterType:
    return _generate_evaluations(operation_layers=operation_layers)


@solid
def process_evaluations(context, evaluations: EvaluationsDagsterType) -> None:
    return _process_evaluations(evaluations=evaluations)


@solid
def summarise_evaluations(context, evaluations: EvaluationsDagsterType) -> dict:
    return _summarise_evaluations(evaluations=evaluations)


@solid
def prepare_export(
    context,
    evaluations: EvaluationsDagsterType,
    summary_evaluations: dict,
    operations: OperationsDagsterType,
) -> dict:
    return _prepare_export(
        evaluations=evaluations,
        summary_evaluations=summary_evaluations,
        operations=operations,
    )


@solid
def export_json(context, _config: AppConfigDagsterType, export_data: dict) -> None:
    export_path = _config["export_path"]
    with open(export_path, mode="w") as export_file:
        json.dump(obj=export_data, fp=export_file, indent=4, sort_keys=True)

    yield AssetMaterialization(
        asset_key="export",
        description="Data export",
        metadata_entries=[
            EventMetadataEntry.path(str(export_path.absolute()), "export_path")
        ],
    )
    yield Output(None)


@solid
def export_google_sheets(
    context, _config: AppConfigDagsterType, export_data: dict
) -> None:
    context.log.info("Export to Google sheets")


@pipeline
def rds_dashboard_pipeline():
    config = get_config()
    operations = get_operations(_config=config)
    operation_layers = get_operation_layers(_config=config, operations=operations)
    operations = filter_operations(
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
    export_json(_config=config, export_data=export_data)
    export_google_sheets(_config=config, export_data=export_data)


def run():
    execute_pipeline(rds_dashboard_pipeline)
