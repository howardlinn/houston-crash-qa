"""Queries over the bundled synthetic crash dataset (data/crashes.json), and the questions' answer key."""

import json
import statistics
from collections import Counter
from pathlib import Path

from contract import (
    AnswerKeyOutput,
    AnswerKind,
    Column,
    ColumnInfo,
    CountInput,
    CountOutput,
    DescribeInput,
    DescribeOutput,
    Filter,
    Group,
    GroupInput,
    GroupOutput,
    Op,
    Question,
    QuestionInput,
    Stat,
    StatInput,
    StatOutput,
)

ROWS = json.loads((Path(__file__).parent / "data" / "crashes.json").read_text(encoding="utf-8"))
NUMERIC = {"hour", "vehicles", "injuries"}
COMPARE = {
    Op.EQ: lambda a, b: a == b,
    Op.NE: lambda a, b: a != b,
    Op.GT: lambda a, b: a > b,
    Op.GE: lambda a, b: a >= b,
    Op.LT: lambda a, b: a < b,
    Op.LE: lambda a, b: a <= b,
}
STATS = {
    Stat.MEAN: statistics.fmean,
    Stat.MEDIAN: statistics.median,
    Stat.SUM: sum,
    Stat.MIN: min,
    Stat.MAX: max,
}


def _matcher(condition: Filter):
    name = condition.column.value
    if name in NUMERIC:
        try:
            wanted = int(condition.value)
        except ValueError:
            raise ValueError(f"{name} holds whole numbers, not {condition.value!r}") from None
    else:
        if condition.op not in (Op.EQ, Op.NE):
            raise ValueError(f"{name} is not numeric: compare it only with eq or ne")
        known = {row[name] for row in ROWS}
        if name != "date" and condition.value not in known:
            raise ValueError(f"{name} is never {condition.value!r}; its values: {', '.join(sorted(known))}")
        wanted = condition.value
    compare = COMPARE[condition.op]
    return lambda row: compare(row[name], wanted)


def select(filters):
    matchers = [_matcher(condition) for condition in filters]
    return [row for row in ROWS if all(match(row) for match in matchers)]


def groups(column, filters):
    counts = Counter(str(row[column]) for row in select(filters))
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def describe_dataset(value: DescribeInput, workspace: Path) -> DescribeOutput:
    columns = []
    for column in Column:
        values = [row[column.value] for row in ROWS]
        if column.value in NUMERIC:
            columns.append(ColumnInfo(name=column, numeric=True, values=[str(min(values)), str(max(values))]))
        elif column.value == "date":
            columns.append(ColumnInfo(name=column, numeric=False, values=[min(values), max(values)]))
        else:
            columns.append(ColumnInfo(name=column, numeric=False, values=sorted(set(values))))
    return DescribeOutput(rows=len(ROWS), columns=columns)


def count_rows(value: CountInput, workspace: Path) -> CountOutput:
    return CountOutput(count=len(select(value.filters)))


def group_count(value: GroupInput, workspace: Path) -> GroupOutput:
    return GroupOutput(groups=[Group(value=key, count=count) for key, count in groups(value.group_by.value, value.filters)])


def column_stat(value: StatInput, workspace: Path) -> StatOutput:
    rows = select(value.filters)
    if not rows and value.stat != Stat.SUM:
        raise ValueError(f"no crash meets the filters, so it has no {value.stat.value}")
    numbers = [row[value.column.value] for row in rows]
    return StatOutput(value=float(STATS[value.stat](numbers)), rows=len(rows))


def _where(*conditions):
    return [Filter(column=Column(column), op=Op(op), value=str(wanted)) for column, op, wanted in conditions]


def _number(value, tolerance=0.0):
    return AnswerKeyOutput(kind=AnswerKind.NUMBER, number=float(value), tolerance=tolerance, accepted=[])


def _top(counts):
    best = max(counts.values())
    return AnswerKeyOutput(kind=AnswerKind.CATEGORY, number=0.0, tolerance=0.0,
                           accepted=sorted(key for key, count in counts.items() if count == best))


def _answer(question):
    rows = select
    match question:
        case Question.RAIN_ON_I45:
            return _number(len(rows(_where(("road", "eq", "I-45"), ("weather", "eq", "rain")))))
        case Question.WORST_ROAD:
            severe = rows(_where(("severity", "ne", "none"), ("severity", "ne", "minor")))
            return _top(Counter(row["road"] for row in severe))
        case Question.NIGHT_VEHICLES:
            return _number(statistics.fmean(row["vehicles"] for row in rows(_where(("lighting", "eq", "night")))), 0.01)
        case Question.WEEKEND_HOUR:
            weekend = [row for row in ROWS if row["weekday"] in ("Saturday", "Sunday")]
            return _top(Counter(str(row["hour"]) for row in weekend))
        case Question.BIG_CRASH_INJURIES:
            return _number(sum(row["injuries"] for row in rows(_where(("vehicles", "ge", 3)))))
        case Question.FATAL_FOG_BW8_NIGHT:
            conditions = (("severity", "eq", "fatal"), ("weather", "eq", "fog"), ("road", "eq", "BW-8"),
                          ("lighting", "eq", "night"))
            return _number(len(rows(_where(*conditions))))
        case Question.RISKIEST_WEATHER:
            totals = Counter(row["weather"] for row in ROWS)
            hurt = Counter(row["weather"] for row in ROWS if row["injuries"] >= 1)
            shares = {weather: hurt[weather] / totals[weather] for weather in totals}
            best = max(shares.values())
            return AnswerKeyOutput(kind=AnswerKind.CATEGORY, number=0.0, tolerance=0.0,
                                   accepted=sorted(w for w, share in shares.items() if share == best))
        case Question.BW8_MEDIAN_HOUR:
            return _number(statistics.median(row["hour"] for row in rows(_where(("road", "eq", "BW-8")))), 0.01)
        case Question.I10_INJURY_WEEKDAY:
            return _top(Counter(row["weekday"] for row in rows(_where(("road", "eq", "I-10"), ("injuries", "ge", 1)))))
        case Question.NIGHT_PERCENT:
            night = len(rows(_where(("lighting", "eq", "night"))))
            return _number(100 * night / len(ROWS), 0.05)


def answer_key(value: QuestionInput, workspace: Path) -> AnswerKeyOutput:
    return _answer(value.question)
