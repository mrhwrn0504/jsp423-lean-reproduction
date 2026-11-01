# 来源、许可及改动归属

## 数学及主要形式化

- 数学作者：Marcus Michelen、Mehtaab Sawhney。[论文](https://arxiv.org/html/2509.02729v1)。
- 主要形式化：[plby/lean-proofs](https://github.com/plby/lean-proofs)，固定提交 `8822f7ddef30fadbd92e1c6ab4ed897af356af5e`。Erdos527 文件署名 Codex、GPT-5.6 Sol，并载明 Apache 2.0；保留各文件自己的版权及作者声明。
- 外部 BoundedGaps 依赖：[frenzymath/FormalPantheon](https://github.com/frenzymath/FormalPantheon)，固定提交 `ffbb65c21afc8a36ace67720f1b0df1c63d26bd1`。[仓库 LICENSE](https://raw.githubusercontent.com/frenzymath/FormalPantheon/ffbb65c21afc8a36ace67720f1b0df1c63d26bd1/LICENSE) 为 Apache 2.0。
- plby 的 [src/latest/LICENSE](https://raw.githubusercontent.com/plby/lean-proofs/8822f7ddef30fadbd92e1c6ab4ed897af356af5e/src/latest/LICENSE) 说明外部来源文件的 Apache 2.0 许可；它不是整个仓库统一授权的证明。以逐文件声明为准。
- Mathlib 与配套依赖按固定 manifest 从各原始仓库获取；其许可文件保留在对应 checkout 中。本复现工具不改变其许可。

## 本地贡献

- `ExactStatement.lean`：保留原题两项假设的审阅接口，直接调用已有上游定理；`check_exact.py` 为新增接口保存编译、公理与来源收据。它们不构成独立重写或首次形式化声明。

- 既有证明的编译、公理检查和证据整理。
- `NoSquareSumHypothesis.lean`：调用上游结论的接口补充，去除未使用假设并展开定义。
- 本次 `reproduce.py`、固定来源清单、构建说明和语义对应表。

这些贡献不应署为上游数学证明或完整形式化的首次作者。本项目不主张独立重写、官方认证或奖励资格。

## 补丁

`patches/kernel-v4.33.0.patch` 提取自固定 plby 提交的 `src/latest/patches/formalpantheon-v4.33.0.patch` 中与最小导入闭包有关的一段，并只调整路径前缀。它将 `sum_Ioc_nat_eq_sum_range_succ` 的有限集映射证明改写为归纳证明；定理陈述不变。其余上游补丁不涉及本导入闭包，未应用。

下载的原始源码不随小型交付包分发：脚本从固定原址获取，并保留所有原始字节与逐文件声明。经过修改的工作副本与补丁、原始副本、源码收据并列保存。若以后再分发完整第三方源码树，应连同原项目许可及有关通知一起处理。
