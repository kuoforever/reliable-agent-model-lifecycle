# Resume evidence index

> **Status: current derived job-application view, reviewed against frozen
> evidence on 2026-08-10.** This is not a final resume or deployment claim.

| ID | Highlight | Strongest evidence scope |
| --- | --- | --- |
| `RAML-01` | [Reliable model-lifecycle vertical slice](RAML-01-lifecycle-architecture.md) | Implemented offline MVP-0/1 path |
| `RAML-02` | [Dataset and frozen evaluation governance](RAML-02-data-eval-governance.md) | Versioned local artifacts and audits |
| `RAML-03` | [LoRA safety repair and decision compilation](RAML-03-lora-safety-compiler.md) | Frozen local training/eval evidence |
| `RAML-04` | [BF16/FP32 numerical drift isolation](RAML-04-numerical-drift.md) | Repeat-stable single-example diagnostic lineage |
| `RAML-05` | [Offline artifact reproducibility and provenance](RAML-05-artifact-reproducibility.md) | Same-environment clean-location evidence |
| `RAML-06` | [Pre-registered evidence engineering](RAML-06-evidence-engineering.md) | Repository-wide gate discipline |

## JD selection

| Target role | Start with | Add when the JD emphasizes |
| --- | --- | --- |
| LLM post-training / applied ML | RAML-02, 03, 01 | RAML-04 for numerical depth |
| AI infrastructure / ML systems | RAML-04, 05, 06 | RAML-01 for system context |
| Evaluation / model quality | RAML-02, 03, 06 | RAML-05 for artifact identity |
| Agent / tool-use modeling | RAML-01, 03, 02 | Link Guarded Desktop Agent separately for Runtime |
| MLOps / reproducibility | RAML-05, 06, 02 | Do not claim serving or rollout |

Select three or four non-overlapping items, confirm personal ownership, and
open all evidence sources before submission. Preferred offline candidate,
portable package, deployment, serving, promotion, and Runtime eligibility are
different states and must never be collapsed into one claim.
