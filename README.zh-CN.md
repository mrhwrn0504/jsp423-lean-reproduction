# JSP423 最小复现项目

统一入口：`python -I verify.py --mode full --toolchain "你的Lean安装目录"`，在新目录获取依赖并完整重建。已有基础构建时，`--mode compile` 重新编译接口及目标类型检查；`--mode retained` 核对现有记录和输入，不运行Lean。这三种模式的范围与耗时分别记录在 `_work/verification.json`。声明列表保存在 `targets.json`。额外同内核重放使用 `python -I replay.py --custom-closure`，不等于独立验证器或从空环境重放Mathlib。

原题对应入口及审阅步骤见 [REVIEW-PACKET.md](REVIEW-PACKET.md)。新增 `ExactStatement.lean` 保留原题两项系数假设；它直接调用上游证明。完整复现、类型审阅完成后执行 `python -I check_exact.py`，编译新增入口并核对实际公理输出。此前的 `result.json` 保持原有构建范围，新入口结果另存为 `exact-statement.json`。

本项目核验既有的 Erdős527 实系数形式化，并编译一个接口补充。数学工作属于 Marcus Michelen、Mehtaab Sawhney；主要 Lean 实现来自 plby/lean-proofs，文件署名 Codex、GPT-5.6 Sol。这里不主张首次形式化、数学新发现或奖项资格。

## 环境和入口

- Python 3.11+、Git、Lean **4.33.0**。安装方法见 [Lean 官方说明](https://lean-lang.org/install/)。
- 可访问 GitHub 固定提交和 Mathlib 官方缓存；代理可通过标准 `HTTPS_PROXY`、`HTTP_PROXY` 环境变量设置。
- 请预留约 20 GiB 磁盘空间。自定义模块单线程编译，解释器内存上限 4096 MiB；Mathlib 缓存需要额外空间。

在本目录执行：

```sh
python reproduce.py
```

若 Lean 未加入 PATH，可指定安装目录（含 `bin/lean`、`bin/lake`）：

```sh
python reproduce.py --toolchain "你的Lean安装目录"
```

路径由当前脚本位置计算，不要求 G 盘或特定用户名。下载及所有构建产物位于 `_work/`；可使用 `--work-dir "另一个新目录"` 改变位置。不要将该目录指向旧审计树。

可分别运行 `--phase sources`、`--phase dependencies`、`--phase cache`、`--phase build`。默认按此顺序全部运行。`build` 阶段重新编译全部18个自定义模块及本地接口，不复用旧自定义编译产物。重复执行不会删除旧目录；阶段日志保存最近一次执行记录。

这是一个 Python 驱动的最小 Lean 编译项目，入口不是顶层 `lake build`。Lake 只用于固定 Mathlib 项目的官方缓存获取。

## 固定与检查

`sources.lock.json` 固定两套上游提交、18份原始文件哈希、补丁后 LF 文件哈希、本地接口哈希，以及 Mathlib 完整依赖 manifest。

1. 从原始公开 URL 获取源码，检查下载字节哈希。
2. 保留原始字节于 `originals/`；在 `sources/` 统一 LF。
3. 应用 `patches/kernel-v4.33.0.patch`，再检查全部预期源码哈希。该补丁只改写一个私有求和引理的证明。
4. 从固定 Git 提交取得 Mathlib 及8个配套依赖，获取官方编译缓存。
5. 清除继承的 Lean 搜索路径，将自定义输出限定到新的 `lib/`，按导入拓扑重新编译。
6. 编译 `NoSquareSumHypothesis.lean`，核查三个目标的公理输出恰为 `propext`、`Classical.choice`、`Quot.sound`。

最终成功证据为 `_work/result.json`，同时必须读取 `_work/status.json` 与日志。源码获取、依赖、工具链、编译日志及产物哈希均另行保存。只看以前的成功文件不代表最新运行成功。

成功后执行 `python review.py`，用 Lean 输出实际检查过的终端类型与关键定义，保存在 `_work/logs/statement-review.log`。该步骤不引入新定理。然后执行 `python audit.py` 复核保留证据：检查实际文件、编译收据、源与产物哈希、依赖提交及目标公理日志，本身不重新编译。接口源文件按原字节保留，其头注提到的 `completion_audit.json` 属于历史审计；本项目新一轮结果以 `_work/` 下的证据为准。

本项目使用官方预编译 Mathlib 缓存，并不从零重建整个 Mathlib，也没有运行另一个独立内核。源文件哈希不是对数学陈述忠实性的替代。原题对应见 [STATEMENT.md](STATEMENT.md)，作者及许可见 [ATTRIBUTION.md](ATTRIBUTION.md)。

## 本次复现状态

2026-11-01 已在 Windows 新目录完成18个上游模块及本地接口的实际构建，三个目标的公理输出均为标准三公理；另有145项文件与执行收据核对通过。详细结果、缓存复用范围和平台边界见 [REPRODUCTION.md](REPRODUCTION.md)。这不是对第二台物理机器或其他操作系统已成功运行的声明。
