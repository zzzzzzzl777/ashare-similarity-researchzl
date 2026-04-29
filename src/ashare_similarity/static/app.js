const state = {
  response: null,
  responseSignature: null,
  responseDirty: false,
  predictionSignature: null,
  systemStatus: null,
  symbolHints: null,
  queryChart: null,
  matchCharts: [],
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatPct(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "--";
  const number = Number(value);
  const prefix = number > 0 ? "+" : "";
  return `${prefix}${number.toFixed(2)}%`;
}

function formatProbability(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "--";
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function formatScore(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "--";
  return Number(value * 100).toFixed(2);
}

function formatDistance(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "--";
  return Number(value).toFixed(4);
}

function formatPlainNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "--";
  return Number(value).toFixed(digits);
}

function formatBoardStage(value) {
  const labels = {
    none: "非连板",
    first_board: "首板",
    second_board: "二板",
    multi_board: "三板及以上",
  };
  return labels[String(value || "none")] || String(value || "--");
}

function formatDateTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("zh-CN", { hour12: false });
}

function formatDateLabel(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return date.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" }).replace("/", "-");
}

function formatFullDate(value) {
  if (!value) return "--";
  const raw = String(value);
  if (/^\d{4}-\d{2}-\d{2}/.test(raw)) return raw.slice(0, 10);
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return raw.slice(0, 10);
  return date.toLocaleDateString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" }).replaceAll("/", "-");
}

function formatDateRange(start, end) {
  return `${formatFullDate(start)} 至 ${formatFullDate(end)}`;
}

function formatBackfillStatus(status) {
  const labels = {
    running: "运行中",
    completed: "已完成",
    partial: "部分完成",
  };
  return labels[status] || status || "--";
}

function formatFrequency(value) {
  const labels = {
    daily: "日线",
    1: "1分钟",
    5: "5分钟",
    15: "15分钟",
    30: "30分钟",
    60: "60分钟",
  };
  return labels[value] || value || "--";
}

function formatIndexBackend(value) {
  const labels = {
    faiss: "FAISS 向量索引",
    "faiss-gpu": "FAISS GPU 向量索引",
    "sklearn-nearest": "sklearn 最近邻索引",
    "torch-cuda-bruteforce": "Torch CUDA 精确检索",
    "torch-cpu-bruteforce": "Torch CPU 精确检索",
  };
  return labels[value] || value || "--";
}

function normalizeSymbol(value) {
  const raw = String(value ?? "").trim();
  if (!raw) return "";
  return /^\d+$/.test(raw) ? raw.padStart(6, "0") : raw;
}

function formSignature(formData) {
  return JSON.stringify({
    symbol: normalizeSymbol(formData.symbol),
    end_date: String(formData.end_date || ""),
    frequency: String(formData.frequency || "daily"),
    window_size: Number(formData.window_size || 0),
    top_k: Number(formData.top_k || 0),
    search_scope: String(formData.search_scope || "historical"),
  });
}

function exactCachedSymbolMatch(frequency, symbol) {
  const normalized = normalizeSymbol(symbol);
  if (!normalized) return null;
  if (!state.symbolHints) return null;
  if (String(state.symbolHints.frequency || "") !== String(frequency || "")) return null;
  if (normalizeSymbol(state.symbolHints.query || "") !== normalized) return null;
  return state.symbolHints.exact_match || null;
}

function setPrepareResult(message = "", kind = "warn") {
  const box = document.getElementById("prepare-result");
  if (!box) return;
  if (!message) {
    box.hidden = true;
    box.textContent = "";
    box.dataset.kind = "idle";
    return;
  }
  box.hidden = false;
  box.dataset.kind = kind;
  box.innerHTML = message;
}

function renderSymbolHint(form, payload) {
  const helper = document.getElementById("symbol-helper");
  const dataList = document.getElementById("symbol-suggestions");
  const randomButton = document.getElementById("random-symbol-button");
  const prepareButton = document.getElementById("prepare-symbol-button");
  const frequency = String(payload?.frequency || form.elements.namedItem("frequency")?.value || "daily");
  const normalizedQuery = normalizeSymbol(payload?.query || form.elements.namedItem("symbol")?.value || "");
  const totalCached = Number(payload?.total_cached ?? 0);
  const items = Array.isArray(payload?.items) ? payload.items : [];
  const exactMatch = payload?.exact_match || null;
  const sampleText = items
    .slice(0, 4)
    .map((item) => `${escapeHtml(item.symbol)}${item.name ? ` · ${escapeHtml(item.name)}` : ""}`)
    .join("、");

  dataList.innerHTML = items
    .flatMap((item) => {
      const codeOption = `<option value="${escapeHtml(item.symbol)}" label="${escapeHtml(item.name || "")}">${escapeHtml(item.symbol)}${item.name ? ` · ${escapeHtml(item.name)}` : ""}</option>`;
      if (!item.name) return [codeOption];
      return [
        codeOption,
        `<option value="${escapeHtml(item.name)}" label="${escapeHtml(item.symbol)}">${escapeHtml(item.name)} · ${escapeHtml(item.symbol)}</option>`,
      ];
    })
    .join("");

  if (totalCached <= 0) {
    helper.innerHTML = `当前${escapeHtml(formatFrequency(frequency))}还没有本地缓存，请先补数据后再查。`;
  } else if (normalizedQuery && exactMatch) {
    helper.innerHTML = `
      <strong>${escapeHtml(exactMatch.symbol)}${exactMatch.name ? ` · ${escapeHtml(exactMatch.name)}` : ""}</strong>
      已在${escapeHtml(formatFrequency(frequency))}本地缓存中，可直接检索。当前共缓存 ${totalCached} 只标的${sampleText ? `；也可以试试 ${sampleText}` : ""}。
    `;
  } else if (normalizedQuery) {
    helper.innerHTML = `
      当前输入 <strong>${escapeHtml(normalizedQuery)}</strong> 还没有精确匹配的本地缓存。当前${escapeHtml(formatFrequency(frequency))}已缓存 ${totalCached} 只标的
      ${sampleText ? `，可先试 ${sampleText}` : ""}，或者点击“补齐当前股票”。
    `;
  } else {
    helper.innerHTML = `当前${escapeHtml(formatFrequency(frequency))}已缓存 ${totalCached} 只标的${sampleText ? `，可直接试 ${sampleText}` : ""}。`;
  }

  randomButton.disabled = items.length === 0;
  prepareButton.disabled = !normalizeSymbol(form.elements.namedItem("symbol")?.value || "") || !form.elements.namedItem("end_date")?.value;
}

async function loadCachedSymbolHints(form, { query = null, limit = 12, force = false } = {}) {
  const frequency = String(form.elements.namedItem("frequency")?.value || "daily");
  const normalizedQuery = normalizeSymbol(query ?? (form.elements.namedItem("symbol")?.value || ""));
  if (
    !force &&
    state.symbolHints &&
    String(state.symbolHints.frequency || "") === frequency &&
    normalizeSymbol(state.symbolHints.query || "") === normalizedQuery
  ) {
    renderSymbolHint(form, state.symbolHints);
    return state.symbolHints;
  }

  const params = new URLSearchParams({ frequency, limit: String(limit) });
  if (normalizedQuery) {
    params.set("q", normalizedQuery);
  }
  const response = await fetch(`/api/cached-symbols?${params.toString()}`);
  if (!response.ok) {
    throw new Error("无法读取可用标的列表");
  }
  const payload = await response.json();
  state.symbolHints = payload;
  renderSymbolHint(form, payload);
  return payload;
}

function expectedWindowsForFrequency(frequency) {
  return frequency === "daily" ? [5, 8, 10, 20] : [60, 120, 240];
}

