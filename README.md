# A股K线相似检索系统

这是一个本地可运行、离线优先的 A 股 K 线相似检索系统，目标是：

- 输入 `股票代码 + 截止日期 + K线周期 + 窗口长度`
- 在全市场历史窗口中检索最相似的 K 线片段
- 同时输出 `综合相似榜` 和 `形态最像榜`
- 为每个历史案例提供后续 `1/3/5/10` 个交易日的表现统计

系统采用“离线建库 + 本地秒级查询”的设计：

- 数据层：`AKShare / 东方财富免费接口`
- 存储层：`DuckDB + Parquet`
- 特征与检索：`NumPy / Pandas / Polars / Torch(CUDA 可选) / FAISS(可选) / sklearn`
- Web：`FastAPI + Jinja2 + ECharts`

## 先看真实状态

这几个判断比“功能很多”更重要：

- 这是本地单机工具，不是公开注册、多租户、对外 SaaS 平台。
- Web 侧主要负责查询、展示和导出；重任务默认放在 CLI 的 `backfill` / `backfill-loop` / `maintain` / `build` 里执行。
- 项目确实涉及并发与解耦问题，但当前不是任务队列、分布式调度、异步 worker 平台。
- 存储是真实的本地存储：`data/raw`、`data/cache`、`data/index` 和 `workspace.duckdb` 会持续增长，不应该提交到 GitHub。
- 免费数据边界是真约束，不是文档客套话。日线是“逐步回填后尽可能全”，分钟线是“近期窗口可用”，不是“全历史随时可查”。
- GPU 不是硬性依赖，但运行时已经支持“有条件自动加速”。默认索引工件仍可落为 CPU 兼容格式；如果本机存在可用 CUDA / Torch 运行环境，查询阶段会优先切到 GPU 精确检索，并在 `doctor` 与 `/api/status` 中明确展示真实运行时后端。

默认数据目录不再依赖当前工作目录：

- 可通过环境变量 `ASHARE_SIMILARITY_HOME` 指定数据根目录
- 源码仓库运行时如果存在被 gitignore 的 `ashare_similarity.local.ps1`，会自动读取其中的 `ASHARE_SIMILARITY_HOME`
- 源码仓库没有本地配置时才回退到仓库内 `data/`
- wheel 安装后默认使用用户目录下 `.ashare_similarity/data`

## 哪些担忧和本项目相关

相关：

- 并发与前后台解耦：查询请求不应顺手触发重建或大规模回填
- 异步边界：Web 路由是 `async`，但核心维护流程并不是独立的异步任务系统
- 存储设计：Parquet 落时序数据，DuckDB 记元数据、状态和失败样本
- 大文件增长：原始行情、索引矩阵、导出结果都会持续变大
- 免费数据可靠性：上游限流、网络抖动、分钟历史范围不足都会直接影响可用性
- 性能与 GPU：支持“CPU 兼容工件 + 运行时 GPU 提升”的混合模式，实际是否启用以 `doctor` 和 `/api/status` 的运行时字段为准

当前不相关：

- 用户注册 / 登录 / 权限体系
- 邮件验证码、自建邮件投递、短信验证
- IP 池、批量注册、反垃圾注册链路
- UGC 发帖、评论审核、内容安全
- 公网多租户隔离、账单、SaaS 控制面

如果以后要做成公网 SaaS，这些当然都重要；但它们不应该掩盖当前仓库真正需要先做扎实的本地检索、回填、索引和交付质量问题。更完整的范围说明见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 当前能力

- 日线：支持本地缓存、相似检索、自动回填、索引重建
- 分钟线：支持免费接口可覆盖的近期数据，并会明确提示历史范围限制
- 免费多源策略：日线默认走东方财富，失败时回退到新浪；指数默认走新浪，失败时回退到腾讯；分钟线默认走东方财富，失败时回退到新浪
- 检索方式：ANN 召回 + 价格路径/蜡烛几何/量能/环境精排
- 运维能力：支持可恢复回填、失败样本追踪、状态查看、自动化维护命令
- 交付能力：包含 LICENSE、贡献指南、行为准则、安全说明、CI、Issue/PR 模板

## 安装

推荐先安装开发依赖：

```bash
pip install -e .[dev]
```

如果你当前 Python 环境可用 `faiss-cpu`，也可以安装：

```bash
pip install -e .[dev,faiss]
```

如果你需要验证正式可安装交付物，也可以直接构建 wheel：

