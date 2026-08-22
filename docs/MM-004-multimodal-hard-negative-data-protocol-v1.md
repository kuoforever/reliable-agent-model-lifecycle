# MM-004 multimodal hard-negative data protocol v1

## Outcome

`MM-004-multimodal-hard-negative-data-protocol-v1` is frozen as a model-free
data-contract gate. It defines how a later generation gate may construct and
validate synthetic clean/hard-negative pairs. It does not contain a generated
dataset and does not authorize training, model evaluation, Runtime changes, or
desktop capture.

The canonical preregistration is
`configs/mm004_multimodal_hard_negative_data_protocol_v1.json`. Its 22,675
canonical UTF-8 bytes have SHA-256
`f31e009ed8316d59240e9767865a041e86f30325a1fd15f8a29891d56d418355`.

## Frozen category taxonomy

The protocol requires coverage of exactly seven reviewed failure categories:

1. `wrong_control_grounding`
2. `observation_conflict`
3. `ignored_post_state`
4. `duplicate_side_effect`
5. `approval_bypass`
6. `tool_failure_false_success`
7. `plausible_without_evidence`

Each future family must contain exactly one `clean` record with an `accept`
verdict and one mutated `hard_negative` record with a `reject` verdict. The
negative must change the observation or candidate action; relabeling an
identical clean record is rejected.

## Identity and leakage boundary

Family, pair, record, instruction, observation, and candidate identities use
domain-separated SHA-256 over canonical JSON. A record ID covers every record
field except the ID itself. The validator recomputes these identities and
fails closed on content drift.

The frozen exclusion registry is derived from 9 MM-002 eval records, 18 MM-003
training records, and 9 MM-003 validation records. It binds 36 case IDs, 36
family IDs, instruction/observation/candidate hashes, and all 24 historical
synthetic image hashes. Future generation must avoid every registered
collision. Clean/negative pairs remain in one split, while family,
instruction, observation, candidate, and image identities must be disjoint
between train and validation.

## Provenance and authority

Only deterministic reviewed synthetic generation is eligible. Real desktop
capture and Lane B rich capture remain prohibited. Lane A may inform verifier
taxonomy only and may not supply rich content. MM-002 gold/eval and the MM-003
Adapter are authenticated read-only evidence; gold may not be copied, the
Adapter may not be modified, and the consumed MM-003 repeatability output may
not be reopened.

Runtime remains the sole policy, approval, WAL, and dispatch boundary. A model
record never has execution authority.

## Validation evidence

The contract, builder, frozen preregistration, and ten focused adversarial
tests validate deterministic rebuilds, claim tampering, record tampering,
pair/split binding, category coverage, upstream collision rejection, verifier
evidence, and real negative mutation. The unified offline gate passes 621 tests
with four expected Windows privilege skips, 51 audited source files, and
`valid=true` on CPython 3.11.15, 3.12.12, and 3.13.7.

## Claims that remain false

No records have been generated; the dataset and splits are not frozen; no
verifier or model has been evaluated; no model has been trained; and no
quality, safety, real-content, serving, promotion, or Runtime eligibility is
established.

The single next gate is
`MM-004-multimodal-hard-negative-data-generation-v1`. That gate must freeze
counts, seed, construction inputs, and output receipts before any generated
records can be accepted.