function builtWindowsForFrequency(status, frequency) {
  const explicit = status?.index_health?.[frequency]?.built_windows;
  if (Array.isArray(explicit)) {
    return explicit.map((item) => Number(item)).sort((left, right) => left - right);
  }
  return indexEntriesForFrequency(status, frequency)
    .map((item) => Number(item.window_size))
    .sort((left, right) => left - right);
}

function indexEntriesForFrequency(status, frequency) {
  return Object.values(status?.index_status || {}).filter(
    (item) => item.frequency === frequency && item.window_size !== null && item.window_size !== undefined,
  );
}

function indexSymbolCount(item) {
  return Number(item?.metadata?.symbol_count ?? item?.symbol_count ?? 0);
}

function isIndexEntryStale(status, frequency, item) {
  if (typeof item?.stale === "boolean") {
    return item.stale;
  }

  const explicit = status?.index_health?.[frequency]?.stale_windows;
  if (Array.isArray(explicit) && item?.window_size !== null && item?.window_size !== undefined) {
    const windowSize = Number(item.window_size);
    return explicit.map((value) => Number(value)).includes(windowSize);
  }

  const cachedSymbols = Number(status?.cache_status?.[frequency]?.cached_symbols ?? 0);
  const symbolCount = indexSymbolCount(item);
  if (cachedSymbols > 0 && symbolCount > 0 && symbolCount < cachedSymbols) {
    return true;
  }

  const cacheLatestDataAt = status?.cache_status?.[frequency]?.data_freshness?.latest_data_at;
  const builtLatestDataAt = item?.metadata?.built_from?.latest_data_at;
  if (cacheLatestDataAt && builtLatestDataAt) {
    const cacheTime = new Date(cacheLatestDataAt);
    const builtTime = new Date(builtLatestDataAt);
    if (!Number.isNaN(cacheTime.getTime()) && !Number.isNaN(builtTime.getTime()) && builtTime < cacheTime) {
      return true;
    }
  }

  return false;
}

function staleWindowsForFrequency(status, frequency) {
  const explicit = status?.index_health?.[frequency]?.stale_windows;
  if (Array.isArray(explicit)) {
    return explicit.map((item) => Number(item)).sort((left, right) => left - right);
  }
  return indexEntriesForFrequency(status, frequency)
    .filter((item) => isIndexEntryStale(status, frequency, item))
    .map((item) => Number(item.window_size))
    .sort((left, right) => left - right);
}

function missingWindowsForFrequency(status, frequency) {
  const explicit = status?.index_health?.[frequency]?.missing_windows;
  if (Array.isArray(explicit)) {
    return explicit.map((item) => Number(item)).sort((left, right) => left - right);
  }
  return expectedWindowsForFrequency(frequency).filter((windowSize) => !builtWindowsForFrequency(status, frequency).includes(windowSize));
}

function currentIndexSymbolCountForFrequency(status, frequency) {
  const explicit = Number(status?.index_health?.[frequency]?.current_index_symbol_count ?? 0);
  if (explicit > 0) return explicit;
  return indexEntriesForFrequency(status, frequency).reduce((maxValue, item) => Math.max(maxValue, indexSymbolCount(item)), 0);
}

function isPartialIndexResponse(response) {
  const frequency = String(response?.query_meta?.frequency || "daily");
  const windowSize = Number(response?.query_meta?.window_size ?? 0);
  if (staleWindowsForFrequency(state.systemStatus, frequency).includes(windowSize)) {
    return true;
  }
  if (Array.isArray(response?.warnings)) {
    return response.warnings.some((item) => {
      const message = String(item || "");
      return message.includes("索引") || message.toLowerCase().includes("stale");
    });
  }
  return false;
}

function readinessForForm(status, formData) {
  if (!status) {
    return {
      ready: true,
      warning: true,
      reason: "status_unavailable",
      message: "系统状态暂时不可用，本次会直接尝试检索；如果失败，再根据错误提示补缓存或重建索引。",
    };
  }

  const frequency = String(formData.frequency || "daily");
  const symbol = normalizeSymbol(formData.symbol);
  const windowSize = Number(formData.window_size);
  const cachedSymbols = Number(status.cache_status?.[frequency]?.cached_symbols ?? 0);
  if (cachedSymbols <= 0) {
    return {
      ready: false,
      reason: "no_cache",
      message: `当前${formatFrequency(frequency)}还没有本地缓存，请先运行 bootstrap 和 maintain。`,
    };
  }

  const builtWindows = builtWindowsForFrequency(status, frequency);
  if (!builtWindows.includes(windowSize)) {
    return {
      ready: false,
      reason: "missing_index",
      message: `当前缺少 ${formatFrequency(frequency)} 窗口 ${windowSize} 的索引，请先运行 maintain 或 build。`,
    };
  }

  if (symbol) {
    const exactMatch = exactCachedSymbolMatch(frequency, symbol);
    const hintQueryMatches =
      state.symbolHints &&
      String(state.symbolHints.frequency || "") === frequency &&
      normalizeSymbol(state.symbolHints.query || "") === symbol;
    if (hintQueryMatches && !exactMatch) {
      return {
        ready: false,
        reason: "missing_symbol_cache",
        message: `标的 ${symbol} 在所选区间内没有本地缓存，可先随机一个可用标的，或点击“补齐当前股票”。`,
      };
    }
  }

  const selectedEntry = indexEntriesForFrequency(status, frequency).find((item) => Number(item.window_size) === windowSize);
  const selectedSymbolCount = indexSymbolCount(selectedEntry);
  if (selectedEntry && isIndexEntryStale(status, frequency, selectedEntry)) {
    return {
      ready: false,
      reason: "stale_index",
      message:
        selectedSymbolCount > 0 && selectedSymbolCount < cachedSymbols
          ? `当前 ${formatFrequency(frequency)} 窗口 ${windowSize} 的索引只覆盖 ${selectedSymbolCount}/${cachedSymbols} 只标的。为避免误导，请先离线重建索引。`
          : `当前 ${formatFrequency(frequency)} 窗口 ${windowSize} 的索引早于本地最新行情缓存，请先离线重建对应窗口索引。`,
    };
  }

  return { ready: true, message: "系统已就绪，可以开始检索。" };
}

function setStatus(message, kind = "idle") {
  const box = document.getElementById("status-box");
  box.textContent = message;
  box.dataset.kind = kind;
}

function commandCard(label, command) {
  return `
    <div class="command-card">
      <span>${escapeHtml(label)}</span>
      <code>${escapeHtml(command)}</code>
    </div>
  `;
}

function buildSetupCommands(status, formData, readiness) {
  const commands = [];
  const frequency = String(formData.frequency || "daily");
  const symbol = normalizeSymbol(formData.symbol || "");
  const windowSize = Number(formData.window_size || 10);
  const cachedSymbols = Number(status?.cache_status?.[frequency]?.cached_symbols ?? 0);
  const builtWindows = builtWindowsForFrequency(status, frequency);
  const staleWindows = staleWindowsForFrequency(status, frequency);

  if (readiness.reason === "missing_symbol_cache") {
    commands.push(commandCard("直接在页面里补齐当前股票", "点击“补齐当前股票”按钮"));
    commands.push(commandCard("换成一个可立即查询的标的", "点击“随机可用标的”按钮"));
    if (symbol) {
      commands.push(
        commandCard(
          "如果你更习惯命令行补单只股票",
          `python -m ashare_similarity.cli backfill --frequency ${frequency} --max-symbols 1 --symbols ${symbol} --end-date ${formData.end_date}`,
        ),
      );
    }
    return {
      message: readiness.message,
      html: commands.join(""),
    };
  }

  if (Number(status?.universe_count ?? 0) <= 0) {
    commands.push(commandCard("初始化股票池和基础环境", "python -m ashare_similarity.cli bootstrap --with-sample"));
  }
  if (cachedSymbols <= 0) {
    if (frequency === "daily") {
      commands.push(
        commandCard(
          "回填一批日线样本并自动建索引",
          "python -m ashare_similarity.cli maintain --frequency daily --batch-size 10 --max-symbols-per-round 50 --max-rounds 1 --round-interval-seconds 0 --retry-failures-every 1",
        ),
      );
    } else {
      commands.push(
        commandCard(
          `回填 ${formatFrequency(frequency)} 缓存`,
          `python -m ashare_similarity.cli backfill-loop --frequency ${frequency} --batch-size 20 --max-symbols-per-round 50 --max-rounds 5 --round-interval-seconds 2`,
        ),
      );
    }
  }
  if (!builtWindows.includes(windowSize) || staleWindows.includes(windowSize)) {
    commands.push(
      commandCard(
        `重建 ${formatFrequency(frequency)} 窗口 ${windowSize} 索引`,
        `python -m ashare_similarity.cli maintain --frequency ${frequency} --max-rounds 1 --max-symbols-per-round 1 --round-interval-seconds 0 --force-rebuild --window-sizes ${windowSize}`,
      ),
    );
  }
  commands.push(commandCard("完成后再跑一次自检", "python -m ashare_similarity.cli doctor"));
  commands.push(commandCard("然后启动 Web", "start_web.bat"));

  return {
    message: readiness.message,
    html: commands.join(""),
  };
}

