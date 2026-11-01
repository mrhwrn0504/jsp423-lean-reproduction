# 原题与形式声明对照

`JSP423Audit.seriesConvergesAt_iff_partialSums` 将上游收敛定义与“存在复数极限L，使前N项和趋于L”联系为等价命题；`JSP423Audit.original_problem_partial_sums` 给出使用普通部分和的原题入口。它们在 `ExactStatement.lean`，实际编译与目标公理记录见 `_work/exact-statement.json`。概率模型已有性质的逐项名称见工作区调研报告《随机模型对应.md》。

新增原题入口为 `ExactStatement.lean` 中的 `JSP423Audit.original_problem` 和 `JSP423Audit.original_problem_expanded`：两者都保留平方和发散与 little-o 衰减假设，直接调用 `Erdos527.erdos_527`。后一入口展开假设与自然顺序收敛定义。`NoSquareSumHypothesis.lean` 的更强接口继续作为附加内容，不替代这两个原题入口。验证命令与边界见 `REVIEW-PACKET.md`。

原题：[Erdős527](https://www.erdosproblems.com/527)。数学来源：[Michelen–Sawhney 论文](https://arxiv.org/html/2509.02729v1)。原题网站直接读取曾返回403，题文曾通过搜索索引读取；本项目主要依据固定 Lean 源码的明确类型进行逐项对应，不把索引访问当作直接页面全文核验。

固定源码：plby 提交 `8822f7ddef30fadbd92e1c6ab4ed897af356af5e`，`src/latest/ErdosProblems/Erdos527.lean`。

| 数学含义 | 固定源码中的定义或声明 | 审阅边界 |
|---|---|---|
| 实数系数序列 | `a : ℕ → ℝ` | 不等于论文一般复系数版本 |
| 独立公平随机符号 | 第46行 `rademacherMeasure`，第54行 `rademacherProductMeasure` | 每坐标取±1各半；以无穷乘积测度表达 |
| 系数衰减快于 n 的负二分之一次方 | 第513行 `DecaysFasterThanInvSqrt`，little-o 条件 | n=0 的约定不改变无穷远条件 |
| 平方和发散 | 第509行 `SquareSumDiverges`，自然部分和趋向正无穷 | 上游最终包装器要求它；本地接口不要求它 |
| 几乎必然存在一个单位圆点 | 第20672行 `erdos_527`，`∀ᵐ ε, ∃ z, ‖z‖ = 1 ∧ ...` | z 可以依赖符号序列 ε；不是一个 z 对几乎所有 ε 通用 |
| 幂级数按自然顺序收敛 | 第505行 `SeriesConvergesAt`，`SummationFilter.conditional ℕ` | 不额外要求绝对收敛或无条件求和 |

本地 `JSP423Audit.literal_statement` 展开了系数条件与收敛定义，方便审阅。`ae_convergence_without_square_sum_divergence` 调用已有的上游一般下层结论，移除最终包装器未使用的平方和发散条件。其证明仍依赖上游全部分析链，不构成独立证明。

本项目不涵盖论文收敛点集合 Hausdorff 维数等于1的结论，也不据此断言其他仓库没有相关形式化。公理核查通过只说明所检查形式声明的依赖范围，不会自动认证定义与原题的语义一致性或奖项资格。
