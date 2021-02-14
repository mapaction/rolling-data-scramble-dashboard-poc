from typing import Union

from rich import box
from rich.console import Console
from rich.columns import Columns
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import track, Progress, BarColumn, ProgressColumn, GetTimeCallable
from rich.tree import Tree
from rich.table import Table


def _colour_result(result):
    if result == "PASS":
        return "green"
    if result == "FAIL":
        return "red"
    elif result == "PASS_WITH_WARNINGS":
        return "yellow"
    elif result == "NOT_EVALUATED":
        return "orange3 reverse"
    elif result == "ERROR":
        return "magenta reverse"


def _index_operations(operations):
    _operations = dict()
    for operation in operations:
        _operations[operation["id"]] = operation
    return _operations


def _sum_operation_results(operation):
    _results = {
        "PASS": 0,
        "PASS_WITH_WARNINGS": 0,
        "FAIL": 0,
        "NOT_EVALUATED": 0,
        "ERROR": 0,
    }
    for layer, result in operation.items():
        _results[result] += 1
    return _results


def _sum_results(summary_stats):
    total = 0
    for result in summary_stats.values():
        total += result
    return total


def columns1(export_data):
    console = Console()

    results = []
    # for result in export_data["data"]["ungrouped_results"][9:13]:
    for result in export_data["data"]["ungrouped_results"]:
        results.append(
            Panel(
                f"[b]{result['operation_id']}[/b]\n[blue]{result['layer_id']}\n[{_colour_result(result['result'])}]{result['result']}",
                expand=True,
            )
        )
    console.print(Columns(results))


def columns2(export_data):
    console = Console()

    operations = _index_operations(operations=export_data["data"]["operations"])
    for operation_id, operation in operations.items():
        console.print(
            Markdown(
                f"# {operation['name']} - {operation['affected_country_name']} "
                f"[{operation['id']} - {operation['affected_country_iso3']}]"
            )
        )
        _results = []
        for layer, result in export_data["data"]["results_by_operation"][
            operation_id
        ].items():
            _results.append(f"{layer}\n[{_colour_result(result)}]{result}")
        console.print(Columns(_results))


def tree1(export_data):
    console = Console()

    tree = Tree("Rolling Data Scramble Dashboard")
    for operation_id, operation in export_data["data"]["results_by_operation"].items():
        sub_tree = tree.add(operation_id)
        for layer_id, result in operation.items():
            sub_sub_tree = sub_tree.add(layer_id)
            sub_sub_tree.add(f"[{_colour_result(result)}]{result}")

    console.print(tree)


def table1(export_data):
    console = Console()

    table = Table(title="Rolling Data Scramble Dashboard", box=box.ROUNDED)

    table.add_column("Affected Country")
    table.add_column("Layer")
    table.add_column("Result", justify="right")

    for operation_id, operation in export_data["data"]["results_by_operation"].items():
        affected_country = _index_operations(
            operations=export_data["data"]["operations"]
        )[operation_id]["affected_country_name"]
        for layer_id, result in operation.items():
            table.add_row(
                f"{affected_country}",
                layer_id,
                f"[{_colour_result(result)}]{result}",
            )

    console.print(table)


def table2(export_data):
    console = Console()

    table = Table(title="Rolling Data Scramble Dashboard", box=box.ROUNDED)

    table.add_column("Affected Country")
    table.add_column("Passing Layers")
    table.add_column("Passing (with warnings) Layers")
    table.add_column("Failing Layers")
    table.add_column("Unevaluated Layers")
    table.add_column("Errors")
    table.add_column("Total")

    for operation_id, operation_results in export_data["data"][
        "results_by_operation"
    ].items():
        affected_country = _index_operations(
            operations=export_data["data"]["operations"]
        )[operation_id]["affected_country_name"]

        results = _sum_operation_results(operation_results)
        total_results = len(operation_results)

        table.add_row(
            affected_country,
            f"[{_colour_result('PASS')}]{results['PASS']}",
            f"[{_colour_result('PASS_WITH_WARNINGS')}]{results['PASS_WITH_WARNINGS']}",
            f"[{_colour_result('FAIL')}]{results['FAIL']}",
            f"[{_colour_result('NOT_EVALUATED')}]{results['NOT_EVALUATED']}",
            f"[{_colour_result('ERROR')}]{results['ERROR']}",
            f"[blue]{total_results}",
        )

    console.print(table)


