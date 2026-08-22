# MM-004 multimodal hard-negative data generation protocol v1

## Outcome

The deterministic, model-free generation protocol was frozen before any
generation output existed. Its canonical 10,522-byte preregistration is
`configs/mm004_multimodal_hard_negative_data_generation_v1.json`, with
SHA-256
`c49e18ec570ff198dfa564fdb711b3ba45cf34e5934a9cb667e6a62e13a07ceb`.

The protocol precomputed expected bytes and receipts in memory without
materializing them. PR #45 later merged the exact preregistration, generation
contract, runner, and parent protocol sources as
`2d41b99e7e984975056f7e1088e768cd8a62b744`; that commit became the formal
execution freeze commit.

## Frozen construction plan

- seed: `44004`
- categories: the exact seven frozen MM-004 categories
- families: 28, with four families per category
- split: three train families and one validation family per category
- pairs: 28 atomic clean/hard-negative pairs
- records: 56 total, 42 train and 14 validation
- images: 28 unique deterministic synthetic PNG scenes
- planned outputs: 31 files, including images, two datasets, and one manifest
- network, ML dependencies, real capture, and retries: prohibited

Each clean/negative pair shares its family, instruction, observation, image,
category, and split. The candidate action differs semantically: the clean
candidate follows the category-specific evidence rule, while the negative
candidate implements the registered failure mutation. Content identities,
split isolation, upstream exclusions, and image receipts are validated by the
already frozen parent contract.

## Freeze boundary

Formal materialization must run from `master` with `HEAD == origin/master ==`
the supplied 40-hex freeze commit. The runner compares the preregistration and
every protocol source against `git show <freeze-commit>:<path>` before writing.
Outputs are built in a unique staging directory and atomically renamed to the
fixed fixture root. Existing output roots are rejected.

This is stronger than recording a seed alone: source code, parent protocol,
every planned output path, byte count, and SHA-256 are frozen before execution.

## Formal execution result

The formal invocation ran from `master == origin/master ==`
`2d41b99e7e984975056f7e1088e768cd8a62b744` with zero internal retries. It
atomically materialized the exact 31 planned fixture files under
`fixtures/mm004_hard_negative_v1`:

- 28 deterministic, unique PNGs
- 28 families and 28 atomic clean/hard-negative pairs
- 56 records: 42 train and 14 validation
- `train.json`: 86,330 bytes
- `validation.json`: 29,397 bytes
- `manifest.json`: 8,016 bytes
- total fixture payload: 127,336 bytes

The canonical 9,425-byte evidence is
`baseline/mm004-multimodal-hard-negative-data-generation-v1.json`, with
SHA-256
`0c79a89f8f2431640e4c91d9957af978775e54f2360c15eb67b97a89bb60b133`.
It binds the preregistration, exact freeze commit, all 31 actual receipts, all
13 required gates, the validated summary, and the narrow execution claims.

## Validation evidence at freeze

Twelve focused tests cover deterministic preregistration, claim/source tamper,
exact category and split distributions, meaningful clean/negative mutations,
unique PNGs, single-byte output drift, evidence reseal attempts, atomic and
exclusive materialization, merged-master enforcement, and the absence of
model/network imports. Ruff and scoped strict mypy pass.

The freeze-era unified offline gate reconstructed all 31 planned outputs in
memory and required the fixture/evidence paths to be absent. PR #45 CI passed
633 tests with four expected Windows privilege skips and 52 audited source
files on its Python 3.11/3.12/3.13 matrix.

## Validation evidence after execution

Fourteen focused tests now include reconstruction of the tracked outputs and
evidence. Ruff 0.15.22 passes; scoped strict Mypy 2.3.0 reports no issues in the
typed generation contract/runner; `py_compile` and preregistration `--check`
pass. The unified offline gate passes on local CPython 3.11.15, 3.12.13, and
3.13.7. Every run reports 635 tests, four expected Windows privilege skips, 52
audited source files, `valid=true`, 31 output files, 127,336 output bytes, and
the same evidence digest.

## Claims that remain false

Generation executed and the synthetic records, split, and dataset receipts are
validated. No verifier or model was evaluated, no model was trained, and no
quality, safety, real-content, serving, promotion, or Runtime eligibility claim
is established.

The next gate is
`MM-004-multimodal-hard-negative-model-evaluation-protocol-v1`, which must be
frozen before any model execution.
