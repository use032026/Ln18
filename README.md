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

更新公共源后，在 Ln18 中执行：

```sh
python3 tool/sync_all.py --only sdk
```

它按移动端和SDK各自已固定的Flutter工具链生成资源并执行gen-l10n，同时导出PC词库。只校验、不改文件：

```sh
python3 tool/sync_all.py --only sdk --check
```

可用 `--only mobile`、`--only sdk`、`--only pc` 限定范围，也可用root参数指定其他机器上的仓库位置。没有对应源仓库时，公共包、A/B示例和已有SDK生成代码仍可单独查看或运行。

各原仓库也有维护入口：

```sh
# chat-im-cs/lpp/lpp_mobile
python3 tool/sync_l10n.py --catalog-root /Users/starburst/Desktop/Ln18/packages/im_l10n_catalog --check

# chat-im-cs/lpp/lpp_pc_client
python3 scripts/sync-l10n.py --catalog-root /Users/starburst/Desktop/Ln18/packages/im_l10n_catalog --check

# IMSDK
python3 scripts/sync_l10n.py --catalog-root /Users/starburst/Desktop/Ln18/packages/im_l10n_catalog --check
```

0.3.0 本轮只更新 SDK；chat-im-cs 移动/PC消费者仍固定0.2.0，应配合未变的0.2.0归档源使用。当前checkout请用 `python3 tool/sync_all.py --only sdk`，不要直接运行默认全消费者同步。

这些命令也支持环境变量 `IM_L10N_CATALOG_ROOT`。去掉 `--check` 更新生成资源；之后Flutter消费者执行自己的gen-l10n。只读check需要先准备公共包的Dart依赖，缺少依赖时会报错而不会自动写缓存。

## 日常维护与版本

1. 修改公共catalog中的翻译源；App专属差异保存在对应profile或独立消费者dataset。
2. 包版本、catalog版本、消费者声明一起升级；发布后的版本内容保持不变。
3. 运行同步、等价或本地化检查，以及受影响端的定向测试。
4. 提交公共包和对应消费者生成结果。SDK源码交付必须包含生成Dart/TS和收据。

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
