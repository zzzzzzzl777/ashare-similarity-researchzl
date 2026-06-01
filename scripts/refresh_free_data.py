"""Refresh AKShare free daily OHLCV bars + market indices to latest."""
import sys
import os
import logging
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "..", "logs", "data_backfill_2020_2026", "free_refresh.log"),
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("free_refresh")

from ashare_similarity.runtime import get_runtime

runtime = get_runtime()

log.info("Starting daily OHLCV refresh (all stocks, 2026-05-08 ~ 2026-05-12)")
result = runtime.data_service.refresh_market_data(
    frequency="daily",
    start_date=date(2026, 5, 8),
    end_date=date(2026, 5, 12),
    refresh_context=True,
    rebuild_industry_context=False,
)
log.info(f"Done: processed={result['symbols_processed']}, failed={len(result['failed_symbols'])}, market_context={result['market_context_rows']}")
if result["failed_symbols"]:
    log.warning(f"Failed symbols ({len(result['failed_symbols'])}): {result['failed_symbols'][:10]}")
