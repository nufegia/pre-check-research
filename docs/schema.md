# Finding JSON Schema

All detector CLIs should write a top-level payload with:

- `tool_id`
- `tool_name`
- `detector_runtime`
- `dependency_status`
- `source`
- `input_type`
- `findings`

Each item in `findings` should include:

- `level`: `high`, `medium`, `low`, or `info`
- `check`
- `target`
- `summary`
- `evidence`
- `detail`
- `suggestion`
- `meaning`
- `normal_explanations`
- `review_steps`
- `confidence`
- `false_positive_risk`

The machine-readable schema is in `tools/common/schemas/finding.schema.json`.
