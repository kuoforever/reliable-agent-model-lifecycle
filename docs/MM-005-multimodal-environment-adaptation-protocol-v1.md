# MM-005 multimodal environment-adaptation protocol v1

## Outcome

`MM-005-multimodal-environment-adaptation-protocol-v1` freezes the next
model-free environment boundary before any new data generation, model call,
training, capture, or Runtime integration. The registered environment order is:

1. Desktop GUI
2. Document / Chart / PDF
3. Browser Research
4. Audio / Video
5. Robotics / Autonomous Driving Simulation (optional)

The existing MM-001 through MM-004 chain closes a synthetic Desktop GUI depth
slice without Runtime deployment. The next environment is therefore
`document_chart_pdf`; skipping directly to a later environment is prohibited.

The frozen artifact is
`configs/mm005_multimodal_environment_adaptation_protocol_v1.json`: 49,202
canonical bytes with SHA-256
`311822603bb6c05c1b7f388cd782c30556fa8b7aa0d67cbd1ccd89f9d13a532a`.

## Bounded first vertical slice

The selected scope is synthetic, English, single-page visual evidence
grounding. It includes rendered text, tables, bar charts, single-page PDF
rendering, and exact answer-to-region evidence references. It defines four task
families:

- `document_text_evidence_grounding`
- `table_cell_evidence_grounding`
- `chart_value_evidence_grounding`
- `page_region_selection`

The next data protocol must use one page image plus sanitized synthetic layout
ground truth. It may not claim Runtime OCR or ingest a real file path. Multi-page
documents, scanned/noisy OCR, handwriting, real user or external documents,
Browser Research, Audio/Video, robotics/autonomous-driving simulation, and tool
or desktop execution remain deferred.

Counts and generation seed are intentionally absent. They belong to the next
gate, `MM-005-document-chart-pdf-data-protocol-v1`, so scope review cannot be
silently converted into data production.

## Four-component environment delta

| New environment component | Frozen responsibility |
|---|---|
| Environment Adapter | Project a document-page record into model input and compile a strict JSON answer |
| Task set | Define the four task families and compatible synthetic source kinds |
| Deterministic Verifier | Compare normalized answer, exact ordered evidence refs, and page number without an LLM judge |
| Synthetic dataset | Provide future train/validation records under the frozen record and provenance contract |

Training orchestration, evaluation lifecycle, Serving/model routing, policy,
approval, WAL, grounding authority, budgets, recovery, and desktop dispatch are
inherited and must not be duplicated per environment.

## Adapter and record interface

The Adapter receives `instruction`, `observation`, `task_family_id`, and
`source_kind`. Gold/verifier fields and real file paths are never exposed as
model input. Candidate output is a strict JSON object with exactly:

```json
{"answer":"...","evidence_refs":["region-ref"],"page_number":1}
```

Extra keys, duplicate JSON keys, malformed/non-finite/oversized output,
non-unique refs, and any page other than `1` compile to a deterministic invalid
result and score wrong.

Each future record binds:

- a domain-separated local `family_id` from task family, source kind, and
  template;
- a domain-separated local `record_id` over the complete record body;
- shared cross-stage content SHA-256 identities for instruction, observation,
  and target;
- the exact rendered image SHA-256.

Train and validation must be disjoint by family, template, instruction content,
observation content, target content, and image. All four task families, all four
source kinds, and both splits are mandatory.

## Read-only lineage and leakage exclusions

The protocol reconstructs 63 exact source receipts: 11 protocol, sequencing,
Runtime/capture-boundary, and upstream dataset files plus 52 historical
synthetic PNGs. It recomputes shared cross-stage content identities from the
actual MM-002, MM-003, and MM-004 values rather than trusting their older local
ID schemes.

The frozen exclusion registry contains:

| Identity set | Count |
|---|---:|
| Prior case/record IDs | 92 |
| Prior family IDs | 64 |
| Instruction content hashes | 64 |
| Observation content hashes | 64 |
| Target content hashes | 92 |
| Image hashes | 52 |

Any collision is a hard failure. This makes data reuse visible even when an
upstream stage used a different domain-separated identifier.

## Provenance and Runtime authority

Future data is limited to deterministic, reviewed, repository-generated
synthetic content. Real document collection, external download, Lane A rich
content, Lane B capture, and Runtime OCR claims are false. Capture remains off
and unauthorized.

Model output has no execution authority. The Runtime repository remains the
sole policy, approval, WAL, grounding, budget, recovery, and desktop-dispatch
boundary; this protocol changes neither Runtime code nor integration state.

At this freeze, Adapter implementation, task materialization, dataset
generation/validation, verifier execution, model training/evaluation, quality,
safety, Serving, promotion, capture, and Runtime eligibility claims all remain
false.

## Repeatability and validation meaning

The repeatability target at this gate is protocol and identity repeatability:
the same tracked source bytes must rebuild the same canonical protocol, source
receipts, exclusion sets, content identities, and deterministic verifier
decision. It is not a model-evaluation repeatability claim.

Fourteen focused tests cover byte-exact reconstruction, sequence and scope,
four-component closure, Runtime authority, protocol/record tampering,
family/source/split coverage, deterministic identities, cross-split and prior
content collision, provenance rejection, evidence binding, single-page scope,
and total model-free compilation/verification. Full-repository Ruff, scoped
strict Mypy, `py_compile`, the frozen builder `--check`, and `git diff --check`
pass. Local CPython 3.11.15, 3.12.12, and 3.13.7 each pass the unified 674-test
gate with four expected Windows privilege skips, 54 audited source files, and
`valid=true`.

## Downstream progression

The registered downstream gate was
`MM-005-document-chart-pdf-data-protocol-v1`: it froze deterministic seed,
counts, template families, render constraints, output receipts, validation,
and execution claims before creating any dataset or image. Its separate
one-shot generation gate has since completed. The subsequent
`MM-005-document-chart-pdf-adapter-verifier-protocol-v1` is now frozen; the
current next gate is its separate implementation without model execution or
Runtime change.
