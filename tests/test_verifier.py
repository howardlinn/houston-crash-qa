from __future__ import annotations

from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import (
    TASKS,
    TOOLS,
    AnswerKeyOutput,
    CountInput,
    DescribeInput,
    GroupInput,
    Question,
    QuestionInput,
    StatInput,
    Task,
    Tool,
)
from plugin import answer_key, column_stat, count_rows, describe_dataset, group_count


# The verifier gets contract instances, as NanoAgent's sandbox builds them from JSON.
def verify_input(tool: str, value: dict) -> dict:
    return verifier.verify_input(tool, build_output(value, TOOLS[Tool(tool)][0]))


def verify_output(tool: str, given: dict, made: dict, workspace: Path) -> dict:
    classes = TOOLS[Tool(tool)]
    return verifier.verify_output(tool, build_output(given, classes[0]), build_output(made, classes[1]), str(workspace))


def key(question: Question, workspace: Path) -> AnswerKeyOutput:
    made = answer_key(QuestionInput(question=question), workspace)
    return build_output(plain_output(made), AnswerKeyOutput)


def answer(question: Question, text: str, workspace: Path, pinned="key") -> dict:
    given, made = TASKS[Task.ANSWER_QUESTION]
    reference = key(question, workspace) if pinned == "key" else pinned
    return verifier.verify_task("answer-question", build_output({"question": question.value}, given),
                                build_output({"answer": text}, made), reference, str(workspace))


def where(*conditions: tuple[str, str, str]) -> list[dict]:
    return [{"column": column, "op": op, "value": value} for column, op, value in conditions]


@pytest.mark.parametrize(
    ("question", "text"),
    [
        (Question.RAIN_ON_I45, "15"),
        (Question.RAIN_ON_I45, " 15 "),
        (Question.WORST_ROAD, "I-610"),
        (Question.WORST_ROAD, "i-610."),  # case and a trailing period do not matter
        (Question.NIGHT_VEHICLES, "2.66"),  # 2.6567..., within 0.01
        (Question.NIGHT_VEHICLES, "2.657"),
        (Question.WEEKEND_HOUR, "16"),
        (Question.WEEKEND_HOUR, "16:00"),
        (Question.BIG_CRASH_INJURIES, "201"),
        (Question.FATAL_FOG_BW8_NIGHT, "0"),  # the right answer is zero
        (Question.RISKIEST_WEATHER, "clear"),
        (Question.BW8_MEDIAN_HOUR, "13"),
        (Question.I10_INJURY_WEEKDAY, "Saturday"),
        (Question.NIGHT_PERCENT, "33.5%"),
        (Question.NIGHT_PERCENT, "33.5"),
    ],
)
def test_accepts_right_answers(tmp_path: Path, question: Question, text: str) -> None:
    assert answer(question, text, tmp_path)["valid"] is True


@pytest.mark.parametrize(
    ("question", "text"),
    [
        (Question.RAIN_ON_I45, "16"),  # off by one
        (Question.RAIN_ON_I45, "fifteen"),  # not a number
        (Question.NIGHT_VEHICLES, "2.64"),  # just outside the tolerance
        (Question.NIGHT_VEHICLES, "3"),  # rounded too far
        (Question.WORST_ROAD, "US-59"),  # the road with the most crashes overall, not the most severe
        (Question.WEEKEND_HOUR, "17"),
        (Question.FATAL_FOG_BW8_NIGHT, "1"),  # dropped a filter: there is 1 fatal crash in fog overall
        (Question.RISKIEST_WEATHER, "fog"),
        (Question.NIGHT_PERCENT, "0.335"),  # a fraction, not a percentage
        (Question.WORST_ROAD, "   "),  # blank
        (Question.WORST_ROAD, "I-610 or I-45"),  # hedging
    ],
)
def test_rejects_wrong_answers(tmp_path: Path, question: Question, text: str) -> None:
    assert answer(question, text, tmp_path)["valid"] is False


def test_a_tie_accepts_every_tied_value(tmp_path: Path) -> None:
    tie = build_output({"kind": "category", "number": 0.0, "tolerance": 0.0, "accepted": ["I-10", "I-45"]},
                       AnswerKeyOutput)
    assert answer(Question.WORST_ROAD, "I-10", tmp_path, tie)["valid"] is True
    assert answer(Question.WORST_ROAD, "I-45", tmp_path, tie)["valid"] is True
    assert answer(Question.WORST_ROAD, "BW-8", tmp_path, tie)["valid"] is False


def test_rejects_a_verdict_without_a_reference(tmp_path: Path) -> None:
    assert answer(Question.RAIN_ON_I45, "15", tmp_path, None)["valid"] is False