```bash
python -m pip wheel . --no-deps -w dist
```

## 快速开始

最省心的首次启动方式是直接运行：

```bash
first_run.bat
```

它会自动执行：

- 停止已有 Web 服务
- `bootstrap` 初始化股票池和基础环境
- `prepare_daily_ready.ps1` 全量准备免费日线缓存和默认索引
- 启动本地 Web

这不是几秒钟的 demo 初始化。首次全量准备会持续拉取免费日线数据、构建 `5/8/10/20` 默认窗口索引，并写入 `run_logs/daily_ready.json`；如果只是想快速 smoke test，请运行：

```bash
first_run.bat -QuickDemo
```

如果你想手工分步执行，再按下面的方式来。

1. 初始化股票池和基础市场环境：

```bash
python -m ashare_similarity.cli bootstrap
```

2. 正式准备全量免费日线缓存与默认索引：

```bash
prepare_daily_ready.bat
```

这一步会：

- 持续回填全 A 去噪股票池内免费可得的日线历史数据
- 自动重试失败样本并记录最近失败原因
- 自动重建默认日线 `5/8/10/20` 索引
- 要求 `cached_symbols == filtered_universe_count`，且默认窗口没有 missing/stale 工件

如果你只是做 demo 或开发 smoke test，可以改用：

```bash
first_run.bat -QuickDemo
```

3. 跑一次自检，确认当前环境是否达到“可直接查询”的状态：

```bash
python -m ashare_similarity.cli doctor
```

这个命令会检查：

- 数据目录和 DuckDB 是否就绪
- 当前缓存覆盖规模
- 默认窗口索引是否齐全
- 默认查询能否直接返回结果
- 当前索引工件后端是什么
- 查询运行时是否真的切到了 GPU / CUDA
- 运行时后端与磁盘工件后端是否一致

4. 推荐用一键脚本启动 Web：

```bash
start_web.bat
```

脚本会自动：

- 选择可用端口
- 等待服务健康检查通过
- 输出可访问地址
- 自动打开浏览器

5. 如果你更喜欢命令行方式，正式启动入口是：

```bash
python -m ashare_similarity.cli serve --host 127.0.0.1 --port 8011
```

wheel 安装后也可以直接使用：

```bash
ashare-similarity serve --host 127.0.0.1 --port 8011
```

6. 打开脚本或命令输出的地址。对“本机直接打开”的场景，优先使用：

```text
http://localhost:8011
http://127.0.0.1:8011
```

如果你显式以局域网模式启动，再使用：

```text
http://<你的局域网IP>:8011
```

7. 停止 Web：

```bash
stop_web.bat
```

开发调试时才建议继续使用：

```bash
uvicorn ashare_similarity.app:create_app --factory --reload
```

## 推荐维护流程

正式使用时，更推荐直接跑维护命令，而不是分散手工执行。

维护建议：

- 先停止 Web 再跑 `maintain` 或批量 `build`，避免 DuckDB 文件被长时间占用
- 维护完成后再重新执行 `start_web.bat`

### 1. 自动回填并按需重建索引

```bash
python -m ashare_similarity.cli maintain --frequency daily --batch-size 20 --max-symbols-per-round 100 --max-rounds 20 --round-interval-seconds 2 --retry-failures-every 5 --stop-after-idle-rounds 3
```

这个命令会：

- 多轮执行可恢复的回填任务
- 自动沿用同一个未完成 run
- 周期性重试失败样本
- 当有新缓存样本或索引缺失时，自动重建默认窗口索引

默认索引窗口：

- 日线：`5 / 8 / 10 / 20`
- 分钟线：`60 / 120 / 240`

### 2. 查看状态

```bash
python -m ashare_similarity.cli status
python -m ashare_similarity.cli status --frequency daily
python -m ashare_similarity.cli doctor
```

可查看：

- 当前股票池规模
- 各周期缓存数量
- 最近一次回填状态
- 最近一次索引构建信息
- 当前索引工件后端与运行时真实加速状态

### 3. 只执行回填

```bash
python -m ashare_similarity.cli backfill-loop --frequency daily --batch-size 20 --max-symbols-per-round 100 --max-rounds 20 --round-interval-seconds 2
```

### 4. 强制重建索引

```bash
python -m ashare_similarity.cli maintain --frequency daily --max-rounds 1 --max-symbols-per-round 1 --round-interval-seconds 0 --force-rebuild
```

