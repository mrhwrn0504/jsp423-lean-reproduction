# JSP-000423 review entry points

This package reproduces an existing upstream development. It does not claim first formalization or award eligibility. The mathematical authors are Marcus Michelen and Mehtaab Sawhney; the pinned plby file credits Codex and GPT-5.6 Sol. See ATTRIBUTION.md.

## Exact targets

- Upstream: `Erdos527.erdos_527`, in `ErdosProblems/Erdos527.lean` at the locked plby commit.
- Review interface: `JSP423Audit.original_problem`, in `ExactStatement.lean`.
- Expanded interface: `JSP423Audit.original_problem_expanded`, in the same file.
- Ordinary partial sums: `JSP423Audit.original_problem_partial_sums`, with the equivalence `JSP423Audit.seriesConvergesAt_iff_partialSums` in the same file. The conclusion explicitly states existence of a limit of the sums over `Finset.range N`.

All three problem interfaces preserve the real coefficient domain, square-sum divergence, little-o decay, fair independent sign sequence measure, almost-everywhere quantifier, signing-dependent unit-circle point, and natural-order convergence. Their proofs use the upstream theorem, without depending on the optional no-square-sum interface.

The series starts at index 0; a finite initial term does not affect convergence. The random space is the product measure on real sequences supported on signs ±1. The witness point is inside the almost-everywhere quantifier. `SummationFilter.conditional ℕ` expresses natural-order summation; it does not assert absolute convergence. This covers the real-coefficient problem, not every stronger complex-coefficient or Hausdorff-dimension conclusion of the paper.

## Reproduce from this package directory

The unified equivalent is `python -I verify.py --mode full --toolchain "path/to/Lean-installation"`. Use `--mode compile` only with a retained successful base build; use `--mode retained` for validation without new Lean execution. `targets.json` names proof interfaces and model declarations; generated `#check` commands inspect them in compile/full modes. The default is full, not reuse. A full run in the independent D: directory passed on 2026-11-01, using matching shared official dependency caches and the same toolchain installation; see IMPROVEMENTS.md and the particular run's verification.json. This does not imply a second machine or an independently rebuilt Mathlib.

Optional `python -I replay.py --custom-closure` runs the bundled leanchecker sequentially on the 18 custom upstream modules and two local interface modules. This is the same Lean kernel replaying each module against its imports. It is neither an independent kernel nor `--fresh` replay of the entire Mathlib dependency closure. The result and explicit module commands are retained in `kernel-replay.json`; only a passed record can support a replay success claim.

```sh
python reproduce.py
python review.py
python audit.py
python -I check_exact.py
```

If necessary, pass `--toolchain "path/to/Lean-installation"` to reproduce.py. With a custom work directory, pass the same `--work-dir` to all four commands. check_exact.py audits the retained base before compiling the three interface targets and checks their actual printed axiom dependencies. It does not rebuild the 18 upstream modules; reproduce.py does that.

The Lean file itself contains valid `#print` and `#print axioms` commands. The checker records the actual Lean invocation, compiler exit code, source/output/log hashes, base-result hash, and checker hash in `_work/exact-statement.json`. An older successful record cannot validate a modified interface or checker: rerun the checker after a change. The historical base record `_work/result.json` retains its original scope and target count.

The checker now compiles a retained byte snapshot of the interface, compares fingerprints before and after execution, and audits the base again afterwards. Fingerprints include the interface/checker/audit code, locked inputs, compiler and 18 custom import artifacts. It records separate audit/Lean timings. `python -I test_input_binding.py` exercises rejection of changed inputs in temporary files, including a child-process mutation. These comparisons detect persistent changes; they are not a filesystem lock or protection against hostile changes that are reverted between observations. Mathlib cache artifacts remain within the base audit's documented trust boundary.

For repeated local checks with unchanged inputs, `python -I check_exact.py --reuse` re-audits the base and validates the retained interface receipt, snapshot, compiler, import artifacts and log. It fails on stale evidence and does not invoke Lean. It writes `exact-reuse.json` with `new_lean_execution: false`; it does not renew the original compilation time. Run without `--reuse` when a fresh interface compilation is wanted. This cache path covers the interface only; it does not implement incremental recompilation of the 18 upstream modules.

An additional incremental driver, `python -I incremental.py`, maintains 18 custom upstream modules plus ExactStatement in a separate `_incremental/` store. Keys bind source, dependency keys/artifact hashes, compiler, fixed baseline context and driver. The first run may seed byte-identical artifacts from the audited base; later runs reuse matching entries. Both are reported separately from actual compilation. `--no-seed` compiles cache misses while retaining valid cache hits; `--force` compiles every target. The original fresh-build evidence remains unchanged. `--source-tree` can select an edited copy of the existing custom module tree; unsupported new custom imports are rejected. Original attribution is retained, and local source differences are recorded. This experimental path is supplemental to full verification, not a replacement for a clean build or the independent review of a changed statement. Its interface log is checked for the expected axiom dependencies.

## Attribution and public records

The same upstream proof already has registration requests [#1256](https://github.com/TheJustinSunPrize/awards/pull/1256) and [#5425](https://github.com/TheJustinSunPrize/awards/pull/5425). At the 2026-11-01 check both were open and unmerged. Our reproduction and interface work does not establish earlier priority or transfer upstream authorship. Their PR authors' assertions are not organizer verification decisions.

The pinned upstream repository has no root lakefile at this commit, so a bare `lake build` in its root is not the reproduction procedure for this package. Use the commands above. See REPRODUCTION.md for the Mathlib cache, compatibility patch, and platform boundaries.

## Supplemental finite-prefix check

`python -I check_index_shift.py` checks the generic `JSP423Audit.partial_sums_drop_zero` lemma against the audited default `_work` environment. It translates natural partial sums to the sequence with its first term removed, with limit adjusted by `f 0`. Its separate receipt is `index-shift.json`. This command is not part of full mode and does not verify shifted coefficient hypotheses or an independent original theorem.
