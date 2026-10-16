"""Statistical inference for backtest results.

* Stationary bootstrap (Politis & Romano, 1994) for confidence intervals that
  respect serial dependence in daily returns.
* Probabilistic Sharpe Ratio and Deflated Sharpe Ratio (Bailey & Lopez de
  Prado, 2012/2014) to account for non-normal returns and multiple testing.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import stats as st

EULER_GAMMA = 0.5772156649015329


def stationary_bootstrap_indices(n: int, mean_block: float, rng: np.random.Generator, n_boot: int = 1) -> np.ndarray:
    """Stationary-bootstrap index resamples, shape (n_boot, n).

    Block lengths are geometric with mean ``mean_block``; blocks wrap around.
    """
    p = 1.0 / mean_block
    pos = np.arange(n)
    new_block = rng.random((n_boot, n)) < p
    new_block[:, 0] = True
    starts = rng.integers(n, size=(n_boot, n))
    block_pos = np.maximum.accumulate(np.where(new_block, pos, 0), axis=1)
    start_val = np.take_along_axis(starts, block_pos, axis=1)
    return (start_val + pos - block_pos) % n


def bootstrap_sharpe(
    returns: np.ndarray, n_boot: int = 2000, mean_block: float = 10.0, alpha: float = 0.10, seed: int = 0,
    periods_per_year: float = 365.0,
) -> dict[str, float]:
    """Bootstrap CI for the annualised Sharpe ratio and a one-sided p-value for SR <= 0.

    The p-value resamples the *demeaned* series (null of zero mean) and reports
    the share of resampled Sharpe ratios at least as large as the observed one.
    """
    r = np.asarray(returns, float)
    r = r[np.isfinite(r)]
    n = r.size
    if n < 30 or r.std(ddof=1) == 0:
        return {"sr": float("nan"), "lo": float("nan"), "hi": float("nan"), "p_value": float("nan")}
    ann = math.sqrt(periods_per_year)
    sr_obs = r.mean() / r.std(ddof=1) * ann
    rng = np.random.default_rng(seed)
    centred = r - r.mean()
    ix = stationary_bootstrap_indices(n, mean_block, rng, n_boot)
    s, z = r[ix], centred[ix]
    with np.errstate(invalid="ignore", divide="ignore"):
        boot = np.nan_to_num(s.mean(axis=1) / s.std(axis=1, ddof=1) * ann)
        null = np.nan_to_num(z.mean(axis=1) / z.std(axis=1, ddof=1) * ann)
    return {
        "sr": float(sr_obs),
        "lo": float(np.quantile(boot, alpha / 2)),
        "hi": float(np.quantile(boot, 1 - alpha / 2)),
        "p_value": float((null >= sr_obs).mean()),
    }


def probabilistic_sharpe_ratio(sr: float, n: int, skew: float, kurt: float, sr_benchmark: float = 0.0) -> float:
    """PSR: P(true SR > benchmark). ``sr`` and benchmark are per-period (not annualised);
    ``kurt`` is Pearson kurtosis (normal = 3)."""
    if n < 2 or not np.isfinite(sr):
        return float("nan")
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr**2
    if denom <= 0:
        return float("nan")
    z = (sr - sr_benchmark) * math.sqrt(n - 1) / math.sqrt(denom)
    return float(st.norm.cdf(z))


def expected_max_sharpe(n_trials: int, var_sr: float) -> float:
    """Expected maximum of ``n_trials`` per-period Sharpe estimates under the null (SR=0)."""
    if n_trials <= 1:
        return 0.0
    a = st.norm.ppf(1.0 - 1.0 / n_trials)
    b = st.norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    return float(math.sqrt(var_sr) * ((1 - EULER_GAMMA) * a + EULER_GAMMA * b))


def deflated_sharpe_ratio(returns: np.ndarray, n_trials: int, var_sr_trials: float | None = None) -> dict[str, float]:
    """DSR of a daily return series selected from ``n_trials`` experiments.

    If ``var_sr_trials`` (variance of per-period SR across trials) is unknown,
    the asymptotic variance of a single SR estimate, 1/(n-1), is used as a
    conservative-to-neutral stand-in.
    """
    r = np.asarray(returns, float)
    r = r[np.isfinite(r)]
    n = r.size
    if n < 30 or r.std(ddof=1) == 0:
        return {"sr_daily": float("nan"), "psr": float("nan"), "dsr": float("nan"), "sr0_daily": float("nan")}
    sr = r.mean() / r.std(ddof=1)
    skew = float(st.skew(r))
    kurt = float(st.kurtosis(r, fisher=False))
    var = var_sr_trials if var_sr_trials is not None else 1.0 / (n - 1)
    sr0 = expected_max_sharpe(n_trials, var)
    return {
        "sr_daily": float(sr),
        "psr": probabilistic_sharpe_ratio(sr, n, skew, kurt, 0.0),
        "dsr": probabilistic_sharpe_ratio(sr, n, skew, kurt, sr0),
        "sr0_daily": sr0,
    }