## 常用命令

### 搜索相似 K 线

```bash
python -m ashare_similarity.cli search --symbol 000333 --end-date 2026-04-23 --frequency daily --window-size 10 --top-k 10
```

### 手工构建指定窗口索引

```bash
python -m ashare_similarity.cli build --frequency daily --window-size 5
python -m ashare_similarity.cli build --frequency daily --window-size 8
python -m ashare_similarity.cli build --frequency daily --window-size 10
python -m ashare_similarity.cli build --frequency daily --window-size 20
```

## Web 功能

首页包含四个固定区域：

- 目标 K 线
- 综合相似榜
- 形态最像榜
- 后续表现汇总

同时支持：

- 导出 CSV
- 导出 HTML
- 查看本地缓存和回填进度状态
- 查看运行时加速状态，包括 `active_backend / artifact_backend / active_device / gpu_enabled`
- 前端图表资源本地打包，不依赖外部 CDN

## 远程访问与虚拟机说明

如果你是“Mac 远程控制 Windows 台式机 / 虚拟机”的使用方式，请区分两种入口：

- 在 Windows 远程桌面里的浏览器打开：优先使用 `http://localhost:<port>/`
- 在 Mac 本机浏览器直接访问 Windows 服务：只有你显式以局域网模式启动时，才使用启动脚本输出的 `http://<Windows局域网IP>:<port>/`

很多远程控制场景不会把 Windows 的 `localhost` 直接映射到 Mac 本机浏览器，所以“Windows 里能开 localhost，Mac 里不能开 localhost”是正常现象，不代表 Web 没启动。

## 安全边界

默认启动方式优先绑定 `127.0.0.1`，也就是仅本机访问。

如果你显式改成 `0.0.0.0` 或局域网 IP 模式，请注意：

- 当前 Web 没有登录、权限、限流或多用户隔离
- `/api/search`、`/api/export/*`、`/api/status` 都是本地工具接口，不是公网服务接口
- 只应在受信任网络和受控防火墙环境下启用局域网访问

如果你确实需要 LAN 模式，可以显式执行：

```bash
powershell -ExecutionPolicy Bypass -File .\start_web.ps1 -BindHost 0.0.0.0
```

## GitHub 交付与报障方式

这个仓库已经补齐了适合公开放 GitHub 的基础资产：

- `LICENSE`: MIT
- `CONTRIBUTING.md`: 本地开发、验证和提 PR 规范
- `CODE_OF_CONDUCT.md`: 协作行为约定
- `SECURITY.md`: 安全问题提报说明
- `.github/workflows/ci.yml`: Windows 上的自动测试与打包
- `.github/ISSUE_TEMPLATE` 与 `.github/pull_request_template.md`: issue / PR 模板
- `.editorconfig` 与 `.gitattributes`: 编码、换行和仓库文本规则

如果你要提 bug，先带上这些最有用的信息：

```bash
python -m ashare_similarity.cli doctor
python -m ashare_similarity.cli status --frequency daily
```

如果问题与分钟线有关，再补充对应频段的 `status` / `doctor` 输出，并说明：

- 频段
- 窗口大小
- 股票代码
- 截止日期
- 是否使用了局域网模式 / 代理 / VPN

不要提交这些内容到 GitHub：

- `data/` 下的真实缓存和索引
- `*.duckdb`
- `run_logs/`
- 导出的 CSV / HTML 报告
- 带内网 IP、代理、VPN 或本机绝对路径的敏感环境信息

数据与提交流程边界见 [docs/DATA_BOUNDARY.md](docs/DATA_BOUNDARY.md)。

## 项目结构

- `src/ashare_similarity/data`: 数据源适配、缓存、股票池、回填任务
- `src/ashare_similarity/context`: 大盘与行业环境特征
- `src/ashare_similarity/features`: 滚动切窗、质量过滤、特征编码
- `src/ashare_similarity/indexing`: 向量索引和索引落盘
- `src/ashare_similarity/search`: 相似检索、精排、聚合统计
- `src/ashare_similarity/web`: Web 路由和页面入口
- `src/ashare_similarity/static` 与 `src/ashare_similarity/templates`: 包内前端资源
- `tests`: 单元测试、API 测试、维护链路测试

## 免费数据源边界

这是正式能力边界，不建议忽略：

