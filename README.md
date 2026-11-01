# Houston Crash Q&A

A NanoAgent plugin with verifiable data questions: an agent answers questions about a table of Houston
freeway crashes by querying it with typed tools, and its answer is checked against an answer key computed
from the same table.

The table is a fixed, **synthetic** dataset of 400 crashes from the first half of 2025 (made-up rows, drawn
from a fixed seed by `src/datagen/make_crashes.py` and committed as `src/plugin/data/crashes.json`), so every
question has one right answer on every computer. Its columns: `date`, `weekday`, `hour`, `road` (I-45, I-10,
US-59, I-610, BW-8), `severity` (none, minor, serious, fatal), `vehicles`, `injuries`, `weather` (clear, rain,
fog) and `lighting` (day, night).

The questions are fixed (`contract.Question`), so the answer key is code. They need more than one query:
an "or" across two values, a ratio of two counts, a filter that makes the answer zero, or a statistic over a
filtered set. A number is right within a stated tolerance (0 for counts, 0.01 for averages and medians,
0.05 for percentages); a category is right when it matches any value tied for first, ignoring case.

## Tools

| Tool | Does | Code |
|---|---|---|
| `describe_dataset` | Describes the table: its size, columns and their values | `src/plugin/crashes.py` |
| `count_rows` | Counts the crashes that meet every filter | `src/plugin/crashes.py` |
| `group_count` | Counts per value of one column, most first | `src/plugin/crashes.py` |
| `column_stat` | Mean, median, sum, minimum or maximum of a numeric column | `src/plugin/crashes.py` |
| `answer_key` | The right answer to a question: the reference, run out of the agent's sight | `src/plugin/crashes.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `count-rows` | Counts the crashes that meet some conditions | `tool`, with `count_rows` |
| `answer-question` | Answers a question about the crashes from the data | `agent`, with `describe_dataset`, `count_rows`, `group_count` and `column_stat`; reference `answer_key` |

## Layout

```text
.
├── nanoagent.yaml   # manifest: id, runtime, permissions, tools, tasks
├── contract.py      # each tool's and task's typed input and output, and the fixed questions
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # needed environment variable names (none)
├── src/plugin/      # the MCP server, the tools (crashes.py) and the bundled data/crashes.json
├── src/datagen/     # make_crashes.py, which generated data/crashes.json from a fixed seed
├── tests/           # test_verifier.py: correct, wrong, missing, malformed and boundary cases
├── ui/              # renderers.js: outputs drawn from their JSON Schema
├── product/         # product.yaml and icon.svg
└── verifier/        # deterministic verifier: crashes.py, on contract instances, standard library only
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

The plugin needs no network and no environment variables.
