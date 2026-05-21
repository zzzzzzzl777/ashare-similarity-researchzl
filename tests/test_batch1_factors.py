"""Unit tests for Batch 1 daily factors: MAX, Corwin-Schultz, skew, double-shot."""
from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from ashare_similarity.prediction.gpu_probe import (
    _corwin_schultz,
    _limit_up_double_shot,
    _rolling_max,
    _rolling_skew,
    _rolling_sum,
)


@pytest.fixture
def device():
    return torch.device("cpu")


class TestMaxReturn1d20:
    def test_known_spike(self, device):
        rets = torch.zeros(30, device=device)
        rets[10] = 8.0  # big up day
        result = _rolling_max(rets, 20)
        assert result[10].item() == pytest.approx(8.0)
        assert result[15].item() == pytest.approx(8.0)
        assert result[29].item() == pytest.approx(8.0)

    def test_decaying_window(self, device):
        rets = torch.zeros(40, device=device)
        rets[5] = 5.0
        result = _rolling_max(rets, 20)
        assert result[24].item() == pytest.approx(5.0)
        assert result[30].item() == pytest.approx(0.0)


class TestMaxReturn5d60:
    def test_cumulative_spike(self, device):
        rets = torch.zeros(80, device=device)
        rets[10:15] = 2.0  # 5 consecutive +2% days
        cumulative_5d = _rolling_sum(rets, 5)
        result = _rolling_max(cumulative_5d, 60)
        assert result[14].item() == pytest.approx(10.0)
        assert result[50].item() == pytest.approx(10.0)


class TestCorwinSchultzSpread:
    def test_tight_spread(self, device):
        n = 40
        close = torch.full((n,), 10.0, device=device)
        high = close * 1.001
        low = close * 0.999
        spread = _corwin_schultz(high, low, close, window=10)
        assert spread[-1].item() < 0.01

    def test_wide_spread(self, device):
        n = 40
        np.random.seed(123)
        close = torch.tensor(10.0 + np.cumsum(np.random.normal(0, 0.3, n)), dtype=torch.float32, device=device)
        high = close + torch.abs(torch.randn(n, device=device)) * 0.5
        low = close - torch.abs(torch.randn(n, device=device)) * 0.5
        spread = _corwin_schultz(high, low, close, window=10)
        assert spread[-1].item() >= 0.0


class TestRealizedSkew20:
    def test_symmetric_returns_near_zero(self, device):
        np.random.seed(42)
        rets = torch.tensor(np.random.normal(0, 1, 40), dtype=torch.float32, device=device)
        skew = _rolling_skew(rets, 20)
        assert abs(skew[-1].item()) < 2.0

    def test_positive_skew(self, device):
        rets = torch.zeros(30, device=device)
        rets[25] = 10.0  # one large positive outlier
        skew = _rolling_skew(rets, 20)
        assert skew[29].item() > 0.0

    def test_negative_skew(self, device):
        rets = torch.zeros(30, device=device)
        rets[25] = -10.0  # one large negative outlier
        skew = _rolling_skew(rets, 20)
        assert skew[29].item() < 0.0


class TestLimitUpDoubleShot:
    def test_classic_pattern(self, device):
        flags = torch.zeros(20, device=device)
        flags[5] = 1.0   # first limit-up
        flags[9] = 1.0   # second limit-up after 3 gap days
        result = _limit_up_double_shot(flags)
        assert result[9].item() == pytest.approx(1.0)

    def test_no_gap(self, device):
        flags = torch.zeros(20, device=device)
        flags[5] = 1.0
        flags[6] = 1.0  # consecutive limit-up, no gap
        result = _limit_up_double_shot(flags)
        assert result[6].item() == pytest.approx(0.0)

    def test_gap_too_large(self, device):
        flags = torch.zeros(20, device=device)
        flags[2] = 1.0
        flags[12] = 1.0  # 9 gap days — too far
        result = _limit_up_double_shot(flags)
        assert result[12].item() == pytest.approx(0.0)

    def test_non_limit_day_is_zero(self, device):
        flags = torch.zeros(20, device=device)
        result = _limit_up_double_shot(flags)
        assert result.sum().item() == pytest.approx(0.0)

    def test_gap_with_limit_in_middle(self, device):
        flags = torch.zeros(20, device=device)
        flags[5] = 1.0
        flags[7] = 1.0  # limit in the middle
        flags[9] = 1.0  # this is double-shot from flags[7]
        result = _limit_up_double_shot(flags)
        assert result[7].item() == pytest.approx(1.0)
        assert result[9].item() == pytest.approx(1.0)
