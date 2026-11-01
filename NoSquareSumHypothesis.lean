import ErdosProblems.Erdos527

/-!
An interface extension to the pinned plby development, not an independent
proof or a mathematical novelty claim. See the retained build and axiom logs
and completion_audit.json for the actual verification status.
Upstream commit: 8822f7ddef30fadbd92e1c6ab4ed897af356af5e.
The analytic argument and probability wrappers belong to upstream authors.
-/

open Filter MeasureTheory

namespace JSP423Audit

/-- Expose the upstream analytic conclusion without the unused square-sum
divergence hypothesis carried by its final public wrapper. -/
theorem ae_convergence_without_square_sum_divergence
    (a : ℕ → ℝ) (hsmall : Erdos527.DecaysFasterThanInvSqrt a) :
    ∀ᵐ ε ∂Erdos527.rademacherProductMeasure,
      ∃ z : ℂ, ‖z‖ = 1 ∧ Erdos527.SeriesConvergesAt a ε z := by
  apply Erdos527.ae_of_arbitrarily_high_measurable_good_sets
    Erdos527.rademacherProductMeasure
    (fun ε ↦ ∃ z : ℂ, ‖z‖ = 1 ∧ Erdos527.SeriesConvergesAt a ε z)
  intro η hη hηone
  exact Erdos527.TerminalAE.exists_measurable_convergence_goodSet
    a hsmall (N0 := 1) (by norm_num)
    (Erdos527.TerminalAE.eventualAdaptiveTransitionBound
      a hsmall (N0 := 1) (by norm_num)) η hη hηone

/-- Expand the upstream definitions so that the actual coefficient condition
and naturally ordered series are visible in the public statement. -/
theorem literal_statement
    (a : ℕ → ℝ)
    (hsmall : (fun n : ℕ ↦ |a n|) =o[atTop]
      (fun n : ℕ ↦ (Real.sqrt (n : ℝ))⁻¹)) :
    ∀ᵐ ε ∂Erdos527.rademacherProductMeasure,
      ∃ z : ℂ, ‖z‖ = 1 ∧
        Summable (fun n : ℕ ↦ ((ε n * a n : ℝ) : ℂ) * z ^ n)
          (SummationFilter.conditional ℕ) := by
  exact ae_convergence_without_square_sum_divergence a hsmall

#print axioms JSP423Audit.ae_convergence_without_square_sum_divergence
#print axioms JSP423Audit.literal_statement
#print axioms Erdos527.erdos_527

end JSP423Audit
