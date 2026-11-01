import ErdosProblems.Erdos527

/-!
Review interfaces for JSP-000423 / Erdos Problem 527.
These wrappers invoke the pinned upstream proof; they are not independent
proofs or claims of first formalization. See ATTRIBUTION.md.
-/

open Filter MeasureTheory
open scoped BigOperators

namespace JSP423Audit

/-- The original real-coefficient problem, retaining both hypotheses. -/
theorem original_problem
    (a : ℕ → ℝ) (hsq : Erdos527.SquareSumDiverges a)
    (hsmall : Erdos527.DecaysFasterThanInvSqrt a) :
    ∀ᵐ ε ∂Erdos527.rademacherProductMeasure,
      ∃ z : ℂ, ‖z‖ = 1 ∧ Erdos527.SeriesConvergesAt a ε z := by
  exact Erdos527.erdos_527 a hsq hsmall

/-- The same target with coefficient assumptions and convergence expanded. -/
theorem original_problem_expanded
    (a : ℕ → ℝ)
    (hsq : Tendsto (fun N ↦ ∑ n ∈ Finset.range N, |a n| ^ 2) atTop atTop)
    (hsmall : (fun n : ℕ ↦ |a n|) =o[atTop]
      (fun n : ℕ ↦ (Real.sqrt (n : ℝ))⁻¹)) :
    ∀ᵐ ε ∂Erdos527.rademacherProductMeasure,
      ∃ z : ℂ, ‖z‖ = 1 ∧
        Summable (fun n : ℕ ↦ ((ε n * a n : ℝ) : ℂ) * z ^ n)
          (SummationFilter.conditional ℕ) := by
  exact original_problem a hsq hsmall

/-- Relate the upstream convergence definition to ordinary natural partial sums. -/
theorem seriesConvergesAt_iff_partialSums (a ε : ℕ → ℝ) (z : ℂ) :
    Erdos527.SeriesConvergesAt a ε z ↔
      ∃ L : ℂ, Tendsto
        (fun N : ℕ ↦ ∑ n ∈ Finset.range N, ((ε n * a n : ℝ) : ℂ) * z ^ n)
        atTop (nhds L) := by
  change (∃ L : ℂ, Tendsto
    (fun s : Finset ℕ ↦ ∑ n ∈ s, ((ε n * a n : ℝ) : ℂ) * z ^ n)
    (SummationFilter.conditional ℕ).filter (nhds L)) ↔ _
  simp only [SummationFilter.conditional_filter_eq_map_range,
    Filter.tendsto_map'_iff, Function.comp_def]

/-- The original problem with ordinary finite partial sums as its conclusion. -/
theorem original_problem_partial_sums
    (a : ℕ → ℝ) (hsq : Erdos527.SquareSumDiverges a)
    (hsmall : Erdos527.DecaysFasterThanInvSqrt a) :
    ∀ᵐ ε ∂Erdos527.rademacherProductMeasure,
      ∃ z : ℂ, ‖z‖ = 1 ∧ ∃ L : ℂ, Tendsto
        (fun N : ℕ ↦ ∑ n ∈ Finset.range N, ((ε n * a n : ℝ) : ℂ) * z ^ n)
        atTop (nhds L) := by
  filter_upwards [original_problem a hsq hsmall] with ε hε
  obtain ⟨z, hz, hc⟩ := hε
  exact ⟨z, hz, (seriesConvergesAt_iff_partialSums a ε z).mp hc⟩

#print JSP423Audit.original_problem
#print JSP423Audit.original_problem_expanded
#print axioms JSP423Audit.original_problem
#print axioms JSP423Audit.original_problem_expanded
#print JSP423Audit.original_problem_partial_sums
#print axioms JSP423Audit.original_problem_partial_sums

end JSP423Audit
