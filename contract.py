"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    DESCRIBE_DATASET = "describe_dataset"
    COUNT_ROWS = "count_rows"
    GROUP_COUNT = "group_count"
    COLUMN_STAT = "column_stat"
    ANSWER_KEY = "answer_key"


class Task(Enum):
    COUNT_ROWS = "count-rows"
    ANSWER_QUESTION = "answer-question"


class Dataset(Enum):
    HOUSTON_CRASHES = "houston-crashes-2025h1"


class Column(Enum):
    DATE = "date"
    WEEKDAY = "weekday"
    HOUR = "hour"
    ROAD = "road"
    SEVERITY = "severity"
    VEHICLES = "vehicles"
    INJURIES = "injuries"
    WEATHER = "weather"
    LIGHTING = "lighting"


class NumericColumn(Enum):
    HOUR = "hour"
    VEHICLES = "vehicles"
    INJURIES = "injuries"


class Op(Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GE = "ge"
    LT = "lt"
    LE = "le"


class Stat(Enum):
    MEAN = "mean"
    MEDIAN = "median"
    SUM = "sum"
    MIN = "min"
    MAX = "max"


class Question(Enum):
    RAIN_ON_I45 = "How many crashes happened on I-45 in the rain?"
    WORST_ROAD = "Which road had the most serious or fatal crashes?"
    NIGHT_VEHICLES = "What was the average number of vehicles in night-time crashes?"
    WEEKEND_HOUR = "Which hour of the day had the most crashes on weekends (Saturday and Sunday together)?"
    BIG_CRASH_INJURIES = "How many people were injured in total in crashes involving 3 or more vehicles?"
    FATAL_FOG_BW8_NIGHT = "How many fatal crashes happened on BW-8 in fog at night?"
    RISKIEST_WEATHER = "Which weather condition had the highest share of its crashes with at least one injury?"
    BW8_MEDIAN_HOUR = "What was the median hour of the day of crashes on BW-8?"
    I10_INJURY_WEEKDAY = "On which weekday did the most crashes with at least one injury happen on I-10?"
    NIGHT_PERCENT = "What percentage of all crashes happened at night?"


class AnswerKind(Enum):
    NUMBER = "number"
    CATEGORY = "category"


FILTERS = "Conditions every counted row meets, all at once; empty for every row"


@dataclass
class Filter(Output):
    column: Annotated[Column, "The column to test"]
    op: Annotated[Op, "The comparison: eq, ne for any column; gt, ge, lt, le for hour, vehicles and injuries"]
    value: Annotated[str, "The value to compare with, e.g. I-45, rain, 3"]


@dataclass
class ColumnInfo(Output):
    name: Annotated[Column, "The column"]
    numeric: Annotated[bool, "Whether it holds whole numbers"]
    values: Annotated[list[str], "Its distinct values, sorted; for a numeric column, its smallest and largest"]


@dataclass
class DescribeInput(Output):
    dataset: Annotated[Dataset, "The dataset to describe"]


@dataclass
class DescribeOutput(Output):
    rows: Annotated[int, "How many crashes it holds"]
    columns: Annotated[list[ColumnInfo], "Its columns"]


@dataclass
class CountInput(Output):
    filters: Annotated[list[Filter], FILTERS]


@dataclass
class CountOutput(Output):
    count: Annotated[int, "How many crashes meet every filter"]


@dataclass
class GroupInput(Output):
    group_by: Annotated[Column, "The column to group by"]
    filters: Annotated[list[Filter], FILTERS]


@dataclass
class Group(Output):
    value: Annotated[str, "A value of the grouped column"]
    count: Annotated[int, "How many crashes meeting the filters have it"]


@dataclass
class GroupOutput(Output):
    groups: Annotated[list[Group], "Every value with at least one crash, most crashes first, ties by value"]


@dataclass
class StatInput(Output):
    column: Annotated[NumericColumn, "The numeric column"]
    stat: Annotated[Stat, "The statistic"]
    filters: Annotated[list[Filter], FILTERS]


@dataclass
class StatOutput(Output):
    value: Annotated[float, "The statistic over the crashes meeting the filters, unrounded"]
    rows: Annotated[int, "How many crashes it is over"]


@dataclass
class QuestionInput(Output):
    question: Annotated[Question, "The question about the dataset"]


@dataclass
class AnswerOutput(Output):
    answer: Annotated[str, "The answer alone: a number (e.g. 12 or 2.47), or a value as the dataset spells it (e.g. I-10)"]


@dataclass
class AnswerKeyOutput(Output):
    kind: Annotated[AnswerKind, "Whether the answer is a number or a value of a column"]
    number: Annotated[float, "The right number, unrounded; 0 for a category"]
    tolerance: Annotated[float, "How far a number may be from it and still be right"]
    accepted: Annotated[list[str], "Every right value, more than one on a tie; empty for a number"]


TOOLS = {
    Tool.DESCRIBE_DATASET: (DescribeInput, DescribeOutput),
    Tool.COUNT_ROWS: (CountInput, CountOutput),
    Tool.GROUP_COUNT: (GroupInput, GroupOutput),
    Tool.COLUMN_STAT: (StatInput, StatOutput),
    Tool.ANSWER_KEY: (QuestionInput, AnswerKeyOutput),
}
TASKS = {
    Task.COUNT_ROWS: (CountInput, CountOutput),
    Task.ANSWER_QUESTION: (QuestionInput, AnswerOutput),
}