- 日线：在免费模式下可以做到“尽可能全”的本地缓存和检索，但稳定性仍受公开源网络状况影响
- 分钟线：仅适合做“近期历史窗口”检索
- `1` 分钟数据通常只能稳定覆盖最近 `5` 个交易日
- 东方财富免费接口在部分网络环境下可能偶发代理断连或超时
- 新浪免费接口可作为备线，但大量抓取同样可能触发限流或封禁
- 免费源之间的复权口径和成交量细节可能存在差异，不应与专业付费源混用做精确回测

系统已经为这些情况做了处理：

- 单只股票失败不会拖垮整批回填
- 失败样本会记录到 DuckDB，可用于后续重试
- 状态页和状态命令会显示最新失败样本
- 回填默认走多级 fallback，不再只依赖单一免费接口

## 验证

建议在每次较大改动后执行：

```bash
python -m pytest -q
```

更详细的首次使用和运维说明见：[docs/OPERATIONS.md](docs/OPERATIONS.md)  
架构和范围说明见：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)  
路线图见：[ROADMAP.md](ROADMAP.md)  
版本策略见：[docs/VERSIONING.md](docs/VERSIONING.md)  
数据边界见：[docs/DATA_BOUNDARY.md](docs/DATA_BOUNDARY.md)  
发布前检查见：[docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md)

## 概率预测研究信号

预测模块只输出研究型概率信号，不输出买入/卖出建议。当前短线预测研究范围固定为 `主板日线`，默认寻找高换手、高成交额、高波动的主板短线异动阶段样本；单只股票当前日必须同时满足换手、成交额/量能和波动门槛，并且最近 3 个交易日至少 2 天也满足这些阶段门槛。预测证据严格使用 `historical`，不会使用目标日期之后的数据作为输入。

```bash
python -m ashare_similarity.cli predict --symbol 晶科科技 --as-of 2026-04-23 --top-k 100
python -m ashare_similarity.cli backtest-prediction --start 2020-01-01 --end 2026-04-23 --sample-size 50000 --target-accuracy 0.75
python -m ashare_similarity.cli gpu-prediction-probe --start 2020-01-01 --train-end 2024-12-31 --test-start 2025-01-01 --end 2026-04-23
python -m ashare_similarity.cli train-prediction
```

Web 首页的“生成概率预测”会调用 `/api/predict`，展示未来 1/2 个交易日的上涨概率、收益区间、短线点火因子、主板涨停结构、相似历史证据、模型诊断和运行时加速状态。

验收规则是硬约束：主板短线历史样本的方向准确率必须达到 `75%` 且概率校准优于基线，否则页面继续显示“实验态/未通过验收”，不会把结果包装成可交易信号。`50,000` 个测试样本是期望规模和报告目标，不再作为硬性通过门槛；若严格异动阶段样本不足 50,000，会使用可用样本并在结果中标记样本量目标未达成。

`gpu-prediction-probe` 会把 `--target-accuracy` 低于 `0.75` 的输入提升到 `0.75`；`--test-rows` 表示期望/最多抽样测试规模，默认 `50,000`。训练集按次日标签日期切分，避免训练样本的标签跨入测试期。探针会在 `data/reports/prediction/gpu_probe_latest.json` 写入最新验收结果，只有通过准确率和 Brier 硬约束时才额外写入 `gpu_probe_passed_latest.json`，后续全局拟合必须读取该门禁文件。

全量探针默认启用特征缓存，会把横截面特征完成后的样本矩阵写入 `data/reports/prediction/feature_cache/`。调整模型、epochs、训练采样或阈值时会优先复用缓存；变更因子 schema、日期、短线过滤或股票池后会使用新的 fingerprint。可用 `--refresh-feature-cache` 强制重建，或 `--no-feature-cache` 关闭缓存。桌面 `因子探索.md` 中已筛过的 P0 日线因子会先进入 GPU 探针；分钟、资金流、跨市场和情绪因子需要独立数据缓存和披露时点测试后再加入正式验收。

当前实现会尽量让 ANN 召回走 Torch CUDA；`gpu-prediction-probe` 的特征矩阵、Torch 模型训练会使用 CUDA，XGBoost 候选会请求 CUDA hist 后端。AKShare 回填、Parquet/DuckDB I/O、部分 Pandas 横截面整理、XGBoost NumPy 桥接、DTW 精排、标签生成、JSON 验收落盘和 sklearn 校准仍在 CPU 侧执行，并在诊断里明确展示，不伪装成全链路 GPU。
