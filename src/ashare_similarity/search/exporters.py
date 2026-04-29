from __future__ import annotations

import html
import io
from datetime import datetime
from typing import Sequence

import pandas as pd

from ashare_similarity.schemas import SearchResponse


def render_search_response_csv(response: SearchResponse, *, forward_windows: Sequence[int]) -> bytes:
    columns = [
        "bucket",
        "rank",
        "symbol",
        "name",
        "industry",
        "start_date",
        "end_date",
        "balanced_score",
        "shape_score",
    ]
    for horizon in forward_windows:
        columns.extend(
            [
                f"return_{horizon}d_pct",
                f"mfe_{horizon}d_pct",
                f"mdd_{horizon}d_pct",
            ]
        )

    rows: list[dict[str, object]] = []
    for bucket, matches in (("balanced", response.balanced_matches), ("shape", response.shape_matches)):
        for rank, match in enumerate(matches, start=1):
            row: dict[str, object] = {
                "bucket": bucket,
                "rank": rank,
                "symbol": match.symbol,
                "name": match.name,
                "industry": match.industry,
                "start_date": match.start_date,
                "end_date": match.end_date,
                "balanced_score": match.scores.balanced,
                "shape_score": match.scores.shape,
            }
            for stat in match.forward_stats:
                row[f"return_{stat.horizon}d_pct"] = stat.return_pct
                row[f"mfe_{stat.horizon}d_pct"] = stat.max_favorable_excursion_pct
                row[f"mdd_{stat.horizon}d_pct"] = stat.max_drawdown_pct
            rows.append(row)

    buffer = io.StringIO()
    pd.DataFrame(rows, columns=columns).to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8-sig")


def render_search_response_html(response: SearchResponse) -> str:
    generated_at = datetime.now().isoformat(timespec="seconds")
    balanced_rows = "".join(
        f"""
        <tr>
          <td>{rank}</td>
          <td>{html.escape(match.symbol)}</td>
          <td>{html.escape(match.name or "-")}</td>
          <td>{html.escape(match.start_date)}</td>
          <td>{html.escape(match.end_date)}</td>
          <td>{match.scores.balanced:.4f}</td>
          <td>{match.scores.shape:.4f}</td>
        </tr>
        """
        for rank, match in enumerate(response.balanced_matches, start=1)
    )
    shape_rows = "".join(
        f"""
        <tr>
          <td>{rank}</td>
          <td>{html.escape(match.symbol)}</td>
          <td>{html.escape(match.name or "-")}</td>
          <td>{html.escape(match.start_date)}</td>
          <td>{html.escape(match.end_date)}</td>
          <td>{match.scores.shape:.4f}</td>
        </tr>
        """
        for rank, match in enumerate(response.shape_matches, start=1)
    )
    aggregate_rows = "".join(
        f"""
        <tr>
          <td>{item.horizon}日</td>
          <td>{item.avg_return_pct if item.avg_return_pct is not None else "-"}</td>
          <td>{round(item.win_rate * 100, 2) if item.win_rate is not None else "-"}</td>
          <td>{item.avg_max_favorable_excursion_pct if item.avg_max_favorable_excursion_pct is not None else "-"}</td>
          <td>{item.avg_max_drawdown_pct if item.avg_max_drawdown_pct is not None else "-"}</td>
        </tr>
        """
        for item in response.aggregate_forward_stats
    )
    warnings = "".join(f"<li>{html.escape(item)}</li>" for item in response.warnings) or "<li>无</li>"
    frequency_label = _frequency_label(response.query_meta.frequency)
    return f"""
    <html lang="zh-CN">
      <head>
        <meta charset="utf-8">
        <title>A股K线相似检索报告</title>
        <style>
          body {{
            font-family: "Segoe UI", "PingFang SC", sans-serif;
            margin: 24px;
            color: #221d16;
            background: #f7f2e9;
          }}
          h1, h2 {{
            margin-bottom: 8px;
          }}
          .meta, .warning-box {{
            padding: 16px;
            border-radius: 12px;
            background: #fffaf1;
            border: 1px solid #e7d8bf;
            margin-bottom: 20px;
          }}
          table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            margin-bottom: 24px;
          }}
          th, td {{
            padding: 10px 12px;
            border-bottom: 1px solid #eee5d6;
            text-align: left;
          }}
          th {{
            background: #f2e7d2;
          }}
        </style>
      </head>
      <body>
        <h1>A股K线相似检索报告</h1>
        <div class="meta">
          <p><strong>生成时间：</strong>{html.escape(generated_at)}</p>
          <p><strong>查询标的：</strong>{html.escape(response.query_meta.symbol)}</p>
          <p><strong>窗口区间：</strong>{html.escape(response.query_meta.start_date)} 至 {html.escape(response.query_meta.end_date)}</p>
          <p><strong>K线周期：</strong>{html.escape(frequency_label)}</p>
          <p><strong>窗口长度：</strong>{response.query_meta.window_size}</p>
          <p><strong>候选池：</strong>{response.query_meta.candidate_pool_size}</p>
        </div>

        <div class="warning-box">
          <h2>提示</h2>
          <ul>{warnings}</ul>
        </div>

        <h2>综合相似榜</h2>
        <table>
          <thead>
            <tr>
              <th>排名</th>
              <th>代码</th>
              <th>名称</th>
              <th>开始</th>
              <th>结束</th>
              <th>综合分</th>
              <th>形态分</th>
            </tr>
          </thead>
          <tbody>{balanced_rows or "<tr><td colspan='7'>无结果</td></tr>"}</tbody>
        </table>

        <h2>形态最像榜</h2>
        <table>
          <thead>
            <tr>
              <th>排名</th>
              <th>代码</th>
              <th>名称</th>
              <th>开始</th>
              <th>结束</th>
              <th>形态分</th>
            </tr>
          </thead>
          <tbody>{shape_rows or "<tr><td colspan='6'>无结果</td></tr>"}</tbody>
        </table>

        <h2>后续表现汇总</h2>
        <table>
          <thead>
            <tr>
              <th>周期</th>
              <th>平均收益</th>
              <th>胜率(%)</th>
              <th>平均最大有利波动</th>
              <th>平均最大回撤</th>
            </tr>
          </thead>
          <tbody>{aggregate_rows or "<tr><td colspan='5'>无结果</td></tr>"}</tbody>
        </table>
      </body>
    </html>
    """


def _frequency_label(frequency: str) -> str:
    if frequency == "daily":
        return "日线"
    return f"{frequency}分钟"
