from __future__ import annotations

import html
import io
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

from ashare_similarity.config import AppConfig
from ashare_similarity.data.base import Frequency
from ashare_similarity.data.service import DataService
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.features.encoder import encode_window
from ashare_similarity.features.models import QueryWindow
from ashare_similarity.indexing.compact_builder import COMPACT_STORAGE_FORMAT
from ashare_similarity.features.service import FeatureService
from ashare_similarity.indexing.service import IndexService, SearchableIndex
from ashare_similarity.schemas import (
    AggregateForwardStat,
    ForwardStats,
    MatchResult,
    MatchSeries,
    QueryMeta,
    ScoreBreakdown,
    SearchRequest,
    SearchResponse,
)
from ashare_similarity.search.scoring import DistanceBreakdown, score_window_pair


@dataclass(slots=True)
class CandidateMatch:
    row: pd.Series
    score: ScoreBreakdown
    distances: DistanceBreakdown


def select_top_matches(
    *,
    candidates: list[dict[str, Any]] | None = None,
    candidate_rows: list[dict[str, Any]] | None = None,
    candidate_frame: pd.DataFrame | None = None,
    top_k: int = 10,
    max_matches_per_symbol: int = 2,
    overlap_days_limit: int = 2,
) -> dict[str, list[dict[str, Any]]]:
    rows: list[dict[str, Any]]
    if candidate_rows is not None:
        rows = [dict(item) for item in candidate_rows]
    elif candidates is not None:
        rows = [dict(item) for item in candidates]
    elif candidate_frame is not None:
        rows = candidate_frame.to_dict(orient="records")
    else:
        rows = []

    balanced = _select_ranked_rows(
        rows=rows,
        score_key="balanced",
        top_k=top_k,
        max_matches_per_symbol=max_matches_per_symbol,
        overlap_days_limit=overlap_days_limit,
    )
    shape = _select_ranked_rows(
        rows=rows,
        score_key="shape",
        top_k=top_k,
        max_matches_per_symbol=max_matches_per_symbol,
        overlap_days_limit=overlap_days_limit,
    )
    return {"balanced_matches": balanced, "shape_matches": shape}


