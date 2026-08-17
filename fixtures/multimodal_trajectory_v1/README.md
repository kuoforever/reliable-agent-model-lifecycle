# MM-001 multimodal trajectory v1 fixtures

`valid/text-only.json` and `valid/image-grounded.json` use the same v1 record
topology. They contain only synthetic content-address-shaped references, not
artifact payloads, screenshots, real user tasks, model transcripts, tool-result
bodies, secrets, memory, continuation, cooperative control, or authority
handoff data.

The text fixture grounds a candidate on UIA and document-text references. The
image fixture uses UIA, OCR, and redacted image references and includes one
synthetic previous action/result. Both link distinct pre/post observations,
bind the same policy context into the Runtime decision, reserve dispatch
authority for Runtime, and require state-based verifier evidence.

Both fixtures remain `synthetic_only=true`, `dataset_split=unassigned`,
`license_status=pending_review`, `training_eligible=false`, and
`execution_eligible=false`. Real data still requires the separately reviewed
Lane B contract and a later capture implementation.

Saved invalid fixtures pin malformed JSON, duplicate keys, non-finite values,
and missing-field behavior. The focused suite mutates the valid fixtures for
version drift, unknown fields, modality conflicts, broken references, orphan
artifacts, unavailable tools, unsupported bbox/ref grounding, authority and
policy contradictions, verifier incompleteness, and governance overclaims.
