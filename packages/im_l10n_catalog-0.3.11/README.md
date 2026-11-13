# IM公共语言资源包 0.3.0

完整版本化语言源及构建时导出工具，当前供chat-im-cs移动/PC和IMSDK使用。

- Flutter源：35语言、2250个key、15模块；消费者profile保留各自语言、key、metadata和差异。SDK选择35语言1040个key，保留原六语30条差异译文。
- PC源：6语言、32模块、每语言2973个leaf；保留原nested/array与fallback。
- 补充源：两端语言名称、翻译示例、法务正文与平台差异、SDK/Web词库、移动原生权限资源。

真实消费者根目录声明l10n.resources.json，版本固定0.3.0；工具生成其原有本地文件和摘要，正常构建不需要公共包checkout。没有在SDK pubspec中加入项目外部path依赖。

```sh
# 在本包内先准备Dart工具依赖：
dart pub get

# 更新消费者；Flutter导出后还需在其Flutter包根执行flutter gen-l10n：
python3 tools/sync.py --consumer-root /path/to/consumer

# 只读验证：
python3 tools/sync.py --consumer-root /path/to/consumer --check
```

Flutter的bin/generate.dart仍支持普通App配置和includeKeys/excludeKeys覆盖；生产profile保留现有接口，flat布局维持lib/l10n导入路径。按配置选择业务资源，不自建ICU引擎，复数与参数代码由Flutter生成。

工具检查版本、路径、输出归属与内容摘要。手写业务代码不放进Flutter生成器独占目录。只读check不自动准备依赖，不静默修复本地内容。补充资源导出不会自动删除旧路径；需要明确的迁移后才可移除。

所有词库与法律原文为私有项目资源，publish_to保持none，没有授权公开发布。消费者的运行、独立源码交付和普通构建只依赖随包生成结果。完整配置、维护说明及证据见Ln18根README和各源仓库的本地化接入文档。

0.3.0 的 SDK 共有 ARB 资源全部来自同一个 35 语公共源。SDK / Web 专属文案没有对应公共译文时使用英语回退；生成的覆盖记录区分公共词条复用与回退，不代表专属文案或法务正文已全部翻译为35语。chat-im-cs现有消费者仍固定0.2.0，维护它们应使用对应0.2.0归档源。当前checkout同步仅SDK时使用Ln18的 `tool/sync_all.py --only sdk`。
