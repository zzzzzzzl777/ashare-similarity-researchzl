# Contributing

感谢你愿意改进这个项目。

## 开始之前

- Python 版本要求：`>=3.11`
- 推荐环境：Windows 本机开发；核心 Python 代码也尽量保持跨平台
- 免费数据源存在限流、超时和口径差异，涉及数据层改动时请先跑本地回归

## 本地开发

如果你的仓库盘空间较小，先复制 `ashare_similarity.local.example.ps1` 为 `ashare_similarity.local.ps1`，并设置：

```powershell
$env:ASHARE_SIMILARITY_HOME = "E:\ashare_similarity_runtime"
```

源码模式下裸 `python -m ...` 会自动读取这个本地脚本，脚本入口和 CLI 才会使用同一个数据根。

```bash
pip install -e .[dev]
python -m pytest -q
python -m ashare_similarity.cli doctor
```

如果改动影响 Web 状态展示或运行时加速判断，补充做一次：

```bash
python -m ashare_similarity.cli serve --host 127.0.0.1 --port 8011
```

然后至少手动确认：

- `/api/healthz`
- `/api/status`
- `/api/search`

如果需要验证打包交付物：

```bash
python -m pip wheel . --no-deps -w dist
```

## 代码和变更建议

- 优先补测试，再改行为。
- 不要把 `data/` 下的真实缓存、索引和 DuckDB 文件提交到仓库。
- 不要提交 `ashare_similarity.local.ps1`；只提交 `ashare_similarity.local.example.ps1`。
- 正式交付前必须跑 `prepare_daily_ready.ps1`，而不是只跑 `QuickDemo` 或一轮小批量 `maintain`。
- Web 启动建议使用 `start_web.bat`；大批量维护前先停止 Web，避免 DuckDB 被占用。
- 涉及免费数据源的改动，要明确说明主源、回退链路和限制边界。
- 如果改动涉及索引后端或 GPU 路径，请同步说明“磁盘工件后端”和“运行时后端”是否发生了分离。

## 提交 Pull Request

- 标题写清楚变更意图，不要只写 “fix” 或 “update”
- 在描述里写明：
  - 改了什么
  - 为什么改
  - 怎么验证
  - 是否影响数据格式、CLI 或 Web 行为
- 如果改动影响用户操作，请同步更新 `README.md` 或相关文档

## 问题报告

提 issue 时请尽量附上：

- 操作系统和 Python 版本
- 启动命令
- `python -m ashare_similarity.cli doctor` 输出
- `python -m ashare_similarity.cli status --frequency daily` 输出
- 相关日志或报错截图
