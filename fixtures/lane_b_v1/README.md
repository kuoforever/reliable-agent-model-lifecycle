# Lane B v1 consent/capture/security review fixtures

## Scope

`valid/minimal-bundle.json` is a synthetic, content-reference-only review
fixture for `FC-BRIDGE-003`. It contains no screenshot bytes, user task,
secret, model transcript, tool-result body, memory, continuation, cooperative
control record, or authority handoff. The nine artifact identifiers are
synthetic SHA-256-shaped references, not retained rich content.

The fixture binds three separately versioned records:

1. one explicit, run-scoped operator consent with a visible indicator,
   bounded application scope, retention deadline, and delete-on-request;
2. one quarantine-stage episode whose candidate action has no execution
   authority and whose Runtime decision remains the only dispatch authority;
3. one synthetic deletion receipt that covers every artifact reference and
   reports zero retained artifacts.

The valid fixture remains `quarantine_review_only`, with `dataset_split` set to
`unassigned`, `license_status` set to `pending_review`, and
`training_eligible=false`. It proves the contract and validator behavior only.
It does not prove a capture adapter, real sanitization or image redaction,
storage enforcement, real deletion, dataset licensing, model training,
Runtime integration, or deployment.

## Fail-closed fixtures

| Fixture | Expected error |
|---|---|
| `invalid/unknown-version.json` | `UNSUPPORTED_VERSION` |
| `invalid/unexpected-field.json` | `UNKNOWN_FIELD` |
| `invalid/missing-consent.json` | `MISSING_FIELD` |
| `invalid/malformed.json` | `MALFORMED_JSON` |

The unit suite additionally mutates the valid fixture to cover consent reuse,
wildcard scope, retention drift, unredacted images, automatic Runtime export,
model authority, dispatch-policy contradictions, broken artifact bindings,
model self-report, incomplete deletion, unsafe files, duplicate JSON keys,
and non-finite numbers without storing redundant full invalid bundles.

## 中文边界

这是纯 synthetic contract review fixture，不含真实截图、用户任务、secret、
模型正文或工具结果正文。它验证显式同意、单次 session、独立存储、写前脱敏/
遮罩声明、content-address binding、Runtime authority、state verifier 与删除回执
之间的关系。它不代表 capture adapter、真实删除、数据许可、训练或 Runtime 接入
已经实现。
