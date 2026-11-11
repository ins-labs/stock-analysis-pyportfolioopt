# Source provenance and qualification state

Prepared2026-11-11 Africa/Cairo. Source only, **UNRUN**. No project import/compile/test/solver/analysis was executed during preparation. No real-market, investment, Sharia-screening or trade outcome is claimed.

## Current owning release

Fresh metadata https://pypi.org/pypi/PyPortfolioOpt/json reports **1.6.0**, MIT; metadata requires_python is absent, so do not claim an upstream Python support floor from that field. Published dependency constraints and their targetPython compatibility were inspected separately. Project https://github.com/pyportfolio/pyportfolioopt ; docs https://pyportfolioopt.readthedocs.io/en/latest/ ; releases https://pypi.org/project/pyportfolioopt/ .

Exact published wheel downloaded, digest checked and source read without import:

https://files.pythonhosted.org/packages/55/51/96055d65a76c5af14a12c3cf7c7232513c622b9a1159c42708de0fe85f98/pyportfolioopt-1.6.0-py3-none-any.whl

SHA256 `fcdff5dfb4e7d0c477d8b76e9b5aff58defc30370fc3cb096e95dd46ae43d617`.

Owning wheel files read: `pypfopt/expected_returns.py`, `risk_models.py`, `efficient_frontier/efficient_frontier.py`, `base_optimizer.py`, `__init__.py` and release MIT license copied unchanged as `UPSTREAM-LICENSE-PyPortfolioOpt.txt`. Adapter/runner itself separately MIT.

Source decisions:

- `mean_historical_return` defaults geometric, but this recipe explicitly returns_data=True/compounding=False/log_returns=False/frequency chosen; it uses daily arithmetic mean*frequency.
- `sample_cov` uses pandas sample covariance*frequency, then can silently repair non-PSD via spectral method. Prevalidate strictly positive well-conditioned sample covariance and require upstream matrix exactly unchanged, not a hidden repair.
- `EfficientFrontier.min_volatility` minimizes portfolio variance plus any extra objectives and sum(w)=1. We add no extra objective/constraint and explicitly bound0..1; expected returns do not drive this objective.
- `BaseConvexOptimizer._solve_cvxpy_opt_problem` allows optimal_inaccurate and rounds raw weights16 decimals. Wrapper is stricter: optimal only; raw weights, no clean_weights clipping/normalization; independently checked bounds/sum/KKT/objective and performance. Use explicit CLARABEL with gap/feasibility tolerances1e-10; no elapsed deadline authored.
- `portfolio_performance(...,risk_free_rate=0)` reports model mean, model volatility and Sharpe. Explicit same-unit annual rf0, not a return promise. No max_sharpe/ticker/market return model, price conversion, discrete allocation or broker exposed.

## Dependency candidate evidence

`DEPENDENCIES.json` includes27 freshly read exact release metadata records for target CPython3.12.16 Ubuntu24.04 x86_64, active non-extra dependency constraints, Python requirements, published file URLs and SHA256. Root runtime is PyPortfolioOpt1.6.0, cvxpy1.9.3, CLARABEL0.11.1, numpy2.5.4, pandas3.1.1, scipy1.18.1. Upstream also mandates scikit-base<0.14 and scikit-learn; keep them, do not suppress merely because this objective doesn't call an estimator.

Current newest scikit-base1.2.1 violates PyPortfolioOpt<0.14, so newest compatible nonprerelease0.13.2 was selected from actual release metadata. Current newest sparsediffpy0.8.0 violates cvxpy>=0.6,<0.7, so newest compatible0.6.1 selected. All selected active declared constraints rechecked after resolution. These are not copied pins from a different tool. Build tools separately pinned from current metadata.

This is not a lock/install/runtime result: no wheel availability, compiled ABI/solver compatibility or successful install is asserted. Actual host must install complete pins, pip check, import/run tests and then separately manual analysis. Requirements are exact-version pins, not pip require-hashes; release hashes in provenance are audit evidence, not a claim pip enforced them.

Actions checkout v4 / setup-python v5 / upload-artifact v4 refs freshly read at preparation and pinned to actual observed commits11d5960a326750d5838078e36cf38b85af677262 / a26af69be951a213d495a4c3e4e4022e16d87065 / ea165f8d65b6e75b540449e92b4886f43607fa02. Tests/manual separated, both stdout/stderr loggers joined before returning original command code, logger failures fail otherwise successful step. No authored timeout.

## Deterministic first case

512 invented weekdays from2022-01-03 through2023-12-19, synthetic labels SYN_A/B/C. Let j=i%8; independent signs from bits0/1/2 are -1/1, returns .0004+.005*sign0, .0006+.010*sign1, .0008+.020*sign2. All eight sign combinations repeated64 times, sample cross-covariance zero to numerical tolerance. Minimum-variance analytic weights16/21,4/21,1/21. Tests use independent scalar sample covariance and Gaussian elimination, solver constraints/performance and active-bound case. No random seed/network/calendar data involved.

## Process and unresolved gate

Issue1 precedes branch `feat/issue-1-minimum-variance`. Baseline main protected review1/stale dismissal/last-push approval/admin enforcement, no force/delete. Required analyze App binding awaits actual first host check identity. Persistent command stored/read back in ANALYSIS_COMMAND. No PR or run at initial source checkpoint. New repository eligible independent reviewer Write/token inclusion is a distinct permission gap; prior QuantStats/ta grants do not expand. Source review, actual PR host results, eligible independent formal approval, protected merge and actual manual512 originals/scalar/constraint/result inspection remain separate. No selfapproval or bypass.
