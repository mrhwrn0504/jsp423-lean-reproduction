# JSP-000423 / Erdős 527: Lean reproduction and review interfaces

This project reproduces an existing public formalization and supplies statement
interfaces, reproducibility tools and review evidence. It makes no claim of
first formalization, an independent proof, official acceptance or an award.

## Exact statement

For real coefficients with divergent square sums and little-o decay relative
to the inverse square root of the index, almost every fair independent sign
sequence admits a point on the complex unit circle where the signed power
series converges in natural order. The point may depend on the signs. The
paper's stronger Hausdorff-dimension result is outside this package's scope.

| Target | File / role |
| --- | --- |
| `Erdos527.erdos_527` | Existing upstream theorem, downloaded from its fixed source |
| `JSP423Audit.original_problem` | `ExactStatement.lean`, retains original hypotheses |
| `JSP423Audit.original_problem_expanded` | Same file, expanded interface |
| `JSP423Audit.original_problem_partial_sums` | Same file, ordinary partial sums |
| `JSP423Audit.seriesConvergesAt_iff_partialSums` | Same file, convergence equivalence |
| `JSP423Audit.partial_sums_drop_zero` | `IndexShift.lean`, separate generic finite-prefix helper |

The problem interfaces call the existing upstream theorem. The optional
`NoSquareSumHypothesis.lean` interface does not replace them. See
[STATEMENT.md](STATEMENT.md) and [REVIEW-PACKET.md](REVIEW-PACKET.md).

## Mathematical source and attribution

Mathematics: Marcus Michelen and Mehtaab Sawhney,
[paper](https://arxiv.org/html/2509.02729v1).
The pinned [plby source](https://github.com/plby/lean-proofs/blob/8822f7ddef30fadbd92e1c6ab4ed897af356af5e/src/latest/ErdosProblems/Erdos527.lean)
credits Codex and GPT-5.6 Sol for formalization.

Local contributions are interfaces, input binding, reproduction and incremental
drivers, and review documentation. They do not transfer upstream authorship or
priority. See [ATTRIBUTION.md](ATTRIBUTION.md) and `licenses/`. Retain upstream
notices when redistributing downloaded source.

## Pinned environment and reproduction

Python 3.11+, Git, Lean **4.33.0**. The toolchain is in `lean-toolchain`;
`sources.lock.json` fixes source revisions, hashes and dependency versions.
Third-party source is obtained from its original pinned locations.

```text
python -I verify.py --mode full --toolchain <Lean-installation-directory>
```

This Python-driven project does not use a top-level `lake build` entry point.
Full mode compiles 18 custom upstream modules and local interfaces and reviews
target declarations. It uses matching official Mathlib compiled caches. Allow
approximately 20 GiB of disk space; compilation is serial with a 4096 MiB
interpreter threshold. See [BOOTSTRAP.md](BOOTSTRAP.md) and
[README.zh-CN.md](README.zh-CN.md).

After a successful full build:

```text
python -I incremental.py --force
python -I incremental.py --no-seed
python -I replay.py --custom-closure
python -I check_index_shift.py
```

The incremental driver covers 19 targets in a separate store. Full mode also
covers the optional no-square-sum interface. Cache reuse is not a new Lean
compilation. The finite-prefix helper is checked separately, outside full mode.
Replay uses the same Lean kernel against imported dependencies, not an
independent kernel or a complete Mathlib recheck.

## Historical verification evidence

The complete `evidence/` tree (including empty logs and source snapshots) is
in `verification-evidence.zip`; major JSON receipts are also browsable directly.
The archive includes `external-runs/d-full-build.zip` for the separate D: full
workflow. Extract it from this repository directory with:

```text
python -m zipfile -e verification-evidence.zip .
```

These records come from the original working directories on
2026-11-01, not this publication tree. Absolute paths identify those runs.
Publishing a new Git commit does not renew their verification date.

| Check | Recorded result |
| --- | --- |
| New-directory full workflow | Passed, 1189.356 seconds; shared official dependency caches |
| Incremental force branch | 19 actual compilations, zero hits/seeds, 690.373 seconds |
| Comment-only source edit | 2 compilations, 17 cache hits, 336.273 seconds |
| Same-kernel replay | 20 explicit custom module targets passed |
| Input/evidence audit | 145 checks passed |
| Tool regression checks | 12 tests passed; these are not mathematical proof checks |

Checked problem targets reported only `propext`, `Classical.choice` and
`Quot.sound`. See [IMPROVEMENTS.md](IMPROVEMENTS.md). This is not a full Mathlib
rebuild or a formal coefficient non-vacuity witness.

## Publication and prize status

Repository: [mrhwrn0504/jsp423-lean-reproduction](https://github.com/mrhwrn0504/jsp423-lean-reproduction), branch `main`.
Published as reproduction and review tooling. Any linked official PR concerns
supplemental documentation, not an award claim or first-formalization credit. The publication commit is distinct from the pinned upstream
proof and the historical checked working directories.

Existing registrations [#1256](https://github.com/TheJustinSunPrize/awards/pull/1256)
and [#5425](https://github.com/TheJustinSunPrize/awards/pull/5425) already refer
to the upstream proof. Current [official rules](https://github.com/TheJustinSunPrize/awards/blob/main/CONTRIBUTING.md)
require the submitter's own attributable contribution and prohibit registering
another person's proof or mirror on their behalf. This reproduction is not an
eligible first-formalization claim.
