# FC-MVP-001 FP32 attached remote revision-origin attestation v1

## Outcome

The gate passes with classification
`fp32_attached_github_and_huggingface_hosted_revision_origins_attested`.
Strict offline recomputation derives `remote_revision_origin_attested=true`
for the fixed GitHub and Hugging Face HTTPS service authorities. All ten
registered gates pass and `remaining_blocking_findings=[]`.

This is a hosted-revision origin statement. It does not establish author
identity or signature, a supply-chain signature, a historical transparency
log, cross-machine reproducibility, or any downstream eligibility decision.

## Frozen protocol and tracked evidence

The contract, collector, preregistration, and focused tests were frozen before
the formal observation at commit
`d0f9a6988ef9702c713402bb179d7524e5e12c7f`.

The frozen preregistration is
`configs/tool_router_fp32_attached_remote_revision_origin_attestation_v1.json`:

- bytes: `17,479`;
- SHA-256:
  `0523caa79ab820e4de892e25f7e94e0081c1086e0255e286c6f202bbc382667e`.

The formal evidence is
`baseline/fc-mvp-001-fp32-attached-remote-revision-origin-attestation-v1.json`:

- bytes: `18,348`;
- SHA-256:
  `cdde41aed18e2fecccea1833f16cea4fc808eb5d212376c96f3e2763fcef7cfd`;
- accepted observation time: `2026-08-09T14:34:50.060194Z`.

The evidence binds the exact frozen protocol sources:

| Source | Bytes | SHA-256 |
|---|---:|---|
| Contract | 47,384 | `22e3aa1a3e8d40f44cec9f27a3e9a489586327f52b87e85caae91891ab82d599` |
| Collector | 25,492 | `ba7458a90704cb66edcf1d35d324e9482cfd147df5fe913f85cff4a3af4d0b25` |

The prior manifest and reproducibility evidence remain unchanged at SHA-256
`4125f2eef2a4b8f07015169ac7fb77b830514e053a4624aa703e5f5a64943eb0`
and
`0e0d2174f4723ab42a5c11375cee10a819e32737810f63111d098decc2984044`.
The latter continues to prove only the same-recorded-environment exact
twenty-case raw and compiled replay.

## GitHub hosted-revision binding

The fixed GitHub authority is repository numeric ID `1315085157`, owner ID
`150589656`, and full name
`kuoforever/reliable-agent-model-lifecycle`. The API resolves package commit
`eafd3f646e4ec08dd0a1f76443ccfd416e81fa22` to:

- parent `782906d44dc75c05b91db92a9ed89355af3203f2`;
- tree `175fc22f53392992dc6c6c32093898399702efeb`;
- a complete non-truncated 247-entry recursive tree response.

The selected package closure is exact for `18/18` entries. For every ordinary
blob, the frozen raw bytes reproduce both the manifest SHA-256 and the Git
blob SHA-1 returned by GitHub. The Adapter weight entry is an exact 133-byte
Git LFS pointer with Git blob SHA-1
`db6f62d5d65595819e7b367f9f9c64c530c1cd26`. Its pointer binds:

- oid
  `sha256:efb62471e105b8ef25641200967d447b8cc2f3ff565937bc47193fbf79f4f342`;
- size `17,462,432` bytes.

The fixed Git LFS Batch request at the pinned commit advertises that same oid
and size with one HTTPS download action. The signed download URL and query are
not followed or stored. No Adapter LFS payload is downloaded by this gate.

GitHub reports the package commit as unsigned. This is recorded as
`verified=false` and `reason=unsigned`; it is not converted into an author
identity or signature claim.

## Hugging Face hosted-revision binding

The fixed Hugging Face authority is
`Qwen/Qwen2.5-1.5B-Instruct` at immutable revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. The revision response is public,
ungated, enabled, and contains exactly ten siblings. Nine are package files.

Eight non-LFS package files, totaling `11,504,784` bytes, are read only from
the already authenticated local snapshot. Each independently reproduces its
manifest raw SHA-256 and the Git blob SHA-1 returned by the Hub revision API.

The base weight file is not read or downloaded by this gate. The Hub LFS
metadata directly binds:

- path `model.safetensors`;
- size `3,087,467,144` bytes;
- SHA-256
  `dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee`;
- pointer size `135` bytes;
- Git pointer blob SHA-1
  `9127f71e7314df0064f469223749e5f237e06463`.

These values exactly equal the externally frozen composite manifest. This is
the content-address bridge from the hosted revision metadata to the exact
package bytes; a successful prior download or manifest match alone was not
accepted as origin evidence.

## Collection and validation boundary

The one accepted formal observation performs five fixed HTTPS metadata
requests with the system CA store and hostname verification. It uses no
alternate repository or revision and performs no automatic request retry.
Collection records:

- `network_used=true` only for metadata collection;
- `model_or_adapter_lfs_downloaded=false`;
- `large_lfs_payload_bytes_read=0`;
- `model_loaded=false` and `generation_calls=0`;
- `package_bytes_written=false`;
- `raw_response_bodies_stored=false`;
- `lfs_signed_url_or_query_stored=false`.

The tracked artifact contains only sanitized authority projections. Offline
validation authenticates both raw artifact hashes, the freeze commit, exact
protocol source hashes, prior artifacts, all remote identities, all selected
tree/file identities, both content-binding sets, all gates, the classification,
and every fail-closed claim.

The unified offline gate passes `379` tests with `valid=true` and audits 33
source files on local CPython 3.12.12, 3.12.13, and 3.13.7. The clean
pull-request CI matrix independently passes the same gate on CPython 3.11.15,
3.12.13, and 3.13.14. The 28 focused tests, Ruff, strict mypy on the new typed
contract/collector scope, `py_compile`, and `git diff --check` pass.

## Decision boundary and next gate

The gate closes the prior `remote_revision_origin_unverified` blocker. It does
not automatically grant offline-artifact, portable-package, preferred-candidate,
serving, promotion, merged-artifact, or Runtime eligibility; every one remains
false. It also does not claim cross-machine, cross-driver, or cross-library
behavioral portability.

The single next objective is
`FC-MVP-001-fp32-attached-offline-artifact-eligibility-reassessment-v1`:
reassess eligibility from the completed metadata, clean-location replay, and
hosted-origin evidence without inferring preferred-candidate, promotion,
serving, or Runtime readiness.