function renderSetupState(formData, readiness) {
  const setup = buildSetupCommands(state.systemStatus, formData, readiness);
  const queryChart = document.getElementById("query-chart");
  const aggregate = document.getElementById("aggregate-table");
  const balanced = document.getElementById("balanced-list");
  const shape = document.getElementById("shape-list");

  if (state.queryChart && !state.queryChart.isDisposed()) {
    state.queryChart.dispose();
    state.queryChart = null;
  }

  document.getElementById("query-summary").textContent = "当前查询还不能直接执行";
  document.getElementById("query-badges").innerHTML = [
    `<span class="badge-chip">${escapeHtml(formatFrequency(formData.frequency || "daily"))}</span>`,
    `<span class="badge-chip">窗口 ${escapeHtml(formData.window_size || "10")}</span>`,
    `<span class="badge-chip">准备模式</span>`,
  ].join("");
  document.getElementById("response-notices").innerHTML = `
    <article class="notice-card warn">
      <strong>还差前置步骤</strong>
      <p>${escapeHtml(setup.message)}</p>
    </article>
  `;
  queryChart.innerHTML = `
    <section class="setup-panel">
      <h3>首次使用准备清单</h3>
      <p>当前页面不会盲目发起查询；先把缺失的缓存或索引补齐，再回来就能直接搜。</p>
      <div class="command-stack">${setup.html}</div>
    </section>
  `;
  aggregate.innerHTML = '<section class="setup-placeholder"><strong>后续表现汇总</strong><p>准备完成后，这里会展示综合相似榜样本的聚合统计。</p></section>';
  balanced.classList.remove("empty-state");
  shape.classList.remove("empty-state");
  balanced.innerHTML = '<section class="setup-placeholder"><strong>综合相似榜</strong><p>准备完成后，这里会展示价格路径、蜡烛几何、量能与环境的综合排序结果。</p></section>';
  shape.innerHTML = '<section class="setup-placeholder"><strong>形态最像榜</strong><p>准备完成后，这里会展示更强调形态轮廓和蜡烛结构的历史样本。</p></section>';
}

function updateLeaderboardTitles(topK = null) {
  document.getElementById("balanced-title").textContent = topK ? `综合相似榜（Top ${topK}）` : "综合相似榜";
  document.getElementById("shape-title").textContent = topK ? `形态最像榜（Top ${topK}）` : "形态最像榜";
}

function serializeForm(form) {
  const formData = new FormData(form);
  return Object.fromEntries(formData.entries());
}

function applyUrlParamsToForm(form) {
  const params = new URLSearchParams(window.location.search);
  ["symbol", "end_date", "frequency", "window_size", "top_k", "search_scope"].forEach((key) => {
    const value = params.get(key);
    if (!value) return;
    const field = form.elements.namedItem(key);
    if (field) field.value = value;
  });
}

function persistQueryToUrl(formData) {
  const params = new URLSearchParams();
  Object.entries(formData).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      params.set(key, String(value));
    }
  });
  const query = params.toString();
  const url = query ? `${window.location.pathname}?${query}` : window.location.pathname;
  window.history.replaceState({}, "", url);
}

function chartOption(series, title) {
  const dates = series.dates || [];
  const candleData = dates.map((_, index) => [
    series.open[index],
    series.close[index],
    series.low[index],
    series.high[index],
  ]);

  return {
    backgroundColor: "transparent",
    animationDuration: 450,
    title: {
      text: title,
      left: 12,
      top: 10,
      textStyle: { color: "#f6f3ea", fontSize: 15, fontWeight: 600 },
    },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross" },
    },
    grid: [
      { left: 30, right: 18, top: 50, height: "56%" },
      { left: 30, right: 18, top: "74%", height: "14%" },
    ],
    xAxis: [
      {
        type: "category",
        data: dates,
        boundaryGap: true,
        axisLabel: {
          color: "#b8b0a2",
          formatter: (value) => formatDateLabel(value),
          showMinLabel: true,
          showMaxLabel: true,
        },
        axisLine: { lineStyle: { color: "rgba(255,255,255,0.12)" } },
      },
      {
        type: "category",
        gridIndex: 1,
        data: dates,
        axisLabel: { show: false },
        axisLine: { show: false },
      },
    ],
    yAxis: [
      {
        scale: true,
        axisLabel: { color: "#b8b0a2" },
        splitLine: { lineStyle: { color: "rgba(255,255,255,0.08)" } },
      },
      {
        gridIndex: 1,
        axisLabel: { color: "#b8b0a2" },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "目标窗口",
        type: "candlestick",
        data: candleData,
        itemStyle: {
          color: "#ef6f51",
          color0: "#33b18a",
          borderColor: "#ef6f51",
          borderColor0: "#33b18a",
        },
      },
      {
        xAxisIndex: 1,
        yAxisIndex: 1,
        name: "成交量",
        type: "bar",
        data: dates.map((_, index) => series.volume[index]),
        itemStyle: { color: "#c79a5f" },
      },
    ],
  };
}

function ensureQueryChart() {
  const element = document.getElementById("query-chart");
  if (!state.queryChart) {
    state.queryChart = echarts.init(element);
    window.addEventListener("resize", () => {
      if (state.queryChart) state.queryChart.resize();
      state.matchCharts.forEach((chart) => chart.resize());
    });
  }
  return state.queryChart;
}

function disposeMatchCharts() {
  state.matchCharts.forEach((chart) => {
    if (chart && !chart.isDisposed()) {
      chart.dispose();
    }
  });
  state.matchCharts = [];
}

function normalizedCandles(series) {
  if (!series?.close?.length) return [];
  const base = Number(series.close[0]) || 1;
  const scale = 100 / base;
  return series.dates.map((_, index) => [
    Number(series.open[index]) * scale,
    Number(series.close[index]) * scale,
    Number(series.low[index]) * scale,
    Number(series.high[index]) * scale,
  ]);
}