class SearchService:
    def __init__(
        self,
        config: AppConfig,
        store: LocalDataStore,
        data_service: DataService,
        feature_service: FeatureService,
        index_service: IndexService,
    ) -> None:
        self.config = config
        self.store = store
        self.data_service = data_service
        self.feature_service = feature_service
        self.index_service = index_service

    def search(self, request: SearchRequest) -> SearchResponse:
        self._ensure_index(request.frequency, request.window_size)
        query = self.feature_service.build_query_frame(
            symbol=request.symbol,
            end_date=request.end_date,
            frequency=request.frequency,
            window_size=request.window_size,
            ensure_remote=False,
        )
        searchable = self.index_service.load(request.frequency, request.window_size)
        stale_warning = self._index_staleness_warning(request.frequency, searchable)
        if stale_warning:
            raise ValueError(
                f"{stale_warning} 请先离线重建索引，避免用旧样本库给出误导性结果。"
            )
        component_slices = searchable.manifest.get("component_slices") or query.component_slices

        candidate_matches = self._collect_candidates(
            searchable=searchable,
            query=query,
            component_slices=component_slices,
            top_k=request.top_k,
            search_scope=request.search_scope,
        )
        history_cache: dict[tuple[str, Frequency], pd.DataFrame] = {}

        balanced_matches = self._build_ranked_matches(
            candidate_matches=candidate_matches,
            query=query,
            frequency=request.frequency,
            score_key="balanced",
            top_k=request.top_k,
            history_cache=history_cache,
        )
        shape_matches = self._build_ranked_matches(
            candidate_matches=candidate_matches,
            query=query,
            frequency=request.frequency,
            score_key="shape",
            top_k=request.top_k,
            history_cache=history_cache,
        )

        warnings = list(query.warnings)
        if request.frequency != "daily" and self.config.data_source.minute_history_notice:
            warnings.append(self.config.data_source.minute_history_notice)
        if len(balanced_matches) < request.top_k:
            warnings.append(f"仅有 {len(balanced_matches)} 条综合相似结果通过去重过滤。")
        if len(shape_matches) < request.top_k:
            warnings.append(f"仅有 {len(shape_matches)} 条形态相似结果通过去重过滤。")

        warnings = list(dict.fromkeys(warnings))
        freshness = self._get_data_freshness(request.frequency)
        return SearchResponse(
            query_meta=self._query_meta(
                query=query,
                searchable=searchable,
                candidate_pool_size=len(candidate_matches),
            ),
            balanced_matches=balanced_matches,
            shape_matches=shape_matches,
            aggregate_forward_stats=self._aggregate_forward(balanced_matches),
            data_freshness=freshness,
            warnings=warnings,
        )

    def select_top_matches(self, **kwargs: Any) -> dict[str, list[dict[str, Any]]]:
        return select_top_matches(**kwargs)

    def export_csv(self, response: SearchResponse) -> bytes:
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
        for horizon in self.config.ranking.forward_windows:
            columns.extend(
                [
                    f"return_{horizon}d_pct",
                    f"mfe_{horizon}d_pct",
                    f"mdd_{horizon}d_pct",
                ]
            )
        rows: list[dict[str, Any]] = []
        for bucket, matches in (("balanced", response.balanced_matches), ("shape", response.shape_matches)):
            for rank, match in enumerate(matches, start=1):
                row: dict[str, Any] = {
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

    def export_html(self, response: SearchResponse) -> str:
        generated_at = datetime.now().isoformat(timespec="seconds")
        frequency_label = self._frequency_label(response.query_meta.frequency)
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

    def _ensure_index(self, frequency: Frequency, window_size: int) -> None:
        if self.index_service.exists(frequency, window_size):
            return
        raise ValueError(
            f"当前缺少 {self._frequency_label(frequency)} 窗口 {window_size} 的本地索引，请先运行 "
            "`python -m ashare_similarity.cli maintain` 或 "
            f"`python -m ashare_similarity.cli build --frequency {frequency} --window-size {window_size}`。"
        )

    def _collect_candidates(
        self,
        *,
        searchable: SearchableIndex,
        query: QueryWindow,
        component_slices: dict[str, tuple[int, int]],
        top_k: int,
        search_scope: str = "historical",
    ) -> list[CandidateMatch]:
        recall_k = min(
            _searchable_row_count(searchable),
            max(self.config.ranking.recall_k, top_k * 25),
        )
        candidates = self._score_recall(
            searchable=searchable,
            query=query,
            component_slices=component_slices,
            recall_k=recall_k,
            search_scope=search_scope,
        )
        if len(candidates) >= top_k * 2 or recall_k >= _searchable_row_count(searchable):
            return candidates
        expanded_recall_k = min(
            _searchable_row_count(searchable),
            max(recall_k * 4, top_k * 200, self.config.ranking.recall_k * 4),
        )
        if expanded_recall_k <= recall_k:
            return candidates
        return self._score_recall(
            searchable=searchable,
            query=query,
            component_slices=component_slices,
            recall_k=expanded_recall_k,
            search_scope=search_scope,
        )

    def _score_recall(
        self,
        *,
        searchable: SearchableIndex,
        query: QueryWindow,
        component_slices: dict[str, tuple[int, int]],
        recall_k: int,
        search_scope: str = "historical",
    ) -> list[CandidateMatch]:
        _, indices = searchable.search(query.matrix.astype(np.float32), recall_k)
        seen_indices: set[int] = set()
        matches: list[CandidateMatch] = []
        vector_cache: dict[tuple[str, str, str], np.ndarray] = {}
        history_cache: dict[tuple[str, Frequency], pd.DataFrame] = {}

        for raw_index in indices.tolist():
            row_index = int(raw_index)
            if row_index < 0 or row_index >= _searchable_row_count(searchable):
                continue
            if row_index in seen_indices:
                continue
            seen_indices.add(row_index)

            row = _searchable_metadata_row(searchable, row_index)
            if self._overlaps_query(query, row):
                continue
            if search_scope == "historical" and self._overlaps_query_period(query, row):
                continue

            candidate_vector = self._candidate_vector(
                searchable=searchable,
                row_index=row_index,
                row=row,
                frequency=query.frequency,
                vector_cache=vector_cache,
                history_cache=history_cache,
            )
            if candidate_vector is None:
                continue

            score, distances = score_window_pair(
                query_vector=query.matrix[0],
                candidate_vector=candidate_vector,
                component_slices=component_slices,
                weights=self.config.search_weights,
            )
            matches.append(CandidateMatch(row=row, score=score, distances=distances))

        return matches

    def _candidate_vector(
        self,
        *,
        searchable: SearchableIndex,
        row_index: int,
        row: pd.Series,
        frequency: Frequency,
        vector_cache: dict[tuple[str, str, str], np.ndarray],
        history_cache: dict[tuple[str, Frequency], pd.DataFrame],
    ) -> np.ndarray | None:
        matrix = searchable.matrix
        if (
            getattr(matrix, "ndim", 0) == 2
            and matrix.shape[1] > 0
            and 0 <= row_index < matrix.shape[0]
            and searchable.manifest.get("storage_format") != COMPACT_STORAGE_FORMAT
        ):
            return np.asarray(matrix[row_index], dtype=np.float32)

        cache_key = (
            str(row.get("symbol", "")),
            str(row.get("start_date", "")),
            str(row.get("end_date", "")),
        )
        cached = vector_cache.get(cache_key)
        if cached is not None:
            return cached

        series = self._load_match_series(row, frequency, history_cache=history_cache)
        if series.empty:
            return None
        industry = _optional_text(row.get("industry"))
        enricher = getattr(self.feature_service, "_enrich_with_context", None)
        if callable(enricher):
            series = enricher(series, industry, frequency)
        encoded = encode_window(series)
        vector_cache[cache_key] = encoded.vector
        return encoded.vector

    def _build_ranked_matches(
        self,
        *,
        candidate_matches: list[CandidateMatch],
        query: QueryWindow,
        frequency: Frequency,
        score_key: str,
        top_k: int,
        history_cache: dict[tuple[str, Frequency], pd.DataFrame],
    ) -> list[MatchResult]:
        ordered = sorted(
            candidate_matches,
            key=lambda item: (
                -float(getattr(item.score, score_key)),
                float(item.distances.balanced_distance),
                str(item.row.get("symbol", "")),
                str(item.row.get("end_date", "")),
            ),
        )

        accepted: list[MatchResult] = []
        fallback: list[tuple[MatchResult, str, tuple[pd.Timestamp, pd.Timestamp]]] = []
        counts: defaultdict[str, int] = defaultdict(int)
        ranges_by_symbol: defaultdict[str, list[tuple[pd.Timestamp, pd.Timestamp]]] = defaultdict(list)

        for candidate in ordered:
            symbol = str(candidate.row.get("symbol", "")).strip()
            if counts[symbol] >= self.config.ranking.max_matches_per_symbol:
                continue

            candidate_range = (
                pd.Timestamp(candidate.row.get("start_date")),
                pd.Timestamp(candidate.row.get("end_date")),
            )
            if any(
                _overlap_days(candidate_range, accepted_range) > self.config.ranking.overlap_days_limit
                for accepted_range in ranges_by_symbol[symbol]
            ):
                continue

            match = self._build_match(
                candidate.row,
                candidate.score,
                frequency,
                history_cache=history_cache,
            )
            if self._has_forward_data(match):
                accepted.append(match)
                counts[symbol] += 1
                ranges_by_symbol[symbol].append(candidate_range)
            else:
                fallback.append((match, symbol, candidate_range))
            if len(accepted) >= top_k:
                break

        if len(accepted) < top_k:
            for match, symbol, candidate_range in fallback:
                if counts[symbol] >= self.config.ranking.max_matches_per_symbol:
                    continue
                if any(
                    _overlap_days(candidate_range, accepted_range) > self.config.ranking.overlap_days_limit
                    for accepted_range in ranges_by_symbol[symbol]
                ):
                    continue
                accepted.append(match)
                counts[symbol] += 1
                ranges_by_symbol[symbol].append(candidate_range)
                if len(accepted) >= top_k:
                    break

        return accepted

    def _build_match(
        self,
        row: pd.Series,
        score: ScoreBreakdown,
        frequency: Frequency,
        *,
        history_cache: dict[tuple[str, Frequency], pd.DataFrame],
    ) -> MatchResult:
        series = self._load_match_series(row, frequency, history_cache=history_cache)
        return MatchResult(
            symbol=str(row["symbol"]),
            name=_optional_text(row.get("name")),
            frequency=frequency,
            start_date=pd.Timestamp(row["start_date"]).isoformat(),
            end_date=pd.Timestamp(row["end_date"]).isoformat(),
            listing_days=_optional_int(row.get("listing_days")),
            industry=_optional_text(row.get("industry")),
            scores=score,
            forward_stats=self._compute_forward_stats(row, frequency, history_cache=history_cache),
            series=self._series_to_schema(series, frequency),
            explanation=self._build_explanations(row, score),
        )

    def _build_explanations(self, row: pd.Series, score: ScoreBreakdown) -> list[str]:
        notes = [
            f"综合相似度 {score.balanced:.4f}，形态相似度 {score.shape:.4f}",
            f"价格路径距离 {score.price_path_distance:.4f}，蜡烛几何距离 {score.candle_geometry_distance:.4f}",
        ]
        if pd.notna(row.get("industry")) and row.get("industry"):
            notes.append(f"行业环境：{row['industry']}")
        return notes

    def _load_match_series(
        self,
        row: pd.Series,
        frequency: Frequency,
        *,
        history_cache: dict[tuple[str, Frequency], pd.DataFrame],
    ) -> pd.DataFrame:
        bars = self._cached_price_history(
            symbol=str(row["symbol"]),
            frequency=frequency,
            history_cache=history_cache,
        )
        if bars.empty:
            return bars
        time_col = self._bars_time_col(frequency)
        bars[time_col] = pd.to_datetime(bars[time_col])
        start = pd.Timestamp(row["start_date"])
        end = pd.Timestamp(row["end_date"])
        return bars[(bars[time_col] >= start) & (bars[time_col] <= end)].copy().reset_index(drop=True)

    def _compute_forward_stats(
        self,
        row: pd.Series,
        frequency: Frequency,
        *,
        history_cache: dict[tuple[str, Frequency], pd.DataFrame],
    ) -> list[ForwardStats]:
        bars = self._cached_price_history(
            symbol=str(row["symbol"]),
            frequency=frequency,
            history_cache=history_cache,
        )
        if bars.empty:
            return [
                ForwardStats(
                    horizon=horizon,
                    return_pct=None,
                    max_favorable_excursion_pct=None,
                    max_drawdown_pct=None,
                )
                for horizon in self.config.ranking.forward_windows
            ]

        time_col = self._bars_time_col(frequency)
        bars[time_col] = pd.to_datetime(bars[time_col])
        end_ts = pd.Timestamp(row["end_date"])
        matched = bars.index[bars[time_col] == end_ts]
        if len(matched) == 0:
            return [
                ForwardStats(
                    horizon=horizon,
                    return_pct=None,
                    max_favorable_excursion_pct=None,
                    max_drawdown_pct=None,
                )
                for horizon in self.config.ranking.forward_windows
            ]

        entry_index = int(matched[0])
        entry_close = float(bars.iloc[entry_index]["close"])
        stats: list[ForwardStats] = []
        for horizon in self.config.ranking.forward_windows:
            future = bars.iloc[entry_index + 1 : entry_index + horizon + 1]
            if len(future) < horizon:
                stats.append(
                    ForwardStats(
                        horizon=horizon,
                        return_pct=None,
                        max_favorable_excursion_pct=None,
                        max_drawdown_pct=None,
                    )
                )
                continue
            return_pct = (float(future.iloc[-1]["close"]) - entry_close) / entry_close * 100.0
            mfe = (float(future["high"].max()) - entry_close) / entry_close * 100.0
            mdd = (float(future["low"].min()) - entry_close) / entry_close * 100.0
            stats.append(
                ForwardStats(
                    horizon=horizon,
                    return_pct=round(return_pct, 4),
                    max_favorable_excursion_pct=round(mfe, 4),
                    max_drawdown_pct=round(mdd, 4),
                )
            )
        return stats

    def _has_forward_data(self, match: MatchResult) -> bool:
        return any(stat.return_pct is not None for stat in match.forward_stats)

    def _index_staleness_warning(self, frequency: Frequency, searchable: SearchableIndex) -> str | None:
        cached_symbols = len(self.store.list_cached_symbols(frequency))
        index_symbols = _searchable_symbol_count(searchable)
        covered_symbols = max(index_symbols, _searchable_built_symbol_count(searchable))
        if cached_symbols and covered_symbols and covered_symbols < cached_symbols:
            return (
                f"当前索引仅覆盖 {index_symbols}/{cached_symbols} 只已缓存标的；"
                "最新补齐的样本需要在离线重建索引后才会进入候选池。"
            )

        built_from = searchable.manifest.get("built_from") or {}
        built_latest_data_at = built_from.get("latest_data_at")
        freshness_latest_data_at = self._freshness_latest_data_at(self._get_data_freshness(frequency))
        if built_latest_data_at and freshness_latest_data_at:
            if pd.Timestamp(built_latest_data_at) < pd.Timestamp(freshness_latest_data_at):
                return (
                    "当前索引早于本地最新行情缓存；"
                    "新增交易日的数据尚未并入相似样本库，建议先离线重建对应窗口索引。"
                )
        return None

    def _aggregate_forward(self, matches: list[MatchResult]) -> list[AggregateForwardStat]:
        rows: list[AggregateForwardStat] = []
        for horizon in self.config.ranking.forward_windows:
            horizon_rows = [
                stat
                for match in matches
                for stat in match.forward_stats
                if stat.horizon == horizon and stat.return_pct is not None
            ]
            if not horizon_rows:
                rows.append(
                    AggregateForwardStat(
                        horizon=horizon,
                        avg_return_pct=None,
                        win_rate=None,
                        avg_max_favorable_excursion_pct=None,
                        avg_max_drawdown_pct=None,
                    )
                )
                continue

            returns = np.asarray([item.return_pct for item in horizon_rows], dtype=float)
            mfes = np.asarray(
                [item.max_favorable_excursion_pct for item in horizon_rows if item.max_favorable_excursion_pct is not None],
                dtype=float,
            )
            mdds = np.asarray(
                [item.max_drawdown_pct for item in horizon_rows if item.max_drawdown_pct is not None],
                dtype=float,
            )
            rows.append(
                AggregateForwardStat(
                    horizon=horizon,
                    avg_return_pct=round(float(np.nanmean(returns)), 4),
                    win_rate=round(float(np.mean(returns > 0)), 4),
                    avg_max_favorable_excursion_pct=round(float(np.nanmean(mfes)), 4) if mfes.size else None,
                    avg_max_drawdown_pct=round(float(np.nanmean(mdds)), 4) if mdds.size else None,
                )
            )
        return rows

    def _query_meta(
        self,
        *,
        query: QueryWindow,
        searchable: SearchableIndex,
        candidate_pool_size: int,
    ) -> QueryMeta:
        return QueryMeta(
            symbol=query.symbol,
            frequency=query.frequency,
            window_size=query.window_size,
            start_date=str(query.metadata["start_date"]),
            end_date=str(query.metadata["end_date"]),
            query_series=self._series_to_schema(query.series, query.frequency),
            universe_size=_searchable_symbol_count(searchable),
            candidate_pool_size=candidate_pool_size,
            filters=[
                "默认历史优先：排除与目标窗口日期段重叠过多的同期横截面样本。",
                f"过滤同一标的中与目标窗口重叠超过 {self.config.ranking.overlap_days_limit} 个自然日的样本。",
                f"每个榜单中，同一只股票最多保留 {self.config.ranking.max_matches_per_symbol} 条结果。",
            ],
        )

    def _frequency_label(self, frequency: Frequency) -> str:
        labels = {
            "daily": "日线",
            "1": "1分钟",
            "5": "5分钟",
            "15": "15分钟",
            "30": "30分钟",
            "60": "60分钟",
        }
        return labels.get(frequency, str(frequency))

    def _series_to_schema(self, series: pd.DataFrame, frequency: Frequency) -> MatchSeries:
        if series.empty:
            return MatchSeries(dates=[], open=[], high=[], low=[], close=[], volume=[])
        time_col = self._bars_time_col(frequency)
        return MatchSeries(
            dates=[pd.Timestamp(value).isoformat() for value in series[time_col].tolist()],
            open=[float(value) for value in series["open"].tolist()],
            high=[float(value) for value in series["high"].tolist()],
            low=[float(value) for value in series["low"].tolist()],
            close=[float(value) for value in series["close"].tolist()],
            volume=[float(value) for value in series["volume"].tolist()],
        )

    def _bars_time_col(self, frequency: Frequency) -> str:
        return "date" if frequency == "daily" else "timestamp"

    def _overlaps_query(self, query: QueryWindow, candidate_row: pd.Series) -> bool:
        if query.symbol != str(candidate_row.get("symbol", "")).strip():
            return False
        return self._overlaps_query_period(query, candidate_row)

    def _overlaps_query_period(self, query: QueryWindow, candidate_row: pd.Series) -> bool:
        query_range = (
            pd.Timestamp(query.metadata["start_date"]),
            pd.Timestamp(query.metadata["end_date"]),
        )
        candidate_range = (
            pd.Timestamp(candidate_row["start_date"]),
            pd.Timestamp(candidate_row["end_date"]),
        )
        return _overlap_days(query_range, candidate_range) > self.config.ranking.overlap_days_limit

    def _get_data_freshness(self, frequency: Frequency):
        if hasattr(self.data_service, "get_data_freshness"):
            return self.data_service.get_data_freshness(frequency)
        if hasattr(self.store, "get_freshness"):
            return self.store.get_freshness(frequency)
        return {
            "last_refresh_at": None,
            "latest_data_at": None,
            "data_source": self.config.data_source.provider,
            "notice": None,
        }

    def _freshness_latest_data_at(self, freshness: Any) -> Any | None:
        if isinstance(freshness, dict):
            return freshness.get("latest_data_at")
        return getattr(freshness, "latest_data_at", None)

    def _cached_price_history(
        self,
        *,
        symbol: str,
        frequency: Frequency,
        history_cache: dict[tuple[str, Frequency], pd.DataFrame],
    ) -> pd.DataFrame:
        cache_key = (symbol, frequency)
        if cache_key not in history_cache:
            history_cache[cache_key] = self._load_price_history(
                symbol=symbol,
                frequency=frequency,
                ensure_remote=False,
            )
        return history_cache[cache_key].copy()

    def _load_price_history(
        self,
        *,
        symbol: str,
        frequency: Frequency,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        ensure_remote: bool = False,
    ) -> pd.DataFrame:
        if hasattr(self.data_service, "load_price_history"):
            return self.data_service.load_price_history(
                symbol=symbol,
                frequency=frequency,
                start_date=start_date,
                end_date=end_date,
                ensure_remote=ensure_remote,
            )

        if hasattr(self.store, "load_bars"):
            return self.store.load_bars(
                symbol=symbol,
                frequency=frequency,
                start_date=start_date,
                end_date=end_date,
            )

        if hasattr(self.data_service, "get_market_data"):
            frame = self.data_service.get_market_data(
                frequency=frequency,
                symbols=[symbol],
                start_date=start_date,
                end_date=end_date,
            )
            if hasattr(frame, "to_pandas"):
                return frame.to_pandas()
        return pd.DataFrame()


def _select_ranked_rows(
    *,
    rows: list[dict[str, Any]],
    score_key: str,
    top_k: int,
    max_matches_per_symbol: int,
    overlap_days_limit: int,
) -> list[dict[str, Any]]:
    ordered = sorted(
        rows,
        key=lambda row: float(_nested_score(row, score_key)),
        reverse=True,
    )
    accepted: list[dict[str, Any]] = []
    counts: defaultdict[str, int] = defaultdict(int)
    ranges_by_symbol: defaultdict[str, list[tuple[pd.Timestamp, pd.Timestamp]]] = defaultdict(list)
    for row in ordered:
        symbol = str(row.get("symbol", "")).strip()
        if counts[symbol] >= max_matches_per_symbol:
            continue
        candidate_range = (pd.Timestamp(row["start_date"]), pd.Timestamp(row["end_date"]))
        if any(_overlap_days(candidate_range, existing) > overlap_days_limit for existing in ranges_by_symbol[symbol]):
            continue
        accepted.append(row)
        counts[symbol] += 1
        ranges_by_symbol[symbol].append(candidate_range)
        if len(accepted) >= top_k:
            break
    return accepted


def _searchable_row_count(searchable: Any) -> int:
    row_count = getattr(searchable, "row_count", None)
    if row_count is not None:
        return int(row_count)
    metadata = getattr(searchable, "metadata", None)
    if metadata is None:
        return 0
    if hasattr(metadata, "index"):
        return int(len(metadata.index))
    try:
        return int(len(metadata))
    except TypeError:
        return 0


def _searchable_metadata_row(searchable: Any, row_index: int) -> pd.Series:
    if hasattr(searchable, "metadata_row"):
        return searchable.metadata_row(row_index)
    metadata = getattr(searchable, "metadata")
    if hasattr(metadata, "row_at"):
        return metadata.row_at(row_index)
    return metadata.iloc[int(row_index)].copy()


def _searchable_symbol_count(searchable: Any) -> int:
    symbol_count = getattr(searchable, "symbol_count", None)
    if symbol_count is not None:
        return int(symbol_count)
    manifest = getattr(searchable, "manifest", {}) or {}
    manifest_symbol_count = int(manifest.get("symbol_count") or 0)
    if manifest_symbol_count:
        return manifest_symbol_count
    metadata = getattr(searchable, "metadata", None)
    if metadata is None:
        return 0
    if hasattr(metadata, "symbol_nunique"):
        return int(metadata.symbol_nunique())
    if hasattr(metadata, "columns") and "symbol" in metadata.columns:
        return int(metadata["symbol"].nunique())
    return 0


def _searchable_built_symbol_count(searchable: Any) -> int:
    manifest = getattr(searchable, "manifest", {}) or {}
    return int((manifest.get("built_from") or {}).get("symbols_count") or 0)


def _nested_score(row: dict[str, Any], score_key: str) -> float:
    scores = row.get("scores") or {}
    if isinstance(scores, dict):
        return float(scores.get(score_key, 0.0))
    return float(getattr(scores, score_key, 0.0))


def _overlap_days(
    left: tuple[pd.Timestamp, pd.Timestamp],
    right: tuple[pd.Timestamp, pd.Timestamp],
) -> int:
    overlap_start = max(left[0], right[0])
    overlap_end = min(left[1], right[1])
    if overlap_end < overlap_start:
        return 0
    return int((overlap_end.normalize() - overlap_start.normalize()).days + 1)


def _optional_text(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return int(value)
