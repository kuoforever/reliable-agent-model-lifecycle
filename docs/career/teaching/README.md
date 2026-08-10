# Teaching-oriented collaboration

> **Status: current collaboration contract. Protocol version: `1`.**

| Module | Purpose |
| --- | --- |
| [Step protocol](STEP_PROTOCOL.md) | Before/during/after explanation contract |
| [Evidence discipline](EVIDENCE_DISCIPLINE.md) | Model/data/artifact claim boundaries |
| [Interview translation](INTERVIEW_TRANSLATION.md) | Turning frozen results into defensible narratives |

Prefer Chinese explanations with exact English technical terms, identifiers,
commands, metrics, artifact hashes, and file names.

## Project-specific boundaries

- `PROJECT_STATUS.md` owns the single active objective.
- Introduce one primary variable per experiment stage.
- Freeze evaluation inputs before model comparisons.
- Bind code, data, model, config, seed, hardware, metrics, and failures.
- Keep raw model behavior, decision compilation, Runtime policy, and artifact
  qualification as separate layers.
- Preferred, eligible, reproducible, portable, promoted, served, and
  Runtime-integrated are different states.
- Runtime changes belong in `guarded-desktop-agent`, under that repository's rules.
- Record negative results; never tune a gate after seeing the outcome.
