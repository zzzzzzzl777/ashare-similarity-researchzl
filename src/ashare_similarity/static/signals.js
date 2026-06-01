// signals.js v1.0.0 — Historical Backtest Signal Dashboard
(function () {
  "use strict";

  var API = "/api/signals/v1";
  var backtestChart = null;

  function $(sel) { return document.querySelector(sel); }

  function fetchJSON(url) {
    return fetch(url).then(function (r) {
      if (r.status === 503) throw new Error("信号缓存未构建，请先运行 build-signals");
      if (!r.ok) throw new Error("请求失败: " + r.status);
      return r.json();
    });
  }

  function pct(v, d) {
    if (v == null) return "-";
    return (v * 100).toFixed(d || 2) + "%";
  }

  function layerBadge(layer) {
    var cls = "layer-badge layer-" + layer;
    var label = layer === "dev_valid" ? "验证集" : "研究集";
    return '<span class="' + cls + '">' + label + "</span>";
  }

  function confBadge(c) {
    return c ? '<span class="badge-conf">高置信</span>' : '<span class="badge-noconf">普通</span>';
  }

  // ── Init ──
  function init() {
    setupTabs();
    loadStatus();
  }

  function setupTabs() {
    var buttons = document.querySelectorAll(".tab-bar button");
    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        buttons.forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        document.querySelectorAll(".tab-panel").forEach(function (p) { p.classList.remove("active"); });
        var panel = $("#tab-" + btn.dataset.tab);
        if (panel) panel.classList.add("active");
        if (btn.dataset.tab === "backtest" && !backtestChart) loadBacktest();
      });
    });
  }

  function loadStatus() {
    fetchJSON(API + "/status").then(function (data) {
      var meta = $("#header-meta");
      if (data.status === "not_built") {
        meta.textContent = "信号缓存尚未构建。请运行 build-signals 命令。";
        $("#summary-cards").innerHTML = '<div class="error-msg">缓存未构建。运行 <code>python -m ashare_similarity.cli build-signals</code> 后刷新。</div>';
        return;
      }
      if (data.status === "manifest_mismatch") {
        meta.textContent = "缓存与冻结候选不匹配，请重新构建。";
        return;
      }
      var range = data.date_range || [];
      var built = data.cache_generated_at || "";
      var builtStr = "?";
      if (built) {
        var bd = new Date(built);
        if (!isNaN(bd.getTime())) {
          builtStr = bd.getUTCFullYear() + "-" + String(bd.getUTCMonth() + 1).padStart(2, "0") + "-" + String(bd.getUTCDate()).padStart(2, "0") + " " + String(bd.getUTCHours()).padStart(2, "0") + ":" + String(bd.getUTCMinutes()).padStart(2, "0") + " UTC";
        }
      }
      meta.textContent = "数据范围: " + (range[0] || "?") + " ~ " + (range[1] || "?") + " | 构建时间: " + builtStr;
      if (data.sample_symbols && data.sample_symbols.length > 0) {
        var inp = $("#stock-query");
        if (inp) inp.placeholder = "例如 " + data.sample_symbols.slice(0, 3).join(", ");
      }
      loadSummaryCards();
      loadDates();
    }).catch(function (e) {
      $("#header-meta").textContent = "加载失败: " + e.message;
    });
  }

  function loadSummaryCards() {
    fetchJSON(API + "/backtest").then(function (data) {
      var html = "";
      data.by_model.forEach(function (m) {
        html += '<div class="summary-card"><h3 style="color:#111827;">' + m.model_tag + " — " + m.best_model + "</h3>";
        html += '<div style="font-size:0.78rem;color:#4b5563;margin-bottom:0.4rem;">selector: ' + m.selector_method + "</div>";
        m.by_layer.forEach(function (l) {
          html += "<div><strong>" + layerBadge(l.layer) + "</strong>";
          html += '<div class="stat-row">';
          html += '<div><span class="stat">' + pct(l.confident_accuracy) + '</span><br/><span class="stat-label">高置信准确率</span></div>';
          html += '<div><span class="stat">' + pct(l.confident_coverage) + '</span><br/><span class="stat-label">覆盖率</span></div>';
          html += '<div><span class="stat">' + l.confident_count + '</span><br/><span class="stat-label">高置信数</span></div>';
          html += '<div><span class="stat">' + pct(l.wilson_lower_95) + '</span><br/><span class="stat-label">Wilson 95% 下界</span></div>';
          html += "</div></div>";
        });
        if (m.artifact_reference) {
          var ref = m.artifact_reference;
          html += '<div style="margin-top:0.5rem;font-size:0.75rem;color:#6b7280;">原始 artifact: acc=' + pct(ref.hc_accuracy) + " cov=" + pct(ref.hc_coverage) + " count=" + (ref.hc_count || "?") + "</div>";
        }
        html += "</div>";
      });
      $("#summary-cards").innerHTML = html;
    }).catch(function () {
      $("#summary-cards").innerHTML = '<div class="loading">回测数据加载中...</div>';
    });
  }

  // ── Dates ──
  function loadDates() {
    fetchJSON(API + "/dates").then(function (data) {
      var sel = $("#date-select");
      sel.innerHTML = "";
      data.dates.forEach(function (d) {
        var opt = document.createElement("option");
        opt.value = d; opt.textContent = d;
        sel.appendChild(opt);
      });
      if (data.dates.length > 0) {
        sel.value = data.dates[data.dates.length - 1];
        loadDaily();
      }
      sel.addEventListener("change", loadDaily);
      $("#model-select").addEventListener("change", loadDaily);
    });
  }

  function loadDaily() {
    var date = $("#date-select").value;
    var model = $("#model-select").value;
    if (!date) return;
    var url = API + "/daily?date=" + date;
    if (model) url += "&model_tag=" + model;
    var wrap = $("#daily-table-wrap");
    wrap.innerHTML = '<div class="loading">加载中...</div>';
    fetchJSON(url).then(function (data) {
      if (!data.signals || data.signals.length === 0) {
        wrap.innerHTML = '<div class="loading">该日期无信号数据</div>';
        return;
      }
      var html = '<table class="signal-table"><thead><tr>';
      html += "<th>代码</th><th>模型</th><th>概率</th><th>置信</th><th>实际</th><th>正确</th><th>层</th>";
      html += "</tr></thead><tbody>";
      data.signals.forEach(function (s) {
        html += "<tr>";
        html += "<td>" + s.symbol + "</td>";
        html += "<td>" + s.model_tag + "</td>";
        html += "<td>" + (s.probability * 100).toFixed(1) + "%</td>";
        html += "<td>" + confBadge(s.confident) + "</td>";
        html += "<td>" + (s.actual >= 0.5 ? "命中" : "未中") + "</td>";
        html += "<td>" + (s.correct === null ? "-" : s.correct ? "正确" : "错误") + "</td>";
        html += "<td>" + layerBadge(s.split_layer) + "</td>";
        html += "</tr>";
      });
      html += "</tbody></table>";
      var summaryHtml = '<div style="margin-bottom:0.5rem;font-size:0.82rem;color:#495057;">';
      summaryHtml += layerBadge(data.split_layer) + " | ";
      for (var tag in data.summary) {
        var st = data.summary[tag];
        summaryHtml += tag + ": " + st.confident + "/" + st.total + " 高置信";
        if (st.accuracy != null) summaryHtml += " (acc " + pct(st.accuracy) + ")";
        summaryHtml += " | ";
      }
      summaryHtml += "</div>";
      wrap.innerHTML = summaryHtml + html;
    }).catch(function (e) {
      wrap.innerHTML = '<div class="error-msg">' + e.message + "</div>";
    });
  }

  // ── Stock Search ──
  $("#stock-search-btn").addEventListener("click", loadStock);
  $("#stock-query").addEventListener("keydown", function (e) { if (e.key === "Enter") loadStock(); });

  function loadStock() {
    var q = $("#stock-query").value.trim();
    if (!q) return;
    var wrap = $("#stock-result");
    wrap.innerHTML = '<div class="loading">搜索中...</div>';
    fetchJSON(API + "/stock?q=" + encodeURIComponent(q)).then(function (data) {
      if (!data.predictions || data.predictions.length === 0) {
        var msg = data.message || "未找到该股票的信号";
        wrap.innerHTML = '<div class="loading">' + msg + '</div>';
        return;
      }
      var html = '<div style="margin-bottom:0.5rem;font-size:0.9rem;font-weight:600;">' + data.symbol + " " + (data.name || "") + "</div>";
      for (var tag in data.summary_by_model) {
        var st = data.summary_by_model[tag];
        html += '<div style="font-size:0.82rem;color:#495057;margin-bottom:0.3rem;">' + tag + ": 共" + st.total + "天, 高置信" + st.confident_count + "天";
        if (st.confident_accuracy != null) html += ", 高置信acc=" + pct(st.confident_accuracy);
        html += "</div>";
      }
      html += '<table class="signal-table"><thead><tr>';
      html += "<th>日期</th><th>模型</th><th>概率</th><th>置信</th><th>实际</th><th>正确</th><th>层</th>";
      html += "</tr></thead><tbody>";
      data.predictions.forEach(function (s) {
        html += "<tr>";
        html += "<td>" + s.date + "</td>";
        html += "<td>" + s.model_tag + "</td>";
        html += "<td>" + (s.probability * 100).toFixed(1) + "%</td>";
        html += "<td>" + confBadge(s.confident) + "</td>";
        html += "<td>" + (s.actual >= 0.5 ? "命中" : "未中") + "</td>";
        html += "<td>" + (s.correct === null ? "-" : s.correct ? "正确" : "错误") + "</td>";
        html += "<td>" + layerBadge(s.split_layer) + "</td>";
        html += "</tr>";
      });
      html += "</tbody></table>";
      wrap.innerHTML = html;
    }).catch(function (e) {
      wrap.innerHTML = '<div class="error-msg">' + e.message + "</div>";
    });
  }

  // ── Backtest Chart ──
  function loadBacktest() {
    fetchJSON(API + "/backtest").then(function (data) {
      renderBacktestChart(data);
      renderBacktestStats(data);
    }).catch(function (e) {
      $("#backtest-chart").innerHTML = '<div class="error-msg">' + e.message + "</div>";
    });
  }

  function renderBacktestChart(data) {
    var container = $("#backtest-chart");
    backtestChart = echarts.init(container);

    var tags = {};
    data.daily_series.forEach(function (d) {
      if (!tags[d.model_tag]) tags[d.model_tag] = { dates: [], acc: [], cov: [], layers: [] };
      tags[d.model_tag].dates.push(d.date);
      tags[d.model_tag].acc.push(d.accuracy);
      tags[d.model_tag].cov.push(d.coverage);
      tags[d.model_tag].layers.push(d.split_layer);
    });

    var series = [];
    var colors = { accuracy_priority: "#2563eb", coverage_priority: "#059669" };
    var allDates = [];

    for (var tag in tags) {
      var t = tags[tag];
      allDates = allDates.concat(t.dates);
      series.push({
        name: tag + " 准确率",
        type: "line",
        yAxisIndex: 0,
        data: t.dates.map(function (d, i) { return [d, t.acc[i]]; }),
        lineStyle: { width: 1.5 },
        symbol: "none",
        color: colors[tag] || "#666",
      });
      series.push({
        name: tag + " 覆盖率",
        type: "line",
        yAxisIndex: 1,
        data: t.dates.map(function (d, i) { return [d, t.cov[i]]; }),
        lineStyle: { width: 1, type: "dashed" },
        symbol: "none",
        color: colors[tag] || "#666",
        opacity: 0.6,
      });
    }

    allDates = Array.from(new Set(allDates)).sort();
    var splitDate = "2026-01-01";
    var markAreas = [];
    if (allDates.length > 0) {
      var first = allDates[0];
      var last = allDates[allDates.length - 1];
      if (first < splitDate) {
        markAreas.push([
          { xAxis: first, itemStyle: { color: "rgba(37,99,235,0.06)" } },
          { xAxis: splitDate < last ? splitDate : last }
        ]);
      }
      if (last >= splitDate) {
        markAreas.push([
          { xAxis: splitDate > first ? splitDate : first, itemStyle: { color: "rgba(106,27,154,0.06)" } },
          { xAxis: last }
        ]);
      }
    }

    if (series.length > 0 && markAreas.length > 0) {
      series[0].markArea = { silent: true, data: markAreas };
    }

    backtestChart.setOption({
      tooltip: { trigger: "axis" },
      legend: { bottom: 0, textStyle: { fontSize: 11 } },
      grid: { left: 60, right: 60, top: 30, bottom: 50 },
      xAxis: { type: "category", data: allDates, axisLabel: { fontSize: 10 } },
      yAxis: [
        { type: "value", name: "准确率", min: 0.5, max: 1.0, axisLabel: { formatter: function (v) { return (v * 100).toFixed(0) + "%"; } } },
        { type: "value", name: "覆盖率", min: 0, max: 0.5, position: "right", axisLabel: { formatter: function (v) { return (v * 100).toFixed(0) + "%"; } } }
      ],
      series: series,
    });
    window.addEventListener("resize", function () { backtestChart && backtestChart.resize(); });
  }

  function renderBacktestStats(data) {
    var container = $("#backtest-stats");
    var html = "";
    data.by_model.forEach(function (m) {
      html += '<div><h4 style="margin:0 0 0.5rem;">' + m.model_tag + " (" + m.best_model + ")</h4>";
      html += '<table class="stats-table"><thead><tr><th>层</th><th>总行数</th><th>高置信数</th><th>准确率</th><th>覆盖率</th><th>Wilson 95%</th><th>Brier</th><th>基线 Brier</th></tr></thead><tbody>';
      m.by_layer.forEach(function (l) {
        html += "<tr>";
        html += "<td style='text-align:left'>" + layerBadge(l.layer) + "</td>";
        html += "<td>" + l.total_rows + "</td>";
        html += "<td>" + l.confident_count + "</td>";
        html += "<td>" + pct(l.confident_accuracy) + "</td>";
        html += "<td>" + pct(l.confident_coverage) + "</td>";
        html += "<td>" + pct(l.wilson_lower_95) + "</td>";
        html += "<td>" + l.brier.toFixed(4) + "</td>";
        html += "<td>" + l.baseline_brier.toFixed(4) + "</td>";
        html += "</tr>";
      });
      html += "</tbody></table>";
      if (m.artifact_reference) {
        var ref = m.artifact_reference;
        html += '<div style="margin-top:0.3rem;font-size:0.75rem;color:#6b7280;">Artifact 参考: acc=' + pct(ref.hc_accuracy) + " cov=" + pct(ref.hc_coverage) + " count=" + (ref.hc_count || "?") + " wilson=" + pct(ref.hc_wilson_lower_95) + "</div>";
      }
      html += "</div>";
    });
    container.innerHTML = html;
  }

  document.addEventListener("DOMContentLoaded", init);
})();
