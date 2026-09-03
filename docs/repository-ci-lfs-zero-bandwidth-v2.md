# Repository CI/LFS zero-bandwidth maintenance v2

## Objective

`repository-ci-lfs-zero-bandwidth-v2` keeps pull-request publication fail-closed
after the repository owner's monthly Git LFS bandwidth has been exhausted. It
does not download or upload an LFS payload in automatic CI. Instead, automatic
CI inherits immutable payload content identity from one successful hydrated
anchor and rejects any descendant whose LFS control plane or pointer inventory
drifts.

This is a bounded CI maintenance detour. It changes no model, Adapter, tensor,
dataset, Runtime contract, diagnostic identity, output, lease, authority,
invocation budget, or result claim. It does not run a diagnostic.

## Immutable hydrated anchor

The trust anchor is exact merge HEAD
`eb2aea3ca1eb5d82e823f7fc7a6aac7b5beb3fc9`, tree
`bddfdadcc650b6ac94787ea2bfbb0e2f2f09a77d`. GitHub Actions workflow run
`33501136645`, hydrated job `99834499141`, completed successfully at that
commit under the `hydrated-lfs-integrity` context. The job began from a
pointer-only checkout, pulled exactly the four registered LFS paths, ran
`git lfs fsck --objects --pointers HEAD`, streamed all 110,524,520 payload
bytes through the frozen SHA-256/size validator, and then ran the complete
offline integrity gate.

The canonical
[`repository_ci_lfs_trust_anchor_v1.json`](../configs/repository_ci_lfs_trust_anchor_v1.json)
records that commit, tree, run, job, protected path set, automatic evidence
boundary, manual trigger, and diagnostic-v2 focused-test topology. The existing
`repository_ci_lfs_inventory_v1.json` remains byte-for-byte frozen.

## Automatic required gates

The three required `python-matrix (3.11/3.12/3.13)` jobs continue to use a
full-history pointer-only checkout with LFS smudge disabled. Each runs the
existing exact pointer/attribute inventory, tracked-Python compilation, and
107 standard-library core tests. Each then runs the diagnostic-v2 focused
gate:

- with all four implementation-v2 files absent, exactly the 18 anchor protocol
  tests run;
- with all four implementation-v2 files present, the implementation's exact 19
  protocol tests plus 43 result tests run, for 62 total;
- any one-to-three-file partial implementation topology fails closed.

The fourth required context retains the historical name
`hydrated-lfs-integrity` solely for ruleset compatibility. Its automatic
meaning is now `immutable_hydrated_anchor_and_pointer_no_drift`. It proves all
of the following without reading a payload:

1. the exact anchor commit exists and resolves to the frozen tree;
2. the anchor is an ancestor of current `HEAD`;
3. `.gitattributes`, the frozen inventory, and all four 133-byte pointer blobs
   have no content or mode drift from the anchor;
4. the only tracked attribute-control file remains root `.gitattributes`;
5. no tracked `.lfsconfig` exists;
6. the current index and pointer-only worktree still expose exactly the four
   registered LFS paths, OIDs, sizes, blob IDs, and attributes.

The automatic workflow contains no `git lfs pull`, LFS fsck, hydrated payload
validator, or complete `validate_offline.py` invocation. Its machine-readable
summary therefore states, truthfully:

```text
content_identity_inherited=true
current_hydration_verified=false
current_payload_integrity_verified=false
remote_availability_verified=false
full_integrity_verified=false
lfs_payload_bytes_read=0
```

SHA-256 content addressing plus protected no-drift allows the intended payload
identity to be inherited from the successful anchor. It does not prove that
GitHub can serve those objects now, that billing permits a current download, or
that a complete current-HEAD offline gate ran remotely.

## Explicit manual hydration

The separate `manual hydrated LFS integrity` workflow has only a
`workflow_dispatch` trigger and emits the distinct
`manual-hydrated-lfs-integrity` context. It cannot replace or mask the required
automatic context. Before checkout it requires this exact acknowledgement:

```text
DOWNLOAD 110524520 LFS BYTES
```

Only after that acknowledgement does it check out pointer-only, validate the
pointer metadata, pull exactly the four registered paths, fsck their objects,
hash all 110,524,520 bytes, and run the complete offline gate. It must not be
dispatched while the monthly bandwidth balance is unavailable. Its concurrency
group queues rather than cancels a prior run, preventing overlap and preserving
the first run's evidence. A second dispatch still downloads again when it
eventually starts and must be cancelled manually if it was accidental.

## Security and evidence boundary

Pointer-only success establishes current Git metadata, attribute policy,
pointer bytes, content IDs, Python syntax, the 107 core tests, and the frozen
diagnostic-v2 focused suite. The ancestor/no-drift proof transfers the anchor's
payload *identity*, not current remote availability. A missing remote object,
an unavailable billing allowance, historical Actions-log retention, or a
server-side retrieval failure remains undetected until the explicit manual
workflow or another hydrated consumer reads the bytes.

The automatic workflow and its validator remain branch-controlled code, as in
the previous design. Required review, thread resolution, strict up-to-date
merging, signed commits, exact status contexts, and no-bypass rules remain part
of the publication boundary. Any future change to an LFS pointer, attribute
controller, inventory, endpoint configuration, or anchor requires a separate
reviewed maintenance protocol and a fresh successful manual hydrated
observation; it must not silently weaken this gate.

## Paused formal lifecycle gate and resume point

The implementation-v2 product slice is paused, not abandoned. Its safe local
resume point is `C:\Users\Alienware\raml-v2i`, branch
`feat/mm005-generation-failure-diagnostic-implementation-v2`, based on
`eb2aea3ca1eb5d82e823f7fc7a6aac7b5beb3fc9`, with exactly 11 intended paths.
This maintenance is only a repository-CI transport prerequisite. Its `gate_id`
does not consume, replace, or advance the protocol's formal lifecycle
`next_gate`; implementation-v2 remains that next gate throughout the detour.
After this maintenance is independently validated, published, and observed on
merge HEAD, implementation-v2 must be rebased onto that clean master and add a
literal `IMPLEMENTATION_BASE_COMMIT` binding to the maintenance merge commit
within its already registered 11-path slice. The protocol commit remains the
receipt and ancestor; the maintenance merge must be the implementation's unique
first parent, and the base-to-implementation delta must remain exactly those 11
paths before publication.

Execution-authority-v2 and exact-once execution-v2 remain later, separate
gates. Neither this maintenance nor implementation-v2 may publish authority,
create a formal output parent, cross the model/CUDA/network boundary, or invoke
the diagnostic.