function comparisonChartOption(querySeries, matchSeries) {
  const axisData = (querySeries?.dates || []).map((_, index) => String(index + 1));
  const queryData = normalizedCandles(querySeries);
  const matchData = normalizedCandles(matchSeries);

  return {
    animationDuration: 350,
    backgroundColor: "transparent",
    legend: {
      top: 4,
      right: 8,
      textStyle: { color: "#b8b0a2", fontSize: 11 },
      data: ["目标窗口", "历史样本"],
    },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross" },
      formatter(params) {
        const lines = [`第 ${params[0]?.axisValue || "--"} 根K线`];
        params.forEach((item) => {
          const data = item.data || [];
          lines.push(
            `${item.seriesName} · 开 ${Number(data[0] || 0).toFixed(2)} 收 ${Number(data[1] || 0).toFixed(2)} 高 ${Number(data[3] || 0).toFixed(2)} 低 ${Number(data[2] || 0).toFixed(2)}`,
          );
        });
        return lines.join("<br/>");
      },
    },
    grid: { left: 12, right: 12, top: 36, bottom: 22 },
    xAxis: {
      type: "category",
      data: axisData,
      axisLabel: { color: "#8f8777", fontSize: 10 },
      axisLine: { lineStyle: { color: "rgba(255,255,255,0.08)" } },
    },
    yAxis: {
      scale: true,
      axisLabel: { color: "#8f8777", fontSize: 10 },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
    },
    series: [
      {
        name: "目标窗口",
        type: "candlestick",
        data: queryData,
        barMaxWidth: 8,
        itemStyle: {
          color: "rgba(215, 163, 93, 0.55)",
          color0: "rgba(88, 143, 118, 0.55)",
          borderColor: "#d7a35d",
          borderColor0: "#7bc0a3",
        },
      },
      {
        name: "历史样本",
        type: "candlestick",
        data: matchData,
        barMaxWidth: 8,
        itemStyle: {
          color: "rgba(239, 111, 81, 0.38)",
          color0: "rgba(126, 181, 255, 0.34)",
          borderColor: "#ef6f51",
          borderColor0: "#7eb5ff",
        },
      },
    ],
  };
}

