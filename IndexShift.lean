import Mathlib.Topology.Algebra.Group.Basic
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Order.Filter.AtTopBot.Basic

/-!
A finite-prefix review bridge. This standard partial-sum identity is provided
to explain the n=0 versus n=1 indexing convention in the original-problem
interface. It is not an independent proof of Erdos Problem 527.
-/

open Filter
open scoped BigOperators

namespace JSP423Audit

theorem partial_sums_drop_zero {E : Type*} [AddCommGroup E]
    [TopologicalSpace E] [IsTopologicalAddGroup E]
    (f : ℕ → E) (L : E)
    (h : Tendsto (fun N : ℕ ↦ ∑ n ∈ Finset.range N, f n) atTop (nhds L)) :
    Tendsto (fun N : ℕ ↦ ∑ n ∈ Finset.range N, f (n + 1))
      atTop (nhds (L - f 0)) := by
  have hshift := (h.comp (tendsto_add_atTop_nat 1)).sub_const (f 0)
  simpa only [Function.comp_def, Finset.sum_range_succ', add_sub_cancel_right] using hshift

#check JSP423Audit.partial_sums_drop_zero
#print axioms JSP423Audit.partial_sums_drop_zero

end JSP423Audit
