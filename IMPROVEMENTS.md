# JSP-000423 improvement and review status

Local record date: 2026-11-01. This project improves reproduction, statement interfaces and review evidence for an existing formalization. It does not claim first formalization, organizer acceptance or an award.

## What can be reviewed

| Area | Implemented evidence | Boundary |
|---|---|---|
| Original statement | Three original-hypothesis interfaces in ExactStatement.lean | Uses the upstream real-coefficient proof |
| Natural-order convergence | Checked equivalence to existence of a limit of finite natural partial sums | Does not assert absolute convergence |
| Random model | targets.json lists upstream fairness, support, coordinate-law and independence declarations; type inspection executed | Properties belong to upstream, not new local proofs |
| Input consistency | Byte snapshot and pre/post fingerprints; temporary-file mutation tests | Not an adversarial filesystem lock; Mathlib cache trust retained |
| Unified verification | compile, retained and new-directory full modes executed successfully; failure-path tests passed | Full run used matching shared official dependency caches on the same machine |
| Kernel replay | 20 explicit custom module targets passed bundled leanchecker | Same kernel, imports trusted, not empty-environment or independent-kernel validation |
| Incremental store | 19-target content/dependency keys; actual corrupt-interface recovery compiled one module and reused 18 | Comment-only source edit passed: 2 actual compilations and 17 cache hits in 336.273 seconds |
| Performance | Three validated warm-cache reuse runs: 1.316, 1.337, 1.223 seconds | Reuse, not recompilation; concurrent background I/O and warm OS caches |

Commands and source/receipt locations are in REVIEW-PACKET.md. The baseline fresh-build result, new interface result, unified workflow result and optional replay result are different records with different scopes. Historical evidence must not be interpreted as a fresh run on another machine.

## Scope and outstanding technical checks

The real coefficient domain, square-sum divergence, little-o decay, signing-dependent unit-circle point and ordinary partial sums are visible in the checked target types. No monotonicity premise was added. The natural number index begins at zero; the separate IndexShift.lean finite-prefix lemma passed Lean checking (34.487 seconds). A fully formal coefficient non-vacuity witness has not been added. The paper's stronger Hausdorff-dimension result is outside this package's proof claim.

A new project directory on D: was populated with source files only and completed full verification with pinned dependencies and the same Lean installation. The final full run exited zero in 1189.356 seconds (about 19 minutes 49 seconds), including 18 newly compiled upstream modules, local interfaces, statement review and target inspection. Its first attempt failed on DNS before Lean compilation; a retry used the system's configured proxy only in that process. Failed and interrupted attempts were preserved separately.

After a very slow first custom-module compilation using the independently populated D: dependency cache, that attempt was preserved and stopped. The next full run retains the new source checkouts but accesses the already available C: official dependency artifact caches through explicitly recorded directory junctions, after comparing both checkouts with the pinned revisions. Original D: artifact directories were preserved. No old custom proof artifacts were linked or copied into this full build. This is a shared official-cache reproduction, not a cold-cache or independent-machine test; `shared-artifact-cache.json` records the placement when included with the new run.

The comment-only upstream source-edit trial was interrupted when concurrent tasks left about 90 MB available memory. The serial rerun subsequently passed in 336.273 seconds: two affected modules compiled and 17 unrelated modules reused. The interrupted attempt remains separate historical evidence.

## Attribution and priority

The pinned upstream file credits Marcus Michelen and Mehtaab Sawhney for the mathematics and Codex / GPT-5.6 Sol for formalization. Git committer information is a different kind of evidence. Local work consists of interfaces, reproduction tooling, input binding, caching and evidence organization; see ATTRIBUTION.md.

Public registration requests [#1256](https://github.com/TheJustinSunPrize/awards/pull/1256) and [#5425](https://github.com/TheJustinSunPrize/awards/pull/5425) already refer to the upstream source. Their opening, or a locally successful build, is not an award or an authorship decision. No public history establishing this user's first completion of the full original formalization has been provided.

The applicable [repository process](https://github.com/TheJustinSunPrize/awards/blob/main/docs/award-process.md) and [contribution instructions](https://github.com/TheJustinSunPrize/awards/blob/main/CONTRIBUTING.md) require original contribution and attribution evidence. A mirror of someone else's complete proof does not establish that contribution. The [website process](https://www.hejustinsun.com/prize/participation) and repository differ on contributor-registration ordering; that conflict is documented, not resolved by this local project. JSP-000423 was not on the MathDB pilot list at the recorded check.

Technical improvements can make review easier and expose gaps. There is no measured or official basis for assigning an award probability to them, and they do not transfer upstream priority to the local reproduction author. All materials remain local; no messages, PRs or claim submissions were sent.

The standalone finite-prefix checker initially exceeded its 1 GiB memory threshold. With the proof source unchanged and only the threshold set to the main workflow's 4 GiB, it passed and printed the standard three axioms. Both the failure and successful receipt are retained. This helper is supplemental, not a replacement for the original-problem interfaces.

The final incremental --force branch passed in 690.373 seconds: all 19 targets actually compiled, with zero cache hits and zero audited-base seeds. Its interface axiom checks passed. This is a separate C: incremental run, not the D: full workflow run.
