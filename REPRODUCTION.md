# 本次隔离目录复现结果

新增接口的后续检查单独记录在 `_work/exact-statement.json`，包含 `JSP423Audit.original_problem` 与 `JSP423Audit.original_problem_expanded` 的实际编译、公理输出和文件哈希。运行 `python -I check_exact.py` 可核对保留的基础构建后编译这两个入口；它不会重编译下面所述的18个上游模块，也不会改写其历史 `result.json`。完整命令见 `REVIEW-PACKET.md`。

日期：2026-11-01（Asia/Shanghai）。Windows x86_64，同一台机器上的全新工作目录；没有将“新目录”说成第二台物理机器或虚拟机。

## 实际构建结果

完整入口从 **14:10:09 至 14:26:25** 运行，约16分16秒，进程退出码 **0**。

| 项目 | 当前实际证据 |
|---|---|
| 工具链 | Lean 4.33.0，发布提交 `d8b18978322de05a8f3dba51ef03cf5461676c17` |
| 安装包 | 复用之前下载的官方 Windows ZIP，重新计算 SHA-256 并完整解压至新 SSD 目录；没有复用旧精简运行库 |
| Mathlib | 固定提交 `db584cd6d46c92f209a44c0f1c829460d327499d`，8个配套仓库均按固定 manifest 获取和核对 |
| Mathlib 缓存 | 官方来源缓存获取工具成功；日志记录8689个本机已有压缩条目解包、1个已解包条目，无需下载缓存文件。未从源码重建整个 Mathlib |
| 自定义模块 | 17个依赖与 `ErdosProblems.Erdos527` 主文件，共18个，在新目录逐个重新编译；每项退出码均为0 |
| 本地接口 | `NoSquareSumHypothesis.lean` 重新编译，退出码0，产物哈希已记录 |
| 搜索路径 | 自定义库只指向新目录 `_work/lib`，另含本次固定 Mathlib 及配套库；不包含旧 G 盘自定义库或旧 SSD 库路径 |
| 原证据 | 对此前快照选择的20个原文件只读重新计算哈希，全部相同；这是20个选定文件的核对，不是整个 G 盘的递归审计 |

本次不是把旧编译日志复制为新验证结果。源代码按固定原始 URL 取得并检查原始及补丁后哈希；新编译收据记录了实际命令、输出目录与退出码，`compiled-modules.json` 绑定实际源码及 `.olean` 字节。

## 三个目标的实际公理输出

以下三项的输出均为 `[propext, Classical.choice, Quot.sound]`：

- `Erdos527.erdos_527`
- `JSP423Audit.ae_convergence_without_square_sum_divergence`
- `JSP423Audit.literal_statement`

它们没有在本次输出中依赖 `sorryAx` 或额外假设公理。这是所检查形式声明的依赖结果，不替代原题语义对应核查。

补充的声明检查进程退出码为0；已人工阅读其输出，核对实系数、先几乎所有符号再存在圆周点、独立公平符号测度以及自然顺序求和等定义。随后 `audit.py` 的145项文件和执行收据检查全部通过。计数是文件/收据核对项目，不是145个独立数学证明。

## 如何复现

将小型交付包解压至其他位置，安装 Python 3.11+、Git、完整的 Lean 4.33.0，然后在项目目录执行：

```sh
python reproduce.py
python review.py
python audit.py
```

如果没有通过 elan 将 Lean 加入 PATH，第一条使用：

```sh
python reproduce.py --toolchain "你的完整Lean安装目录"
```

第二、三条读取本次新生成的环境和收据；不需要旧的用户名、盘符、编译器目录或已编译自定义模块。标准代理环境变量可选，不固化本机代理地址。运行会生成新的 `_work/`；交付包中的 `evidence/` 仅是本次历史执行快照，不会被默认当作新构建的输入或成功状态。

`review.py` 输出实际检查过的终端类型及随机符号测度、系数条件、自然顺序求和等定义；原题逐项对应见 `STATEMENT.md`。`audit.py` 检查当前文件、哈希、编译收据、固定依赖和公理输出，本身不重新执行 Lean 编译。

## 证据位置与边界

工作目录中的主要记录：

- `_work/result.json`、`status.json`、`audit.json`
- `_work/source-receipt.json`、`dependency-receipt.json`、`toolchain-receipt.json`
- `_work/compiled-modules.json`、`build-environment.json`
- `_work/logs/extension-axioms.log` 及其实际退出码收据
- `_work/logs/statement-review.log`、`statement-review.json`
- `_work/full-toolchain-install.json`、`history-preservation.json`

交付包将这些记录复制到 `evidence/`。包不携带工具链、Mathlib 缓存、第三方完整源码树或自定义 `.olean`；第三方源码按锁定的原址获取。准备过程的失败和主动中断见 `BOOTSTRAP.md`。

这里实际核验的平台是 Windows；没有报告 Linux/macOS 或第二台机器构建成功。当前入口采用 Python 标准库及系统路径，具备移植所需的固定来源和命令，但其他平台仍需实际运行确认。

## 贡献定位

数学作者为 Marcus Michelen、Mehtaab Sawhney。主要 Lean 实现来自固定 plby/lean-proofs；我们完成既有证明的复现、接口补充和审阅材料整理。详细作者、逐文件许可及补丁来源见 `ATTRIBUTION.md`。本项目不主张首次形式化、数学新发现或官方奖励资格，全程没有提交 PR、联系他人或登录账号。