def test_the_tools_reach_every_answer(tmp_path: Path) -> None:
    # The answer key is reachable with the agent's own tools: a few questions worked the agent's way.
    rain = count_rows(build_output({"filters": where(("road", "eq", "I-45"), ("weather", "eq", "rain"))}, CountInput),
                      tmp_path)
    assert rain.count == key(Question.RAIN_ON_I45, tmp_path).number
    severe = where(("severity", "ne", "none"), ("severity", "ne", "minor"))
    roads = group_count(build_output({"group_by": "road", "filters": severe}, GroupInput), tmp_path)
    assert [roads.groups[0].value] == key(Question.WORST_ROAD, tmp_path).accepted
    night = build_output({"column": "vehicles", "stat": "mean", "filters": where(("lighting", "eq", "night"))}, StatInput)
    assert column_stat(night, tmp_path).value == pytest.approx(key(Question.NIGHT_VEHICLES, tmp_path).number)
    injuries = build_output({"column": "injuries", "stat": "sum", "filters": where(("vehicles", "ge", "3"))}, StatInput)
    assert column_stat(injuries, tmp_path).value == key(Question.BIG_CRASH_INJURIES, tmp_path).number


@pytest.mark.parametrize(
    "filters",
    [
        where(("road", "eq", "I-99")),  # no such road
        where(("road", "gt", "I-45")),  # ordering a category
        where(("vehicles", "ge", "three")),  # not a whole number
        where(("hour", "lt", "7.5")),
        where(("date", "eq", "01/05/2025")),
        where(("weather", "eq", "Rain")),  # values are case-sensitive, as the dataset spells them
    ],
)
def test_rejects_malformed_filters(filters: list[dict]) -> None:
    assert verify_input("count_rows", {"filters": filters})["valid"] is False
    assert verify_input("group_count", {"group_by": "road", "filters": filters})["valid"] is False


def test_accepts_well_formed_filters() -> None:
    filters = where(("road", "eq", "I-45"), ("vehicles", "ge", "3"), ("date", "ne", "2025-03-01"))
    assert verify_input("count_rows", {"filters": filters})["valid"] is True


def test_count_output(tmp_path: Path) -> None:
    given = {"filters": where(("weather", "eq", "fog"))}
    made = plain_output(count_rows(build_output(given, CountInput), tmp_path))
    assert verify_output("count_rows", given, made, tmp_path)["valid"] is True
    assert verifier.verify_task("count-rows", build_output(given, CountInput),
                                build_output(made, TASKS[Task.COUNT_ROWS][1]), None, str(tmp_path))["valid"] is True
    assert verify_output("count_rows", given, {"count": -1}, tmp_path)["valid"] is False
    assert verify_output("count_rows", given, {"count": 401}, tmp_path)["valid"] is False
    assert verify_output("count_rows", {"filters": []}, {"count": 399}, tmp_path)["valid"] is False


def test_group_output(tmp_path: Path) -> None:
    given = {"group_by": "weather", "filters": []}
    made = plain_output(group_count(build_output(given, GroupInput), tmp_path))
    assert verify_output("group_count", given, made, tmp_path)["valid"] is True
    flipped = {"groups": list(reversed(made["groups"]))}
    assert verify_output("group_count", given, flipped, tmp_path)["valid"] is False
    invented = {"groups": [*made["groups"], {"value": "snow", "count": 1}]}
    assert verify_output("group_count", given, invented, tmp_path)["valid"] is False


def test_stat_output(tmp_path: Path) -> None:
    given = {"column": "hour", "stat": "median", "filters": where(("road", "eq", "BW-8"))}
    made = plain_output(column_stat(build_output(given, StatInput), tmp_path))
    assert verify_output("column_stat", given, made, tmp_path)["valid"] is True
    assert verify_output("column_stat", given, made | {"value": 25.0}, tmp_path)["valid"] is False
    assert verify_output("column_stat", given, made | {"rows": 0}, tmp_path)["valid"] is False


def test_tools_refuse_impossible_queries(tmp_path: Path) -> None:
    none = build_output({"column": "hour", "stat": "mean", "filters": where(("road", "eq", "I-45"), ("road", "eq", "I-10"))},
                        StatInput)
    with pytest.raises(ValueError, match="no crash"):
        column_stat(none, tmp_path)
    with pytest.raises(ValueError, match="eq or ne"):
        count_rows(build_output({"filters": where(("road", "lt", "I-45"))}, CountInput), tmp_path)


def test_describe_output(tmp_path: Path) -> None:
    given = {"dataset": "houston-crashes-2025h1"}
    made = plain_output(describe_dataset(build_output(given, DescribeInput), tmp_path))
    assert verify_output("describe_dataset", given, made, tmp_path)["valid"] is True
    assert verify_output("describe_dataset", given, made | {"rows": 10}, tmp_path)["valid"] is False