function renderAggregate(response) {
  const container = document.getElementById("aggregate-table");
  if (!response.aggregate_forward_stats?.length) {
    container.innerHTML = '<div class="empty-state">暂无汇总结果</div>';
    return;
  }

  const rows = response.aggregate_forward_stats
    .map(
      (item) => `
        <tr>
          <td>${item.horizon}日</td>
          <td>${formatPct(item.avg_return_pct)}</td>
          <td>${formatPct(item.win_rate !== null ? item.win_rate * 100 : null)}</td>
          <td>${formatPct(item.avg_max_favorable_excursion_pct)}</td>
          <td>${formatPct(item.avg_max_drawdown_pct)}</td>
        </tr>
      `,
    )
    .join("");

  container.innerHTML = `
    <table class="stats-table">
      <thead>
        <tr>
          <th>周期</th>
          <th>平均收益</th>
          <th>胜率</th>
          <th>平均最大有利</th>
          <th>平均最大回撤</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderQueryMeta(response) {
  const badges = document.getElementById("query-badges");
  const noticeContainer = document.getElementById("response-notices");
  const frequency = String(response?.query_meta?.frequency || "daily");
  const cachedSymbols = Number(state.systemStatus?.cache_status?.[frequency]?.cached_symbols ?? 0);
  const indexSymbols = Number(response?.query_meta?.universe_size ?? 0);
  const badgeItems = [
    formatFrequency(response.query_meta.frequency),
    `窗口 ${response.query_meta.window_size}`,
    `可检索窗口 ${response.query_meta.universe_size}`,
    `候选池 ${response.query_meta.candidate_pool_size}`,
  ];
  if (cachedSymbols > 0) {
    badgeItems.push(`本地缓存 ${cachedSymbols}`);
    if (indexSymbols > 0 && indexSymbols < cachedSymbols) {
      badgeItems.push(`新股/窗口不足 ${cachedSymbols - indexSymbols}`);
    }
  }
  if (response.data_freshness?.data_source) {
    badgeItems.push(`数据源 ${response.data_freshness.data_source}`);
  }
  if (response.data_freshness?.last_refresh_at) {
    badgeItems.push(`最近刷新 ${formatDateTime(response.data_freshness.last_refresh_at)}`);
  }
  badges.innerHTML = badgeItems.map((item) => `<span class="badge-chip">${escapeHtml(item)}</span>`).join("");

  const noticeCards = [];
  const warningMessages = [response.data_freshness?.notice, ...(response.warnings || [])].filter(Boolean);
  warningMessages.forEach((message) => {
    noticeCards.push(`
      <article class="notice-card warn">
        <strong>使用提示</strong>
        <p>${escapeHtml(message)}</p>
      </article>
    `);
  });
  (response.query_meta.filters || []).forEach((item) => {
    noticeCards.push(`
      <article class="notice-card info">
        <strong>筛选口径</strong>
        <p>${escapeHtml(item)}</p>
      </article>
    `);
  });

  noticeContainer.innerHTML =
    noticeCards.join("") ||
    `
      <article class="notice-card info">
        <strong>检索口径</strong>
        <p>当前页面会展示目标窗口、两套榜单以及基于综合相似榜计算的后续表现汇总。</p>
      </article>
    `;
}

function mountMatchCharts(targetId, matches, querySeries) {
  matches.forEach((match, index) => {
    const element = document.getElementById(`${targetId}-chart-${index}`);
    if (!element) return;
    const chart = echarts.init(element);
    chart.setOption(comparisonChartOption(querySeries, match.series));
    state.matchCharts.push(chart);
  });
}

function renderMatches(targetId, matches, scoreKey, querySeries) {
  const container = document.getElementById(targetId);
  if (!matches?.length) {
    container.classList.add("empty-state");
    container.innerHTML = '<div class="empty-state">暂无结果</div>';
    return;
  }

  container.classList.remove("empty-state");
  const scoreLabel = scoreKey === "balanced" ? "综合分" : "形态分";
  const queryDates = querySeries?.dates || [];
  const targetRange = formatDateRange(queryDates[0], queryDates[queryDates.length - 1]);
  container.innerHTML = matches
    .map((match, index) => {
      const matchRange = formatDateRange(match.start_date, match.end_date);
      const forwardRows = (match.forward_stats || [])
        .map(
          (stat) => `
            <tr>
              <td>后 ${stat.horizon} 个交易日</td>
              <td>${formatPct(stat.return_pct)}</td>
              <td>${formatPct(stat.max_favorable_excursion_pct)}</td>
              <td>${formatPct(stat.max_drawdown_pct)}</td>
            </tr>
          `,
        )
        .join("");

      const explanation = (match.explanation || []).map((item) => escapeHtml(item)).join(" · ");

      return `
        <article class="match-card">
          <div class="match-head">
            <div class="match-title-block">
              <p class="match-rank">#${index + 1}</p>
              <h3>${escapeHtml(match.symbol)}${match.name ? ` · ${escapeHtml(match.name)}` : ""}</h3>
              <p class="match-meta">
                历史样本窗口：${escapeHtml(matchRange)}
                ${match.industry ? ` · ${escapeHtml(match.industry)}` : ""}
              </p>
            </div>
            <div class="score-stack">
              <div class="score-pill primary">
                <span>${scoreLabel}</span>
                <strong>${formatScore(match.scores[scoreKey])}</strong>
              </div>
              <div class="score-pill secondary">
                <span>形态分</span>
                <strong>${formatScore(match.scores.shape)}</strong>
              </div>
            </div>
          </div>

          <div class="segment-grid">
            <div class="segment-card target">
              <span>目标窗口</span>
              <strong>${escapeHtml(targetRange)}</strong>
              <small>你正在查询的 ${escapeHtml(queryDates.length || "-")} 根K线</small>
            </div>
            <div class="segment-card match">
              <span>历史样本窗口</span>
              <strong>${escapeHtml(matchRange)}</strong>
              <small>${escapeHtml(match.symbol)}${match.name ? ` · ${escapeHtml(match.name)}` : ""}</small>
            </div>
          </div>

          <div class="comparison-shell">
            <div class="comparison-caption">
              <span class="legend-chip target">目标窗口：${escapeHtml(targetRange)}</span>
              <span class="legend-chip match">历史样本：${escapeHtml(matchRange)}</span>
              <span class="comparison-note">已按首根收盘价归一化对齐</span>
            </div>
            <div id="${targetId}-chart-${index}" class="comparison-chart"></div>
          </div>

          <div class="score-grid">
            <span>价格路径距离 ${formatDistance(match.scores.price_path_distance)}</span>
            <span>蜡烛几何距离 ${formatDistance(match.scores.candle_geometry_distance)}</span>
            <span>量能距离 ${formatDistance(match.scores.volume_liquidity_distance)}</span>
            <span>环境距离 ${formatDistance(match.scores.environment_distance)}</span>
          </div>

          <div class="forward-table-shell">
            <div class="forward-table-caption">该历史样本之后的实际表现，不是当前股票未来收益预测。</div>
            <table class="forward-table">
              <thead>
                <tr>
                  <th>周期</th>
                  <th>收益</th>
                  <th>最大有利</th>
                  <th>最大回撤</th>
                </tr>
              </thead>
              <tbody>${forwardRows}</tbody>
            </table>
          </div>

          <p class="explanation">${explanation || "当前样本没有额外说明。"}</p>
        </article>
      `;
    })
    .join("");

  mountMatchCharts(targetId, matches, querySeries);
}

function disableExports() {
  const csvLink = document.getElementById("export-csv");
  const htmlLink = document.getElementById("export-html");
  csvLink.href = "#";
  htmlLink.href = "#";
  csvLink.classList.add("disabled");
  htmlLink.classList.add("disabled");
  csvLink.classList.remove("warning");
  htmlLink.classList.remove("warning");
}

function updateExports(formData, response) {
  const params = new URLSearchParams(formData);
  const csvLink = document.getElementById("export-csv");
  const htmlLink = document.getElementById("export-html");
  csvLink.href = `/api/export/csv?${params.toString()}`;
  htmlLink.href = `/api/export/html?${params.toString()}`;
  csvLink.classList.remove("disabled");
  htmlLink.classList.remove("disabled");
  if (isPartialIndexResponse(response)) {
    csvLink.classList.add("warning");
    htmlLink.classList.add("warning");
  } else {
    csvLink.classList.remove("warning");
    htmlLink.classList.remove("warning");
  }
}

function markResponseDirty(formData) {
  if (!state.response) return;
  const signature = formSignature(formData);
  if (state.responseSignature === signature) return;
  state.responseDirty = true;
  disableExports();
  updatePredictionActionState(formData);
  setStatus("表单已变更，请重新点击“开始检索”刷新结果；旧结果当前只保留作参考。", "warn");
}

function currentResponseMatches(formData) {
  return Boolean(state.response && !state.responseDirty && state.responseSignature === formSignature(formData));
}

function updatePredictionActionState(formData = null) {
  const button = document.getElementById("predict-button");
  if (!button) return;
  if (!formData) {
    const form = document.getElementById("search-form");
    formData = form ? serializeForm(form) : {};
  }
  const isDaily = String(formData.frequency || "daily") === "daily";
  const canPredict = isDaily && currentResponseMatches(formData);
  button.disabled = !canPredict;
  button.classList.toggle("disabled", !canPredict);
  button.title = canPredict
    ? "基于当前相似样本生成研究预测"
    : "请先生成当前查询的日线相似样本";
}

function clearResponseState() {
  state.response = null;
  state.responseSignature = null;
  state.responseDirty = false;
  disposeMatchCharts();
  updateLeaderboardTitles();
  document.getElementById("query-summary").textContent = "等待系统判断当前查询是否就绪";
  document.getElementById("query-badges").innerHTML = "";
  document.getElementById("response-notices").innerHTML = "";
  document.getElementById("aggregate-table").innerHTML =
    '<section class="setup-placeholder"><strong>后续表现汇总</strong><p>准备完成后，这里会显示综合相似榜的后续统计。</p></section>';
  document.getElementById("balanced-list").classList.add("empty-state");
  document.getElementById("balanced-list").innerHTML =
    '<section class="setup-placeholder"><strong>综合相似榜</strong><p>系统就绪后会在这里展示历史相似窗口。</p></section>';
  document.getElementById("shape-list").classList.add("empty-state");
  document.getElementById("shape-list").innerHTML =
    '<section class="setup-placeholder"><strong>形态最像榜</strong><p>系统就绪后会在这里展示形态最接近的历史样本。</p></section>';
  if (state.queryChart) {
    state.queryChart.dispose();
    state.queryChart = null;
  }
  document.getElementById("query-chart").innerHTML =
    '<section class="setup-placeholder"><strong>目标K线</strong><p>准备完成后，这里会展示当前查询窗口的 K 线和成交量图。</p></section>';
  disableExports();
  updatePredictionActionState();
}

function predictionSignature(formData) {
  return JSON.stringify({
    symbol: normalizeSymbol(formData.symbol || ""),
    end_date: formData.end_date || "",
    frequency: formData.frequency || "daily",
  });
}

function resetPredictionResult(message = "表单已变化，请先刷新当前查询的相似样本。") {
  const container = document.getElementById("prediction-result");
  state.predictionSignature = null;
  if (!container) return;
  container.classList.add("empty-state");
  container.innerHTML = `
    <section class="setup-placeholder">
      <strong>预测待更新</strong>
      <p>${escapeHtml(message)}</p>
    </section>
  `;
}

function markPredictionDirty(formData) {
  if (!state.predictionSignature) return;
  if (state.predictionSignature === predictionSignature(formData)) return;
  resetPredictionResult("当前输入已经变化，旧预测已隐藏，避免把不同股票或日期的预测误读成当前结果。");
}

async function prepareCurrentSymbol(form) {
  const formData = serializeForm(form);
  const symbol = normalizeSymbol(formData.symbol);
  if (!symbol || !formData.end_date) {
    setStatus("请先补全股票代码和截止日期", "warn");
    return;
  }

  setPrepareResult("", "idle");
  setStatus(`正在补齐 ${symbol} 的本地缓存...`, "loading");
  const response = await fetch("/api/prepare-symbol", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      symbol,
      end_date: formData.end_date,
      frequency: formData.frequency,
      window_size: Number(formData.window_size),
      top_k: Number(formData.top_k),
      search_scope: formData.search_scope || "historical",
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "补齐当前股票失败" }));
    throw new Error(error.detail || "补齐当前股票失败");
  }

  const payload = await response.json();
  const warningText = (payload.warnings || []).map((item) => escapeHtml(item)).join(" ");
  const message = `<strong>${escapeHtml(payload.message || "当前标的已处理")}</strong>${warningText ? `<br/>${warningText}` : ""}`;
  setPrepareResult(message, payload.search_ready ? "success" : "warn");

  await loadSystemStatus();
  await loadCachedSymbolHints(form, { query: symbol, force: true });

  if (payload.search_ready) {
    setStatus(payload.message || "当前标的已补齐，可以开始检索。", warningText ? "warn" : "success");
    await runSearch(form);
  } else {
    setStatus(payload.message || "当前标的还没有准备完成。", "warn");
  }
}

async function randomizeSymbol(form) {
  let payload = state.symbolHints;
  const frequency = String(form.elements.namedItem("frequency")?.value || "daily");
  if (!payload || String(payload.frequency || "") !== frequency || !Array.isArray(payload.items) || !payload.items.length) {
    payload = await loadCachedSymbolHints(form, { query: "", limit: 20, force: true });
  }
  const items = Array.isArray(payload?.items) ? payload.items : [];
  if (!items.length) {
    setStatus(`当前${formatFrequency(frequency)}还没有可用缓存。`, "warn");
    return;
  }
  const pick = items[Math.floor(Math.random() * items.length)];
  form.elements.namedItem("symbol").value = pick.symbol;
  const formData = serializeForm(form);
  markPredictionDirty(formData);
  updatePredictionActionState(formData);
  setPrepareResult("", "idle");
  await loadCachedSymbolHints(form, { query: pick.symbol, force: true });
  const readiness = readinessForForm(state.systemStatus, serializeForm(form));
  updatePredictionActionState(serializeForm(form));
  setStatus(readiness.message, readiness.warning ? "warn" : readiness.ready ? "idle" : "warn");
}

function renderSystemStatus(status) {
  const cards = document.getElementById("system-status-cards");
  const details = document.getElementById("system-status-details");
  const updated = document.getElementById("system-status-updated");
  const dailyCache = status.cache_status?.daily;
  const latestBackfill = status.latest_backfill;
  const acceleration = status.acceleration || {};
  const buildEntries = Object.values(status.index_status || {});
  const coverageRatio =
    status.filtered_universe_count > 0 ? ((Number(dailyCache?.cached_symbols || 0) / Number(status.filtered_universe_count)) * 100).toFixed(2) : "--";
  const latestBuild = buildEntries.length
    ? buildEntries.sort((left, right) => String(right.built_at || "").localeCompare(String(left.built_at || "")))[0]
    : null;
  const frequencyOrder = ["daily", "1", "5", "15", "30", "60"];
  const frequencyRows = frequencyOrder.map((frequency) => {
    const cache = status.cache_status?.[frequency];
    const builtWindows = builtWindowsForFrequency(status, frequency);
    const staleWindows = staleWindowsForFrequency(status, frequency);
    return `
      <li>
        <strong>${formatFrequency(frequency)}</strong>
        <span>缓存 ${cache?.cached_symbols ?? 0}</span>
        <span>索引 ${builtWindows.length ? builtWindows.join(" / ") : "未建"}</span>
        <span>${staleWindows.length ? `待重建 ${staleWindows.join(" / ")}` : "索引最新"}</span>
      </li>
    `;
  });
  const missingDailyWindows = missingWindowsForFrequency(status, "daily");
  const staleDailyWindows = staleWindowsForFrequency(status, "daily");
  const dailyIndexCoverage = currentIndexSymbolCountForFrequency(status, "daily");
  const sampleFailures = (latestBackfill?.sample_failures || []).slice(0, 3);
  const runtimeBackend = acceleration.active_backend;
  const artifactBackend = acceleration.artifact_backend;
  const runtimeDevice = acceleration.active_device_name || acceleration.active_device || "--";
  const backendMismatch = runtimeBackend && artifactBackend && runtimeBackend !== artifactBackend;
  const runtimeSource =
    acceleration.active_backend_source === "runtime-index" ? "运行时探测" : "状态快照";

  updated.textContent = dailyCache?.data_freshness?.last_refresh_at
    ? `日线最近刷新于 ${formatDateTime(dailyCache.data_freshness.last_refresh_at)}`
    : "尚未检测到日线刷新记录";

  if (staleDailyWindows.length && dailyIndexCoverage > 0 && Number(dailyCache?.cached_symbols ?? 0) > 0) {
    updated.textContent += ` 路 褰撳墠绱㈠紩瑕嗙洊 ${dailyIndexCoverage}/${dailyCache.cached_symbols}`;
  }

  cards.innerHTML = `
    <article class="status-card">
      <span class="status-label">股票池</span>
      <strong>${status.filtered_universe_count} / ${status.universe_count}</strong>
      <p>已过滤 ST 后的可选标的数量</p>
    </article>
    <article class="status-card">
      <span class="status-label">免费覆盖</span>
      <strong>${dailyCache?.cached_symbols ?? 0} / ${status.filtered_universe_count || 0}</strong>
      <p>${dailyCache?.cached_symbols ? `当前日线缓存覆盖率 ${coverageRatio}%` : "尚未生成日线缓存"}</p>
    </article>
    <article class="status-card">
      <span class="status-label">最近回填</span>
      <strong>${latestBackfill ? `${latestBackfill.completed_symbols}/${latestBackfill.requested_symbols}` : "--"}</strong>
      <p>${latestBackfill ? `${formatBackfillStatus(latestBackfill.status)} · 剩余 ${latestBackfill.remaining_symbols} · 最后处理 ${latestBackfill.last_symbol || "--"}` : "尚未运行回填任务"}</p>
    </article>
    <article class="status-card">
      <span class="status-label">索引就绪</span>
      <strong>${builtWindowsForFrequency(status, "daily").length ? builtWindowsForFrequency(status, "daily").join(" / ") : "--"}</strong>
      <p>${
        staleDailyWindows.length
          ? `待重建 ${staleDailyWindows.join(" / ")}`
          : latestBuild
            ? `${formatIndexBackend(latestBuild.backend)} · 最近构建 ${formatFrequency(latestBuild.frequency)} / ${latestBuild.window_size}`
            : "尚未生成索引"
       }</p>
     </article>
     <article class="status-card">
       <span class="status-label">运行时加速</span>
       <strong>${formatIndexBackend(runtimeBackend)}</strong>
       <p>${
         runtimeBackend
           ? `${acceleration.gpu_enabled ? "GPU 已启用" : "当前使用 CPU"} · ${escapeHtml(runtimeDevice)}`
           : "尚未探测到运行时后端"
       }</p>
     </article>
   `;

  details.innerHTML = `
    <article class="status-detail">
      <h3>频段缓存与索引</h3>
      <ul class="status-detail-list">${frequencyRows.join("")}</ul>
    </article>
    <article class="status-detail">
      <h3>默认日线窗口</h3>
      <p>${
        missingDailyWindows.length
          ? `缺少 ${missingDailyWindows.join(" / ")}`
          : staleDailyWindows.length
            ? `待重建 ${staleDailyWindows.join(" / ")}`
            : "5 / 8 / 10 / 20 已全部就绪"
      }</p>
      <p>${dailyCache?.data_freshness?.notice ? escapeHtml(dailyCache.data_freshness.notice) : "默认首页只会在当前窗口可检索时自动执行查询。"}</p>
    </article>
     <article class="status-detail">
       <h3>最近失败样本</h3>
       ${
         sampleFailures.length
           ? `<ul class="status-detail-list">${sampleFailures
               .map((item) => `<li><strong>${escapeHtml(item.symbol)}</strong><span>${escapeHtml(item.error || "未知错误")}</span></li>`)
               .join("")}</ul>`
           : "<p>最近一次回填没有记录失败样本。</p>"
       }
     </article>
     <article class="status-detail">
       <h3>运行时后端</h3>
       <ul class="status-detail-list">
         <li><strong>实际检索</strong><span>${formatIndexBackend(runtimeBackend)}</span></li>
         <li><strong>索引工件</strong><span>${formatIndexBackend(artifactBackend)}</span></li>
         <li><strong>运行设备</strong><span>${escapeHtml(runtimeDevice)}</span></li>
         <li><strong>状态来源</strong><span>${escapeHtml(runtimeSource)}</span></li>
         <li><strong>GPU 加速</strong><span>${acceleration.gpu_enabled ? "已启用" : "未启用"}</span></li>
       </ul>
       <p>${
         acceleration.runtime_probe_error
           ? `运行时探测失败：${escapeHtml(acceleration.runtime_probe_error)}`
           : backendMismatch
             ? `当前运行时使用 ${escapeHtml(formatIndexBackend(runtimeBackend))}，磁盘工件记录为 ${escapeHtml(formatIndexBackend(artifactBackend))}。这通常意味着系统在加载后启用了更快的运行时后端。`
             : "运行时后端与当前索引工件状态一致。"
       }</p>
     </article>
   `;
}

async function loadSystemStatus() {
  const response = await fetch("/api/status");
  if (!response.ok) {
    throw new Error("无法读取系统状态");
  }
  const payload = await response.json();
  state.systemStatus = payload;
  renderSystemStatus(payload);
  return payload;
}

function renderResponse(response, formData) {
  state.response = response;
  state.responseSignature = formSignature(formData);
  state.responseDirty = false;
  disposeMatchCharts();
  updateLeaderboardTitles(Number(formData.top_k) || null);

  const chart = ensureQueryChart();
  chart.setOption(chartOption(response.query_meta.query_series, `${response.query_meta.symbol} 查询窗口`), true);

  document.getElementById("query-summary").textContent =
    `${response.query_meta.symbol} · ${response.query_meta.start_date} 至 ${response.query_meta.end_date}`;

  renderQueryMeta(response);
  renderAggregate(response);
  renderMatches("balanced-list", response.balanced_matches, "balanced", response.query_meta.query_series);
  renderMatches("shape-list", response.shape_matches, "shape", response.query_meta.query_series);

  const notices = [response.data_freshness.notice, ...(response.warnings || [])].filter(Boolean);
  setStatus(notices.length ? notices.join(" | ") : "查询完成", notices.length ? "warn" : "success");
  updateExports(formData, response);
  updatePredictionActionState(formData);
  persistQueryToUrl(formData);
}

function renderPrediction(response) {
  const container = document.getElementById("prediction-result");
  if (!container) return;
  container.classList.remove("empty-state");
  const factor = response.factor_snapshot || {};
  const diagnostics = response.model_diagnostics || {};
  const backtest = response.backtest_summary || {};
  const backtestAcceptance = String(backtest.acceptance || "not_evaluated");
  const acceleration = diagnostics.acceleration || {};
  const accelerationMode = acceleration.recall_gpu_enabled ? "GPU 召回" : "CPU 召回";
  const accelerationDevice = acceleration.recall_device_name || acceleration.recall_device || "unknown";
  const gateWarnings = [
    ...(response.warnings || []),
    ...(diagnostics.warnings || []),
    ...(backtest.notes || []),
  ].filter(Boolean);
  const strongGate =
    !diagnostics.passed_validation ||
    backtestAcceptance !== "passed" ||
    String(acceleration.market_scope || "") === "main_board_only";
  const predictionCards = (response.predictions || [])
    .map((prediction) => {
      const quantiles = prediction.return_quantiles_pct || {};
      const sampleCount = Number(prediction.sample_count || 0);
      const confidence = String(prediction.confidence || "");
      const weakSignal =
        !diagnostics.passed_validation ||
        backtestAcceptance !== "passed" ||
        confidence.toLowerCase() === "low" ||
        sampleCount < 20;
      const scenarios = Object.entries(prediction.kline_scenarios || {})
        .map(([name, value]) => `<span>${escapeHtml(name)} ${formatProbability(value)}</span>`)
        .join("");
      const reasons = (prediction.confidence_reasons || [])
        .map((item) => `<li>${escapeHtml(item)}</li>`)
        .join("");
      return `
        <article class="prediction-card${weakSignal ? " weak-signal" : ""}">
          ${
            weakSignal
              ? `<div class="prediction-disclaimer warn"><strong>证据较弱</strong><p>样本、置信度或回测验收不足，数值只适合作研究线索。</p></div>`
              : ""
          }
          <div class="prediction-card-head">
            <div>
              <span>下 ${prediction.horizon} 个交易日</span>
              <small>历史相似样本 / 模型估计上涨占比</small>
            </div>
            <strong>${formatProbability(prediction.up_probability)}</strong>
          </div>
          <div class="prediction-grid">
            <div><span>研究样本期望收益</span><strong>${formatPct(prediction.expected_return_pct)}</strong></div>
            <div><span>收益区间 P10/P50/P90</span><strong>${formatPct(quantiles.p10)} / ${formatPct(quantiles.p50)} / ${formatPct(quantiles.p90)}</strong></div>
            <div><span>平均回撤风险</span><strong>${formatPct(prediction.max_drawdown_risk_pct)}</strong></div>
            <div><span>置信度</span><strong>${escapeHtml(prediction.confidence)}</strong></div>
          </div>
          <div class="scenario-row">${scenarios || "<span>暂无场景统计</span>"}</div>
          <p class="prediction-note">样本 ${sampleCount} 条 · 模型 ${escapeHtml(prediction.selected_model)} · 相似样本占比 ${formatProbability(prediction.analogue_up_probability)} · ML估计 ${formatProbability(prediction.ml_up_probability)}</p>
          ${reasons ? `<ul class="prediction-reasons">${reasons}</ul>` : ""}
        </article>
      `;
    })
    .join("");

  const evidenceRows = (response.analogue_evidence || [])
    .slice(0, 8)
    .map(
      (sample) => `
        <tr>
          <td>${escapeHtml(sample.symbol)}${sample.name ? ` · ${escapeHtml(sample.name)}` : ""}</td>
          <td>${escapeHtml(formatDateRange(sample.start_date, sample.end_date))}</td>
          <td>${formatScore(sample.similarity)}</td>
          <td>${formatPct(sample.forward_returns_pct?.["1"])}</td>
          <td>${formatPct(sample.forward_returns_pct?.["2"])}</td>
        </tr>
      `,
    )
    .join("");
  const warnings = Array.from(new Set(gateWarnings))
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  container.innerHTML = `
    ${
      strongGate
        ? `<div class="prediction-disclaimer warn">
            <strong>主板短线研究模式：未通过验收前不作为交易参考</strong>
            <p>当前只使用主板日线样本；50,000 个短线样本是期望规模，硬验收线为方向准确率 ≥ 75% 且 Brier 优于基线，未达标会持续显示实验态。</p>
          </div>`
        : ""
    }
    <div class="prediction-disclaimer">
      <strong>研究信号，不是买卖建议</strong>
      <p>预测只基于免费日线、相似历史样本和轻量模型对照；下方历史收益是样本之后的实际表现，不是当前股票的确定性收益。</p>
    </div>
    <div class="prediction-summary">
      <article>
        <span>目标</span>
        <strong>${escapeHtml(response.query_meta?.symbol || "--")}${response.query_meta?.name ? ` · ${escapeHtml(response.query_meta.name)}` : ""}</strong>
        <p>${escapeHtml(formatFullDate(response.query_meta?.as_of_date))} · 窗口 ${escapeHtml((response.query_meta?.window_sizes || []).join(" / "))} · 遇休市按交易日顺延</p>
      </article>
      <article>
        <span>因子快照</span>
        <strong>短线热度 ${formatPlainNumber(factor.short_hot_score)} / 点火 ${formatPlainNumber(factor.large_order_fire_score)}</strong>
        <p>成交额Z ${formatPlainNumber(factor.amount_zscore)} · 换手Z ${formatPlainNumber(factor.turnover_zscore)} · 振幅 ${formatPct(factor.range_pct)}</p>
      </article>
      <article>
        <span>主板涨停结构</span>
        <strong>${escapeHtml(formatBoardStage(factor.board_chain_stage))}</strong>
        <p>${factor.limit_up_like ? "近似涨停" : "未近似涨停"} · 10cm阈值 ${formatPct(factor.limit_threshold_pct)} · 连板 ${factor.consecutive_limit_up_days ?? 0}</p>
      </article>
      <article>
        <span>量价/波动</span>
        <strong>ATR ${formatPct(factor.atr_14_pct)} / MFI ${formatPlainNumber(factor.mfi_14)}</strong>
        <p>OBV趋势 ${formatPlainNumber(factor.obv_trend_5)} · 行业相对强弱 ${formatPct(factor.industry_relative_strength_5)}</p>
      </article>
      <article>
        <span>模型状态</span>
        <strong>${escapeHtml(diagnostics.passed_validation ? "ML对照通过" : "实验态")}</strong>
        <p>${escapeHtml(diagnostics.selected_model || "--")} · ${escapeHtml(backtest.acceptance || "not_evaluated")} · 主板样本</p>
      </article>
      <article>
        <span>运行加速</span>
        <strong>${escapeHtml(accelerationMode)}</strong>
        <p>${escapeHtml(acceleration.recall_backend || "--")} · ${escapeHtml(accelerationDevice)}</p>
      </article>
    </div>
    <div class="prediction-card-grid">${predictionCards || '<div class="empty-state">暂无预测结果</div>'}</div>
    <div class="prediction-evidence">
      <h3>相似历史证据（样本后续实际表现）</h3>
      <table class="forward-table">
        <thead>
          <tr>
            <th>样本</th>
            <th>历史窗口</th>
            <th>相似度</th>
            <th>下1个交易日实际收益</th>
            <th>下2个交易日实际收益</th>
          </tr>
        </thead>
        <tbody>${evidenceRows || "<tr><td colspan='5'>暂无可用证据</td></tr>"}</tbody>
      </table>
    </div>
    ${warnings ? `<div class="prediction-disclaimer warn"><strong>风险提示</strong><ul>${warnings}</ul></div>` : ""}
  `;
}

async function runPrediction(form) {
  const formData = serializeForm(form);
  if (!formData.symbol || !formData.end_date) {
    setStatus("请先补全股票代码/名称和截止日期", "warn");
    return;
  }
  if (String(formData.frequency || "daily") !== "daily") {
    setStatus("一期概率预测只支持日线。", "warn");
    return;
  }
  try {
    await loadCachedSymbolHints(form, { query: formData.symbol });
  } catch (error) {
    setStatus(error.message || "无法读取可用标的列表，本次不生成预测。", "warn");
    return;
  }
  const readiness = readinessForForm(state.systemStatus, formData);
  if (!readiness.ready) {
    resetPredictionResult(readiness.message);
    updatePredictionActionState(formData);
    setStatus(readiness.message, "warn");
    return;
  }
  if (!currentResponseMatches(formData)) {
    resetPredictionResult("请先点击“开始检索”生成当前查询的相似样本，再基于这组样本生成研究预测。");
    updatePredictionActionState(formData);
    setStatus("请先生成当前查询的相似样本，避免把旧榜单和新预测混用。", "warn");
    return;
  }
  const container = document.getElementById("prediction-result");
  if (container) {
    container.classList.add("empty-state");
    container.innerHTML = '<section class="setup-placeholder"><strong>正在生成预测</strong><p>系统正在检索历史相似样本、计算因子和轻量模型对照...</p></section>';
  }
  setStatus("正在生成下 1/2 个交易日研究预测...", "loading");
  const response = await fetch("/api/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      symbol: String(formData.symbol || "").trim(),
      as_of_date: formData.end_date,
      frequency: "daily",
      horizons: [1, 2],
      window_sizes: [5, 8, 10, 20],
      top_k: 100,
    }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "预测失败" }));
    throw new Error(error.detail || "预测失败");
  }
  const payload = await response.json();
  renderPrediction(payload);
  state.predictionSignature = predictionSignature(formData);
  setStatus("概率预测已生成：请按研究信号理解，不作为买卖建议。", "success");
}

async function submitSearch(formData) {
  setStatus("正在构建目标窗口并检索历史案例...", "loading");
  const payload = {
    symbol: String(formData.symbol || "").trim(),
    end_date: formData.end_date,
    frequency: formData.frequency,
    window_size: Number(formData.window_size),
    top_k: Number(formData.top_k),
    search_scope: formData.search_scope || "historical",
  };

  const response = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "查询失败" }));
    throw new Error(error.detail || "查询失败");
  }
  return response.json();
}

async function runSearch(form) {
  const formData = serializeForm(form);
  if (!formData.symbol || !formData.end_date) {
    setStatus("请先补全股票代码和截止日期", "warn");
    return;
  }
  try {
    await loadCachedSymbolHints(form, { query: formData.symbol });
  } catch (error) {
    setStatus(error.message || "无法读取可用标的列表，本次将直接尝试检索。", "warn");
  }
  const readiness = readinessForForm(state.systemStatus, formData);
  if (!readiness.ready) {
    clearResponseState();
    renderSetupState(formData, readiness);
    setStatus(readiness.message, "warn");
    return;
  }
  try {
    const response = await submitSearch(formData);
    renderResponse(response, formData);
    loadSystemStatus().catch(() => {});
  } catch (error) {
    clearResponseState();
    setStatus(error.message || "查询失败", "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("search-form");
  const symbolField = form.elements.namedItem("symbol");
  const frequencyField = form.elements.namedItem("frequency");
  const randomButton = document.getElementById("random-symbol-button");
  const prepareButton = document.getElementById("prepare-symbol-button");
  const predictButton = document.getElementById("predict-button");
  applyUrlParamsToForm(form);
  disableExports();
  updateLeaderboardTitles();
  updatePredictionActionState(serializeForm(form));
  setPrepareResult("", "idle");

  const refreshReadinessHint = async ({ forceHints = false, query = null } = {}) => {
    const hasResponse = Boolean(state.response);
    const currentFormData = serializeForm(form);
    try {
      await loadCachedSymbolHints(form, { query, force: forceHints });
    } catch (error) {
      setStatus(error.message || "无法读取可用标的列表", "error");
      return;
    }
    if (hasResponse) {
      markResponseDirty(currentFormData);
      updatePredictionActionState(currentFormData);
      return;
    }
    const readiness = readinessForForm(state.systemStatus, currentFormData);
    updatePredictionActionState(currentFormData);
    setStatus(readiness.message, readiness.warning ? "warn" : readiness.ready ? "idle" : "warn");
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await runSearch(form);
  });

  form.addEventListener("change", () => {
    setPrepareResult("", "idle");
    const formData = serializeForm(form);
    markPredictionDirty(formData);
    updatePredictionActionState(formData);
    refreshReadinessHint({ forceHints: true }).catch(() => {});
  });
  symbolField.addEventListener("input", () => {
    setPrepareResult("", "idle");
    const formData = serializeForm(form);
    markPredictionDirty(formData);
    updatePredictionActionState(formData);
    refreshReadinessHint({ forceHints: true, query: symbolField.value }).catch(() => {});
  });
  frequencyField.addEventListener("change", () => {
    setPrepareResult("", "idle");
    const formData = serializeForm(form);
    markPredictionDirty(formData);
    updatePredictionActionState(formData);
    refreshReadinessHint({ forceHints: true, query: symbolField.value }).catch(() => {});
  });
  randomButton.addEventListener("click", () => {
    randomizeSymbol(form).catch((error) => {
      setStatus(error.message || "无法选择可用标的", "error");
    });
  });
  prepareButton.addEventListener("click", () => {
    prepareCurrentSymbol(form).catch((error) => {
      setPrepareResult(`<strong>补齐失败</strong><br/>${escapeHtml(error.message || "当前标的补齐失败")}`, "error");
      setStatus(error.message || "当前标的补齐失败", "error");
    });
  });
  predictButton?.addEventListener("click", () => {
    runPrediction(form).catch((error) => {
      const container = document.getElementById("prediction-result");
      if (container) {
        container.classList.add("empty-state");
        container.innerHTML = `
          <section class="setup-placeholder">
            <strong>预测失败</strong>
            <p>${escapeHtml(error.message || "概率预测失败")}</p>
          </section>
        `;
      }
      setStatus(error.message || "概率预测失败", "error");
    });
  });

  loadSystemStatus()
    .then(() => {
      return loadCachedSymbolHints(form, { query: form.elements.namedItem("symbol")?.value || "", force: true });
    })
    .then(() => {
      return refreshReadinessHint({ query: form.elements.namedItem("symbol")?.value || "" });
    })
    .then(() => {
      const readiness = readinessForForm(state.systemStatus, serializeForm(form));
      if (!readiness.ready || readiness.warning) return;
      runSearch(form).catch(() => {});
    })
    .catch((error) => {
      state.systemStatus = null;
      document.getElementById("system-status-updated").textContent = error.message || "无法读取系统状态";
      setStatus("系统状态暂时不可用，将直接尝试当前查询。", "warn");
      const formData = serializeForm(form);
      if (formData.symbol && formData.end_date) {
        runSearch(form).catch(() => {});
      }
    });
});
