# 公共语言资源包与真实项目接入

`im_l10n_catalog 0.3.0` 是当前语言资源的维护源。chat-im-cs 移动端、PC 端和 IMSDK 已接入生成流程；原仓库保留各自需要的生成文件，正常构建不依赖 Ln18 存在。代码仓库：[use032026/Ln18](https://github.com/use032026/Ln18)。语言资源包尚未发布到 pub.dev。

## 当前资源范围

| 消费者 | 保留语言 | 主要资源 | 差异处理 |
| --- | --- | --- | --- |
| chat-im-cs Flutter | 当前全部35种 | 每语言2250个ARB key，15个业务模块 | 使用chat_mobile profile，保持全部值和metadata |
| chat-im-cs PC | zh-CN、zh-TW、en、ja、vi、th | 每语言2973个leaf，32个顶层模块 | 保留嵌套数组、对象顺序和原英语fallback |
| IMSDK Flutter | 与chat-im-cs相同的35种 | 每语言1040个ARB key | 使用im_sdk profile，30条差异译文单独覆盖 |
| IMSDK Web | 35种语言识别，专属缺译回退英语 | 146条中文原文索引词库 | 保留原翻译函数、参数和fallback |

另已抽取两端的设备语言名称、应用语言自名、翻译示例、SDK 77条补充界面文案与文件提示，以及多语言法务正文和平台差异文案。移动端35份iOS权限提示和Android strings保留原路径、原文及稳定通知标识。

这里的“完整”指现有静态语言资源，不包含把业务兼容判断、协议语言码或服务端返回内容重新翻译。0.3.0 将SDK语言选择扩展为35种；没有统一原本不同的注册能力提示。

## 公共包如何组织

```text
packages/im_l10n_catalog/
├── pubspec.yaml                    version: 0.3.0
├── catalog/
│   ├── index.json                  Flutter的语言和15模块归属
│   ├── common/app_*.arb
│   ├── auth/app_*.arb
│   ├── chat/app_*.arb
│   ├── settings/app_*.arb
│   ├── ...                         其余业务模块
│   ├── profiles/chat_mobile.json   移动端语言/key与原顺序
│   ├── profiles/im_sdk.json        SDK范围、差异和原metadata
│   ├── mobile_supplemental/        移动端补充、法务和原生资源
│   ├── sdk_supplemental/           SDK补充、法务和Web资源
│   └── pc/                        locale × module JSON，保留数组
├── bin/generate.dart              Flutter ARB选择器
├── tools/sync.py                  三个真实消费者的同步/check入口
├── renderers/                     移动、SDK、PC的静态格式导出
└── test/                          生成与写入边界测试
```

Flutter模块为 common、app、auth、chat、settings、contacts、profile、organization、customer_service、calls、safety、official_account、feedback、favorites、notifications。保留原来的key，不要求业务代码改调用方式。

SDK的5个差异key在原6种语言下合计30条：authExpandJoin、authJoinCredentialHint、authJoinHelp、authJoinNotFound、authQuickLoginSummary。它们保存在SDK profile中，不会被移动端的新文案静默覆盖。新增29语对这5条差异文案显式采用SDK英语回退（另145条），避免引入App测试账号说明或不同注册能力。

## 真实项目的配置与调用

Flutter消费者保留 `l10n.bundle.json`，声明版本、profile、语言、模块和flat输出；两个项目仍使用原来的 `lib/l10n/app_localizations.dart` 与 `AppLocalizations`，公开getter和参数方法保持一致。

```dart
final text = AppLocalizations.of(context);
Text(text.commonSend);
Text(text.chatReadCount(3));
```

各端根目录另有 `l10n.resources.json` 和 `l10n.resources.lock.json`，声明补充资源导出器并记录生成内容摘要。SDK的Flutter配置位于 `packages/im_sdk/l10n.bundle.json`；SDK根配置会指向它。

各项目的同步入口默认从 GitHub 获取自己的固定版本，不需要本机保留 Ln18。
`l10n.source.json` 记录远程仓库、完整提交号、版本归档路径和 SHA256；
工具只下载对应语言包到项目内被忽略的 `.l10n-cache/`，校验后再生成。
移动端和 SDK 当前固定 0.3.0，PC 固定独立维护的 0.2.1。

在对应项目目录执行更新或校验：

```sh
# chat-im-cs/lpp/lpp_mobile
python3 tool/sync_l10n.py
python3 tool/sync_l10n.py --check

# chat-im-cs/lpp/lpp_pc_client
npm run i18n:sync
npm run i18n:check

# IMSDK
python3 scripts/sync_l10n.py
python3 scripts/sync_l10n.py --check
```

移动端和 SDK 的更新命令会自动执行各自的 `flutter gen-l10n`。
`--check` 不改消费者生成文件；首次使用时允许下载归档和准备生成器的锁定 Dart 依赖。
已有缓存时可加 `--offline`，缺少所需输入则明确失败，不回退到最新分支。
缓存可随时移除，下次资源维护再获取；普通构建和运行不访问远程词库。

需要在一台开发机同时维护多个项目时，也可在 Ln18 中执行：

```sh
python3 tool/sync_all.py
```

该命令调用各项目的同步入口，分别使用自己的远程版本和固定工具链，不强制三端使用同一个公共包。只校验消费者生成文件：

```sh
python3 tool/sync_all.py --check
```

可用 `--only mobile`、`--only sdk`、`--only pc` 限定范围，也可用root参数指定其他机器上的仓库位置。没有对应源仓库时，公共包、A/B示例和已有SDK生成代码仍可单独查看或运行。

测试尚未发布的词库修改时，显式传入本地包路径：

```sh
# chat-im-cs/lpp/lpp_mobile
python3 tool/sync_l10n.py --catalog-root /path/to/Ln18/packages/im_l10n_catalog

# chat-im-cs/lpp/lpp_pc_client
python3 scripts/sync-l10n.py --catalog-root /path/to/Ln18/packages/im_l10n_catalog-0.2.1

# IMSDK
python3 scripts/sync_l10n.py --catalog-root /path/to/Ln18/packages/im_l10n_catalog
```

本地维护覆盖也支持环境变量 `IM_L10N_CATALOG_ROOT`；未显式提供时始终使用远程固定来源，不再隐式查找桌面 Ln18。`--cache-dir` 可用于 CI 隔离缓存。以上本地源必须与相应消费者声明的版本一致。

## 日常维护与版本

1. 新功能可以先在 chat-im-cs 开发，同时在 Ln18 的模块 ARB 中添加词条及参数 metadata，并更新 `catalog/index.json` 和 `chat_mobile` profile 的 key 清单。不要直接维护消费者生成文件。
2. SDK 采用该模块或需要这些文案时，同步把所需 key 纳入 `im_sdk` profile 和消费者模块选择；保留 SDK 专属覆盖。新增移动端功能不会自动扩大 SDK 的词条范围。PC 在 `catalog/pc` 中维护自己的 JSON 数据集，同义词条不自动跨格式映射。
3. 为本次词库变更创建新版本，更新包、catalog 及待升级消费者声明。使用显式本地源生成和验证后，由 `tool/package_catalog.py` 生成版本归档，提交并推送 Ln18。已发布归档保持不变；PC 维护包使用对应版本的归档流程。
4. 在需要更新的消费者中，把 `l10n.source.json` 固定到包含该归档的完整远程提交号、归档路径和 SHA256；同步更新资源配置中的 `catalogVersion`（Flutter 同时更新 bundle 配置）。固定提交和摘要，不追踪 `main` 的浮动内容。
5. 在各项目运行同步、`--check` 及受影响端的定向测试，提交生成资源、两个收据和版本来源配置。SDK 源码交付仍包含生成 Dart/TS，普通构建独立于远程词库。未涉及语言资源的业务更新不需要同步词库。

三个消费者旁的 `l10n_source.py` 是 `tool/l10n_source.py` 的随项目交付副本；升级下载工具时应一起更新并核对内容一致。当前仅改造按固定版本获取与生成入口，没有配置自动跨仓库提交或 PR。

创建归档前可先验证已有版本的内容一致性，检查不会改写归档或证据：

```sh
python3 tool/package_catalog.py --check
python3 tool/package_catalog.py --package-root packages/im_l10n_catalog-0.2.1 --check
# PC 维护源升级到新版本后，去掉 --check 创建对应新归档。
```

本轮未向原项目pubspec添加外部path依赖，避免破坏SDK独立打包检查。生成工具是维护时依赖，源仓库中的生成结果是构建输入，运行时不读取整个公共catalog，也不下载语言包。

## A/B按需示例仍然保留

`examples/app_a` 和 `examples/app_b` 仍可运行。它们的源配置已固定公共包0.3.0，并用includeKeys保持原20/15词条范围。

| 示例 | 业务语言与模块 | 结果 |
| --- | --- | --- |
| A | en；common/auth/chat/settings，20词条 | 登录标题Sign in to App A，发送Send，包含Delete |
| B中的SDK | en/zh；common/chat/settings，每语言15词条 | 无auth和Delete，发送覆盖Send message/发送消息 |

```sh
python3 tool/demo.py --verify
# 需要重新构建Web产物时：
python3 tool/demo.py --verify --build-web
```

先前启动的本地服务仍使用保留的Web交付物，地址为 `http://127.0.0.1:8081` 和 `http://127.0.0.1:8082`。它们与真实项目接入无运行时耦合。业务翻译按构建清单选择，Flutter框架自带的Material/Cupertino翻译属于框架依赖，不在业务词库裁剪结论内。

## 验证与证据

`evidence/full-integration-*` 保存抽取前hash、逐值/结构等价、生成校验、测试和清理证据。41份生产ARB的所有译文、metadata及两端公开本地化API均与迁移前一致；PC六语言的数组、对象结构及fallback也一致。

移动端已通过106项既有定向测试和i18n guard，PC通过12项i18n测试、类型和边界检查。公共Dart生成器17项测试、资源导出器5项边界测试和A/B 5项界面测试通过。SDK先前的native hook缓存阻断已解决：固定Flutter 3.41.9重建项目内编译缓存，当前0.3.0的20项定向Flutter测试全部通过（含35语言加载、参数、共享映射/英语回退、宿主登录及返回按钮）；另一次缓存复用检查通过。完整新证据见 `evidence/native-hook-regression/`，旧失败日志保留为历史记录。

本轮没有执行真机、原生安装包发布或真实后端操作。只清理本次确认新建且闲置的精确构建缓存，保留已有其他任务现场、依赖、原有dirty和暂存状态，以及用户正在运行的预览。

## 版本交付

`deliverables/im_l10n_catalog-0.3.0.zip` 为本轮完整版本归档，包含源、导出器和生成工具。原0.1.0示例归档和0.2.0归档保持不变；这些归档随源码保存在本仓库，尚未发布到 pub.dev。

采用现有官方能力：[Flutter本地化生成](https://docs.flutter.dev/ui/internationalization)、[Dart依赖与版本](https://dart.dev/tools/pub/dependencies)。

## SDK 35语同步（0.3.0）

本轮保持SDK每语言1040个ARB key和旧六语译文，新增29语直接从公共模块选择，不复制App专属功能。SDK与Web的语言识别同步扩展，宿主可传对应语言；葡语区分pt-BR与pt-PT。SDK/Web专属文案仅在语义及占位符可匹配时复用公共译文，其余显式回退英语。法务正文、消息翻译服务支持的目标语言与历史业务页面硬编码不属于35语资源齐全的证明。详细覆盖、生成、检查和测试结果保存在 `evidence/sdk-35-locales/`。

0.3.0 本次验证：公共生成器/生产profile合同24项、导出边界5项、补充renderer5项、Flutter定向38项、Web既有54项与新35语专项6项均通过；浏览器35语切换保持输入并验证SDK自身RTL方向。生成结果的旧六语完整JSON和1040个公开调用签名保持一致。真实宿主、真机和35语全部页面视觉验收未执行。0.2.0先前的失败日志作为历史证据保留。
