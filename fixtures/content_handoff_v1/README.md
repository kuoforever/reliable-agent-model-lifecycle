# Content handoff v1 producer example

`append_text.json` is copied from Runtime `tests/fixtures/content_handoff_v1.json`.
SHA-256: `f999de9fe32a555c512de553137585eec1d3a4727e6793ed8e2a3c475e4d589c`.
Both cases are synthetic, with no model request or application execution.

Only each `candidate` object is a producer payload. Profile, source bodies,
initial document and external factual-review decision belong to trusted Host
code, not model output. Never serialize the entire fixture as a model proposal.
Runtime owns `computer_use_agent.content_handoff` and `docs/CONTENT_HANDOFF.md`.
The JSON format supports append-only plain text, not arbitrary task execution.

The first profile targets a browser-summary/document scenario with a 900-character
content cap; the second demonstrates local-note reuse without a browser or fixed
summary format. The Runtime tests replay both profiles and reject mutated content,
unbound sources/targets, forged review fields and incomplete result observations.
The fixtures do not establish a qualified summary producer or Word integration.

The producer supplies source IDs/digests, target/initial-body binding, exact text
and expected complete final-body digest. Host review binds the canonical entire
candidate using `candidate_digest`; this helper itself does not approve anything.
Runtime rejects drift after review, and returns inert `BoundContentTask` data.
Real source capture, factual approval, observation freshness, save/reopen evidence
and all policy/approval/WAL/dispatch controls remain outside producer authority.