def table3(export_data):
    console = Console()

    table = Table(title="Rolling Data Scramble Dashboard", box=box.SIMPLE_HEAVY)

    table.add_column("Affected Country")
    table.add_column("Layers")
    table.add_column("")

    for operation_id, operation_results in export_data["data"][
        "results_by_operation"
    ].items():
        affected_country = _index_operations(
            operations=export_data["data"]["operations"]
        )[operation_id]["affected_country_name"]

        total_results = len(operation_results)
        _results = []
        for result in operation_results.values():
            _results.append(f"[{_colour_result(result)}]=")
        foo = "".join(_results)

        table.add_row(affected_country, foo, f"[blue]{total_results}")

    console.print(table)


def progress1(export_data):
    total_results = _sum_results(export_data["data"]["summary_statistics"]["results"])

    for result_type, result in export_data["data"]["summary_statistics"][
        "results"
    ].items():
        for step in track(
            range(result),
            total=total_results,
            description=f"[{_colour_result(result_type)}]{str(result_type).rjust(20, ' ')}",
        ):
            step += 1


def progress2(export_data):
    total_results = _sum_results(export_data["data"]["summary_statistics"]["results"])

    with Progress(
        "[progress.description]{task.description}",
        BarColumn(complete_style="blue"),
        "[progress.percentage]{task.percentage:>3.0f}%",
    ) as progress:
        for result_type, result in export_data["data"]["summary_statistics"][
            "results"
        ].items():
            task = progress.add_task(
                f"[{_colour_result(result_type)}]{str(result_type).rjust(20, ' ')}",
                total=total_results,
            )
            progress.update(task, advance=result)


def progress3(export_data):
    total_results = _sum_results(export_data["data"]["summary_statistics"]["results"])

    for result_type, result in export_data["data"]["summary_statistics"][
        "results"
    ].items():
        with Progress(
            "[progress.description]{task.description}",
            BarColumn(complete_style=_colour_result(result_type)),
            "[progress.percentage]{task.percentage:>3.0f}%",
        ) as progress:
            task = progress.add_task(
                str(result_type).rjust(20, " "),
                total=total_results,
            )
            progress.update(task, advance=result)


class TableProgress1(Progress):
    def __init__(
        self,
        *columns: Union[str, ProgressColumn],
        console: Console = None,
        auto_refresh: bool = True,
        refresh_per_second: float = None,
        speed_estimate_period: float = 30.0,
        transient: bool = False,
        redirect_stdout: bool = True,
        redirect_stderr: bool = True,
        get_time: GetTimeCallable = None,
        disable: bool = False,
        table: Table = None,
    ) -> None:
        self.table = table
        super().__init__(
            *columns,
            console=console,
            auto_refresh=auto_refresh,
            refresh_per_second=refresh_per_second,
            speed_estimate_period=speed_estimate_period,
            transient=transient,
            redirect_stdout=redirect_stdout,
            redirect_stderr=redirect_stderr,
            get_time=get_time,
            disable=disable,
        )

    def get_renderables(self):
        if self.table is not None:
            yield self.table.add_row("foo", self.make_tasks_table(self.tasks))


def table_progress1(export_data):
    console = Console()

    total_results = _sum_results(export_data["data"]["summary_statistics"]["results"])
    table = Table(title="Rolling Data Scramble Dashboard", box=box.ROUNDED)

    table.add_column("Country")
    table.add_column("Progress")

    with TableProgress1(
        "[progress.description]{task.description}",
        BarColumn(complete_style="blue"),
        "[progress.percentage]{task.percentage:>3.0f}%",
        console=console,
        auto_refresh=False,
        table=table,
    ) as progress:
        task = progress.add_task(
            str("result_type").rjust(20, " "),
            total=total_results,
        )
        progress.update(task, advance=20)
        progress.refresh()

    table.add_row(
        "foo",
        "100%",
    )

    console.print(table)
