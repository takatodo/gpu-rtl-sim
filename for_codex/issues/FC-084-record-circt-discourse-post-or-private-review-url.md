# FC-084: Record CIRCT Discourse post or private-review path

Status: open
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/85
Parent: FC-083 / https://github.com/takatodo/gpu-rtl-sim/issues/84
Target files: `docs/circt_batch_state_rfc_posting_package.md`, `docs/circt_batch_state_discourse_body.md`, `docs/status.md`, `docs/roadmap.md`, `README.md`, `config/selection.json`, `for_codex/issues.md`

## Objective

Complete the external execution step for the CIRCT batch-state discussion.

FC-083 selected LLVM Discourse CIRCT category as the recommended first public
route, using `docs/circt_batch_state_rfc_posting_package.md` as the source
material. FC-083 deferred actual posting only because this execution environment
has no confirmed LLVM Discourse account/session/API authority for the project
owner.

## Required Work

Choose exactly one path:

- Post the package to LLVM Discourse CIRCT category and record the public URL.
- Ask a named CIRCT/arcilator maintainer for private pre-review and record the
  reviewer/path plus expected feedback target.
- Defer again, but only with a fresh owner decision or concrete blocker.

## Owner Action Packet

Prepared source material:

- Posting package: `docs/circt_batch_state_rfc_posting_package.md`
- Copy-paste Discourse body: `docs/circt_batch_state_discourse_body.md`
- Suggested venue: LLVM Discourse CIRCT category
  `https://discourse.llvm.org/c/projects-that-want-to-become-official-llvm-projects/circt/40`
- Suggested title:
  `Measured boundary for independent-state batch execution in arcilator/arc`

After posting, record:

- Public Discourse URL.
- Date posted.
- Exact non-claim: public posting does not imply CIRCT endorsement or accepted
  RFC.

If private review is chosen instead, record:

- Reviewer name or handle.
- Contact path.
- Expected feedback target.

If deferred again, record:

- Fresh owner decision or concrete blocker.
- Whether the prepared package remains valid as-is.

## Record Templates

Use one of these exact templates in GitHub #85 and mirror the chosen record back
into this file.

Public Discourse route:

```text
Path: public Discourse
URL:
Date posted:
Non-claim: this records a public discussion thread only; it is not CIRCT
endorsement, an accepted RFC, an implemented arcilator GPU backend, arbitrary
RTL support, or a broad GPU RTL speedup claim.
Next expected action:
```

Private pre-review route:

```text
Path: private pre-review
Reviewer:
Contact/review channel:
Expected feedback target:
Non-claim: this records a private review request only; it is not CIRCT
endorsement, an accepted RFC, an implemented arcilator GPU backend, arbitrary
RTL support, or a broad GPU RTL speedup claim.
Next expected action:
```

Fresh deferral route:

```text
Path: fresh owner deferral
Owner decision:
Concrete blocker:
Prepared package still valid as-is: yes/no
Next issue or evidence gate:
Non-claim: no public posting happened, and no CIRCT endorsement or accepted RFC
is claimed.
```

## Acceptance

Passes when one of these is recorded in the repo and on GitHub:

- Public Discourse URL, with no endorsement or accepted-RFC claim.
- Named private-review path and expected feedback target.
- Fresh deferral decision with a concrete blocker and next issue.

## 2026-07-04 Package Refresh

- FC-085 / #86 added an importable `BatchStimulusSpec` helper and focused tests,
  so the posting material can now say the input/test-vector boundary is locally
  represented as a small contract, not only described in prose.
- Refreshed both `docs/circt_batch_state_rfc_posting_package.md` and
  `docs/circt_batch_state_discourse_body.md` to mention that helper, round the
  timing table, add a repro-packet status, sharpen the first-reproducer
  exclusions, and reduce the maintainer ask to one primary question plus three
  follow-ups.
- Added a private pre-review message template to the posting package for the
  alternate #85 closure path while preserving the non-claims: no arcilator GPU
  backend, no stable runtime ABI, no arbitrary SystemVerilog testbench, and no
  broad speedup claim.
- Public-posting packet cleanup commit `af11f7c` removed the environment-specific
  dirty-worktree sentence from the posting package and copy-paste Discourse body,
  and replaced short evidence hashes with public commit links for `88bea41`,
  `4495df5`, and `275cd4f`.
- No new task issue is needed before owner action. The remaining closure step is
  still exactly one owner-controlled record: public Discourse URL, named private
  pre-review path, or fresh owner deferral.

## Non-claims

No CIRCT endorsement, no accepted RFC claim, no implemented arcilator GPU
backend, no arbitrary RTL support, no GEM replacement claim, no broad GPU RTL
speedup, and no public posting claim unless a URL is actually recorded.
