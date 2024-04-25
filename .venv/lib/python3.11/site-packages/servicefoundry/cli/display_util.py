import datetime
import functools
import json

from rich import box
from rich import print_json as _rich_print_json
from rich.table import Table

from servicefoundry.cli.config import CliConfig
from servicefoundry.cli.console import console
from servicefoundry.cli.const import DISPLAY_DATETIME_FORMAT
from servicefoundry.json_util import json_default_encoder


def print_json(data, default=json_default_encoder):
    return _rich_print_json(
        json.dumps(data, default=default), highlight=False, default=default
    )


NO_WRAP_COLUMNS = {"fqn"}


def get_table(title):
    return Table(title=title, show_lines=False, safe_box=True, box=box.MINIMAL)


def stringify(x):
    if isinstance(x, datetime.datetime):
        return x.astimezone().strftime(DISPLAY_DATETIME_FORMAT)
    elif isinstance(x, str):
        return x
    else:
        return str(x)


def display_time_passed(seconds: int):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    result = ""
    if d != 0:
        result = f"{int(d)}D"
    elif h != 0 and m != 0:
        result = f"{int(h)}h {int(m)}m"
    elif h != 0:
        result = f"{int(h)}h"
    elif m != 0 and s != 0:
        result = f"{int(m)}m {int(s)}s"
    elif m != 0:
        result = f"{int(m)}m"
    elif s != 0:
        result = f"{int(s)}s"
    return result


def print_entity_list(title, items):
    items = [item.list_row_data() for item in items]
    if CliConfig.get("json"):
        print_json(data=items)
        return

    table = get_table(title)

    columns = []
    if items:
        columns = items[0].keys()
        for column in columns:
            no_wrap = column in NO_WRAP_COLUMNS
            table.add_column(column, justify="left", overflow="fold", no_wrap=no_wrap)

    for item in items:
        row = []
        for c in columns:
            row.append(stringify(item[c]))
        table.add_row(*row)
    console.print(table)


def print_obj(title, item, columns=None):
    if CliConfig.get("json"):
        print_json(data=item)
        return

    table = get_table(title)

    if not columns:
        columns = item.keys()

    # transpose
    keys, columns = columns, ["key", "value"]

    for column in columns:
        no_wrap = column in NO_WRAP_COLUMNS
        table.add_column(column, justify="left", overflow="fold", no_wrap=no_wrap)
    for key in keys:
        table.add_row(f"[bold]{stringify(key)}[/]", stringify(item[key]))
    console.print(table)


def print_entity_obj(title, entity):
    if CliConfig.get("json"):
        print_json(data=entity)
        return

    table = get_table(title)

    columns = entity.get_data().keys()

    # transpose
    keys, columns = columns, ["key", "value"]

    for column in columns:
        no_wrap = "FQN" in column or "Name" in column
        table.add_column(column, justify="left", overflow="fold", no_wrap=no_wrap)
    entity_data = entity.get_data()
    for key in keys:
        table.add_row(f"[bold]{stringify(key)}[/]", stringify(entity_data[key]))
    console.print(table)
