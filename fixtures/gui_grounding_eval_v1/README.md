# GUI grounding evaluation v1 fixtures

`valid/suite.json` is a reviewed synthetic-only nine-case evaluation suite.
Gold labels are stored outside each `model_input`; every record is frozen in
the eval split and prohibited from training use.

`valid/synthetic-probe-predictions.json` deliberately contains correct and
incorrect outputs. It verifies metric sensitivity and is not a model run.

Invalid fixtures pin strict JSON and contract failures. No file contains real
user content, a capture result, training approval, or Runtime execution
authority.
