# 本轮准备过程记录

本文件记录2026-11-01建立复现入口时实际遇到的问题。最终构建结果另见 `REPRODUCTION.md`，不以准备阶段的失败或旧审计日志作为成功证据。

| 步骤 | 实际观察 | 处理与证据 |
|---|---|---|
| 从旧审计资料生成固定清单 | Windows 默认 GBK 无法读取含 Unicode 的上游补丁 | 生成器显式使用 UTF-8；属于项目生成阶段的控制台异常，未保存为 Lean 编译日志 |
| 首次应用最小补丁 | 外层工作区是 Git 仓库，子目录中的 `git apply` 退出0但未改目标文件；补丁后哈希检查拒绝继续 | 为源码目录建立独立 Git 边界；当前补丁检查、应用收据及准备后源码哈希可复查。首次哈希异常保留于聊天工具输出，不声称有独立失败日志文件 |
| 使用旧精简 SSD 运行库构建缓存工具 | 缺少 `include/lean/lean.h`，C 编译失败 | `evidence/logs/partial-runtime-cache-failure.log` 及收据。入口现要求完整工具链 |
| 改用磁盘上的完整工具链 | 启动较慢，主动中断此次尝试 | `evidence/logs/hdd-runtime-interrupted.log` 与收据；这是人为中断，不是 Lean 定理检查失败 |
| 将完整官方安装包重新解压到 SSD | 先重新计算 SHA-256，与固定发布包摘要一致，再逐成员解压并验证 ZIP CRC | `evidence/full-toolchain-install.json`。安装包复用此前下载；没有宣称重新下载 |

工作目录中的路径是 `_work/logs/`、`_work/full-toolchain-install.json`；小型交付包将这些记录复制到 `evidence/`。两者记录同一次执行。工作区旧 G 盘审计文件未作为新构建的自定义库输入；本轮对原证据包选定的20个文件另作只读哈希复查。
