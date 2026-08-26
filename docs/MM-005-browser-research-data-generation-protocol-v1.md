# MM-005 Browser Research data generation protocol v1

## Outcome

The exact Browser Research data preregistration merged through PR #63 as
`9518d5b59fb11dbea237caa17fd245f4dcd5c2db`; PR #64 then closed its
publication status without changing the protocol or generator sources. This
separate `MM-005-browser-research-data-generation-v1` gate freezes the
one-shot, model-free runner before any registered output is materialized.

The canonical protocol is
`configs/mm005_browser_research_data_generation_v1.json`: 64,590 bytes with
SHA-256
`78c60102d042b65e8046523e9c78cc03137bbf3bf8edbb45a0e067bd3e16aa0d`.
It binds the published data-protocol merge commit, four exact data/generation
source receipts, the unchanged 73,476-byte data protocol, and all 139 planned
output receipts totaling 986,989 bytes.

## Frozen execution plan

The plan preserves the existing `seed=55006` grid:

| Measure | Frozen value |
|---|---:|
| Templates / records | 32 / 32 |
| Train / validation records | 24 / 8 |
| Train / validation sources | 51 / 17 |
| Sources / screenshots / source snapshots | 68 / 68 / 68 |
| Output files | 139 |
| Output bytes | 986,989 |
| Internal retries | 0 |

Formal execution requires all of the following:

- the current branch is `master`;
- `HEAD == origin/master ==` the supplied 40-hex generation-protocol freeze
  commit;
- the published data-protocol commit is an ancestor of that freeze commit,
  and its tracked data-protocol bytes still match the current protocol;
- the generation protocol, data protocol, data contract/builder, and
  generation contract/runner exactly match
  `git show <freeze-commit>:<path>`;
- the fixed output root and evidence path are both absent;
- every in-memory output passes the frozen parent-record, exclusion,
  distribution, split-isolation, DOM/page-text/screenshot, PNG, static-source,
  citation, comparison, and freshness checks before writing;
- every file is written exclusively under a unique staging root, followed by
  one same-parent atomic rename of the complete output root;
- the persisted tree contains exactly the 139 registered paths, with no extra
  file, symlink, reparse directory, or path escape;
- all persisted bytes are independently read back and revalidated before the
  execution evidence is created exclusively and atomically.

The runner has no internal retry. A paired-state validator rejects any state
where only the output root or only the evidence exists. Such a partial state
is a failed consumed attempt, not permission to invoke the runner again.

## Freeze state and claims

At this protocol freeze,
`fixtures/mm005_browser_research_v1` and
`baseline/mm005-browser-research-data-generation-v1.json` are absent. No
record, screenshot, static source snapshot, dataset, or evidence was written.
Generation, dataset validation, Environment Adapter/Verifier execution, live
browser/network use, model training/evaluation, quality, safety, prompt-
injection safety, real/external content, capture, Serving, promotion, and all
Runtime claims remain false.

Page content and model output have no instruction or execution authority.
Runtime remains the sole policy, approval, WAL, grounding, budget, recovery,
and desktop-dispatch boundary. No Runtime repository or integration change is
authorized.

## Validation boundary

Seventeen focused adversarial tests cover deterministic protocol
reconstruction, the published-commit binding, source/claim/publication tamper,
exact output semantics, single-byte screenshot drift, missing/extra outputs,
evidence resealing, atomic and exclusive publication, path escape, exact
trees, merged-master and ancestry enforcement, fixed-target absence, and
forbidden browser/network/model imports. Full-repository Ruff, scoped strict
Mypy, `py_compile`, protocol `--check`, and `git diff --check` pass. Local
CPython 3.11.15, 3.12.12, and 3.13.7 each pass the complete unified 828-test
gate with four expected Windows privilege skips, 64 audited source files, and
`valid=true`.

These checks can establish a deterministic one-shot materialization boundary
and exact in-memory reconstruction. They do not establish that generation has
executed, that any dataset exists, or any model, quality, safety, live-browser,
Serving, promotion, cross-machine, or Runtime claim.

## Registered invocation and next gate

Only after this protocol cleanly merges, both feature-branch copies are
deleted, and `master == origin/master == <freeze-commit>`, one invocation may
be made:

```powershell
work/training-env/Scripts/python.exe -I `
  scripts/run_mm005_browser_research_generation.py execute `
  --protocol-freeze-commit <exact-merged-freeze-commit>
```

The immediate registered gate is
`MM-005-browser-research-data-generation-execution-v1`. If and only if that
one-shot execution and independent model-free review pass, the downstream
design gate becomes
`MM-005-browser-research-adapter-verifier-protocol-v1`. The formal invocation
has not occurred at this freeze.
