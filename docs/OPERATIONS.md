# 运维与首次使用说明

## 首次使用

```bash
first_run.bat
```

或者手工分步：

```bash
python -m ashare_similarity.cli bootstrap --with-sample
python -m ashare_similarity.cli maintain --frequency daily --batch-size 10 --max-symbols-per-round 50 --max-rounds 1 --round-interval-seconds 0 --retry-failures-every 1
python -m ashare_similarity.cli doctor
start_web.bat
```

## 远程访问

- 在 Windows 本机或远程桌面里的浏览器打开：优先使用 `http://localhost:<port>/`
- 在 Mac 或其他机器的本机浏览器里访问 Windows 服务：显式用 `-BindHost 0.0.0.0` 启动后，再使用输出的 `http://<Windows局域网IP>:<port>/`
- 远程控制软件通常不会把 Windows 的 `localhost` 映射到你的本机浏览器，这属于正常现象

局域网模式示例：

```bash
powershell -ExecutionPolicy Bypass -File .\start_web.ps1 -BindHost 0.0.0.0
```

## 日常维护

- 先停止 Web，再跑 `maintain` 或批量 `build`
- 回填完成后重新执行 `start_web.bat`
- 免费数据覆盖不完整时，`doctor` 和 `/api/status` 会直观显示缓存规模、索引缺口和剩余 backlog

## 常见问题

### 首页打开后立刻报错

优先检查：

- 是否已经运行过 `bootstrap`
- 当前频段是否有缓存
- 当前窗口是否已有索引
- `python -m ashare_similarity.cli doctor` 是否通过默认查询烟测

### 只回填了一部分股票

这是免费数据模式下的正常现象。继续执行：

```bash
python -m ashare_similarity.cli maintain --frequency daily --batch-size 20 --max-symbols-per-round 100 --max-rounds 20 --round-interval-seconds 2 --retry-failures-every 5 --stop-after-idle-rounds 3
```

### DuckDB 被占用

如果看到数据库文件占用或索引构建失败，先停止 Web：

```bash
stop_web.bat
```

然后再跑维护命令。
