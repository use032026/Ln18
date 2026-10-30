# SDK Flutter native hook 修复与语言包回归

固定 Flutter 3.41.9 对当前 im_l10n_catalog 0.3.0／35语言执行验证。

根因是编译摘要保留而 hook.dill 缺失时，hooks_runner 仍把缓存视为有效。本轮只使SDK项目内 objective_c 和 sqlite3 的编译摘要失效，由官方工具重建快照，没有清空全局缓存或改依赖。

20项定向测试全部通过，0失败、0跳过。新增3项覆盖35语言加载和typed参数、德语共享映射、未映射SDK文案的英语回退。原测试覆盖六种原语言、错误fallback、ARB优先级、文件参数、法务文本、宿主登录与返回按钮。加载事件没有计为用例。

另执行一次35语言delegate用例，成功复用两份kernel快照，SHA与修改时间保持不变。生成校验和SDK独立性检查通过，独立审查通过。

清理了本轮新增的build/test_cache与build/unit_test_assets，共95,199,232 bytes。保留恢复后的hook快照及摘要、既有native_assets/flutter_build、并行iOS框架构建与版本/资源清单更新。656个受保护文件和暂存状态在清理前后未变。

本结论限于本次定向回归，不代表全量SDK、真机或全部页面验收。原始事件、stderr、修复与清理清单均在同目录。
