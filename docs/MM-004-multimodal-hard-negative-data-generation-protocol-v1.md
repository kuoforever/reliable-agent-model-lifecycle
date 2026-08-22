# MM-004 multimodal hard-negative data generation protocol v1

## Outcome

The deterministic, model-free generation protocol is frozen before any
generation output exists. Its canonical 10,522-byte preregistration is
`configs/mm004_multimodal_hard_negative_data_generation_v1.json`, with
SHA-256
`c49e18ec570ff198dfa564fdb711b3ba45cf34e5934a9cb667e6a62e13a07ceb`.

The protocol precomputes expected bytes and receipts in memory but does not
materialize them. Formal execution requires the merged `master` commit that
contains the exact preregistration, generation contract, runner, and parent
protocol sources.

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

## Validation evidence at freeze

Twelve focused tests cover deterministic preregistration, claim/source tamper,
exact category and split distributions, meaningful clean/negative mutations,
unique PNGs, single-byte output drift, evidence reseal attempts, atomic and
exclusive materialization, merged-master enforcement, and the absence of
model/network imports. Ruff and scoped strict mypy pass.

The unified offline gate also reconstructs all 31 planned outputs in memory
and requires the fixture/evidence paths to be absent at freeze. It passes on
CPython 3.11.15, 3.12.12, and 3.13.7; each run reports 633 tests, four expected
Windows privilege skips, 53 audited source files, and `valid=true`.

## Claims that remain false

Generation has not executed. No records, dataset, split, or execution evidence
exists. No verifier or model was evaluated, no model was trained, and no
quality, safety, real-content, serving, promotion, or Runtime eligibility claim
is established.

The next gate is
`MM-004-multimodal-hard-negative-data-generation-execution-v1`, which may run
only after this protocol is merged.
