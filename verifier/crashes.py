"""Checks for the crash-data tools and the answer-question task. Pure functions of their arguments."""

import math
import re

from contract import AnswerKind, Column, NumericColumn, Op, Stat

from .checks import result

ROWS = 400  # the bundled dataset's size, fixed with it
VALUES = {
    Column.ROAD: {"I-45", "I-10", "US-59", "I-610", "BW-8"},
    Column.SEVERITY: {"none", "minor", "serious", "fatal"},
    Column.WEATHER: {"clear", "rain", "fog"},
    Column.LIGHTING: {"day", "night"},
    Column.WEEKDAY: {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"},
}
RANGES = {Column.HOUR: (0, 23), Column.VEHICLES: (1, 5), Column.INJURIES: (0, 6)}
DATE = re.compile(r"^2025-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
WHOLE = re.compile(r"^-?\d+$")
NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


def _filter_problem(condition):
    if condition.column in RANGES:
        if not WHOLE.fullmatch(condition.value.strip()):
            return f"{condition.column.value} holds whole numbers, not {condition.value!r}"
        return None
    if condition.op not in (Op.EQ, Op.NE):
        return f"{condition.column.value} is not numeric: compare it only with eq or ne"
    if condition.column == Column.DATE:
        return None if DATE.fullmatch(condition.value) else f"date must be 2025-MM-DD, not {condition.value!r}"
    if condition.value not in VALUES[condition.column]:
        return f"{condition.column.value} is never {condition.value!r}"
    return None


def _filters_problem(filters):
    for condition in filters:
        problem = _filter_problem(condition)
        if problem:
            return problem
    return None


def verify_describe_input(value):
    return result(True, "input is valid")


def verify_filters_input(value):
    problem = _filters_problem(value.filters)
    return result(problem is None, problem or "input is valid")


def verify_describe_output(input_value, output, workspace):
    if output.rows != ROWS:
        return result(False, f"the dataset holds {ROWS} crashes, not {output.rows}")
    if sorted(column.name.value for column in output.columns) != sorted(column.value for column in Column):
        return result(False, "every column must be described once")
    return result(True, "the dataset is described")


def verify_count_output(input_value, output, workspace):
    if not 0 <= output.count <= ROWS:
        return result(False, f"a count must be 0 to {ROWS}")
    if not input_value.filters and output.count != ROWS:
        return result(False, f"with no filters every one of the {ROWS} crashes counts")
    return result(True, f"{output.count} crashes", count=output.count)


def verify_group_output(input_value, output, workspace):
    values = [group.value for group in output.groups]
    if len(set(values)) != len(values):
        return result(False, "a value is listed twice")
    if any(group.count <= 0 for group in output.groups):
        return result(False, "every group must hold at least one crash")
    if sum(group.count for group in output.groups) > ROWS:
        return result(False, f"the groups hold more than the {ROWS} crashes")
    order = [(-group.count, group.value) for group in output.groups]
    if order != sorted(order):
        return result(False, "groups must be most crashes first, ties by value")
    known = VALUES.get(input_value.group_by)
    if known is not None and not set(values) <= known:
        return result(False, f"{input_value.group_by.value} has no value {min(set(values) - known)!r}")
    return result(True, f"{len(values)} groups")


def verify_stat_output(input_value, output, workspace):
    if not math.isfinite(output.value) or not 0 <= output.rows <= ROWS:
        return result(False, "the statistic is not a finite number over 0 to 400 crashes")
    if output.rows == 0 and not (input_value.stat == Stat.SUM and output.value == 0):
        return result(False, "a statistic over no crashes is only a sum of 0")
    low, high = RANGES[Column(NumericColumn(input_value.column).value)]
    if input_value.stat != Stat.SUM and output.rows and not low <= output.value <= high:
        return result(False, f"a {input_value.stat.value} of {input_value.column.value} must lie in {low} to {high}")
    if input_value.stat == Stat.SUM and not low * output.rows <= output.value <= high * output.rows:
        return result(False, "the sum is out of range for its rows")
    return result(True, f"{input_value.stat.value} over {output.rows} crashes", value=output.value)


def verify_key_output(input_value, output, workspace):
    if output.kind == AnswerKind.CATEGORY and not output.accepted:
        return result(False, "a category answer needs an accepted value")
    if output.kind == AnswerKind.NUMBER and (output.accepted or output.tolerance < 0):
        return result(False, "a number answer has no accepted values and a non-negative tolerance")
    return result(True, "the answer key is consistent")


def _parse_number(text):
    cleaned = text.strip().rstrip("%").replace(",", "").strip()
    return float(cleaned) if NUMBER.fullmatch(cleaned) else None


def _normalize(text):
    cleaned = text.strip().strip(".").casefold()
    return cleaned[:-3] if re.fullmatch(r"\d{1,2}:00", cleaned) else cleaned


def verify_answer(arguments, output, reference, workspace):
    if reference is None:
        return result(False, "there is no answer key to judge against")
    if not output.answer.strip():
        return result(False, "the answer is blank")
    if reference.kind == AnswerKind.NUMBER:
        given = _parse_number(output.answer)
        if given is None:
            return result(False, f"{output.answer!r} is not a number", expected=reference.number)
        error = abs(given - reference.number)
        if error > reference.tolerance + 1e-9:
            return result(False, f"{given:g} is off by {error:g}; allowed {reference.tolerance:g}", expected=reference.number)
        return result(True, f"{given:g} is right", expected=reference.number)
    accepted = {_normalize(value) for value in reference.accepted}
    if _normalize(output.answer) not in accepted:
        return result(False, f"{output.answer!r} is not the answer", expected=reference.accepted)
    return result(True, f"{output.answer.strip()} is right", expected=reference.accepted)
