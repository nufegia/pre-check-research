# Interpretation Boundaries

`pcr` reports risk signals for human review. It does not determine misconduct, fabrication, fraud, data manipulation, intent, or culpability.

## Preferred Language

Use language such as:

- "This check surfaced an anomalous signal."
- "The evidence suggests a follow-up review of the source data or script."
- "Possible normal explanations include extraction error, rounding, coding choices, or incomplete material."
- "This result should be rerun against the original source file before drawing conclusions."

Avoid language such as:

- "This proves fabrication."
- "The data are fraudulent."
- "The authors manipulated the results."
- "This is misconduct."

## Common Limits

- PDF and DOCX table extraction can introduce parsing errors.
- Image checks are weak-signal triage and should use original images when the review matters.
- Raw-data shape and distribution signals can have normal explanations.
- External metadata lookups depend on third-party services and can be incomplete, rate-limited, or unavailable.
- Script reruns use temporary project copies and timeouts, but they are not a strong security sandbox.
- Missing dependencies, disabled external lookups, unsupported script runtimes, and insufficient material are operational notes, not risk findings.

## Review Pattern

A cautious review note should include:

1. The signal.
2. The evidence path or table row.
3. Plausible non-problematic explanations.
4. The source file or material needed for confirmation.
5. A recommended human review step.
