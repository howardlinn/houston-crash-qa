"""The deterministic verifier: each tool's checks live in crashes.py, on contract instances."""

from contract import Task, Tool

from . import crashes

INPUTS = {
    Tool.DESCRIBE_DATASET: crashes.verify_describe_input,
    Tool.COUNT_ROWS: crashes.verify_filters_input,
    Tool.GROUP_COUNT: crashes.verify_filters_input,
    Tool.COLUMN_STAT: crashes.verify_filters_input,
    Tool.ANSWER_KEY: crashes.verify_describe_input,
}
OUTPUTS = {
    Tool.DESCRIBE_DATASET: crashes.verify_describe_output,
    Tool.COUNT_ROWS: crashes.verify_count_output,
    Tool.GROUP_COUNT: crashes.verify_group_output,
    Tool.COLUMN_STAT: crashes.verify_stat_output,
    Tool.ANSWER_KEY: crashes.verify_key_output,
}


def _count_rows(arguments, output, reference, workspace):
    return crashes.verify_count_output(arguments, output, workspace)


# task -> its output's check, verify_task(arguments, output, reference, workspace)
TASKS = {
    Task.COUNT_ROWS: _count_rows,
    Task.ANSWER_QUESTION: crashes.verify_answer,
}


def verify_input(tool, value):
    return INPUTS[Tool(tool)](value)


def verify_output(tool, input_value, output_value, workspace):
    return OUTPUTS[Tool(tool)](input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    return TASKS[Task(task)](arguments, output, reference, workspace)
