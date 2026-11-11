# PyPortfolioOpt: returns-only minimum-variance tool qualification

This is a public, manually triggered tool runner. Its first case uses **512 invented observations of three invented assets**, not EGX/stock data or a user investment mandate. There is no broker, provider, portfolio purchase or investment recommendation.

## Persistent command

Set repository Settings > Secrets and variables > Actions > Variables:

```text
ANALYSIS_COMMAND=python analyze.py --input data/synthetic-returns.csv --metadata data/synthetic-returns.metadata.json --periods-per-year 252 --return-model arithmetic --risk-model sample_cov --objective min_variance --bounds long_only_fully_invested --rf 0 --solver CLARABEL --output results
```

Manually run **Minimum variance returns CSV** on accepted protected main. Variable updates do not execute; dispatch inputs do not replace the persistent variable. PR events only install/test, never analyze the variable. Commands/results are public, including failed-run diagnostics. Use only publishable input with reviewed provenance, never credentials/private portfolios/licensed provider data without rights.

`command_runner.py` permits only the documented `python analyze.py` argv, never shell/eval. Input files must resolve below `data/`; result path is fixed. New public input/metadata or policy changes go through an issue branch and independent review, not arbitrary command execution.

## Explicit v1 qualification contract

- CSV: `Date` then 3-10 unique asset labels matching `[A-Za-z][A-Za-z0-9_]{0,31}`. Dates are strict ISO `YYYY-MM-DD`, unique and increasing. At least252 daily observations. Every return is a finite simple fraction strictly `-1 < r < 1`: .01 means +1%, not the number1, a price or a log return. Bankruptcy/-100%, >=+100% and other policies need a separate recipe.
- No missing/nonfinite/blank records, bad-width rows, duplicate assets/dates or unsorted dates. Gaps remain as supplied; no filling, date/session-calendar completeness claim or price conversion.
- Sidecar nonempty strings: dataset_kind synthetic/market, instruments, source, offset-aware as_of, IANA timezone, return_type exactly simple_fractional, return_basis, frequency exactly daily_observations, publication_rights. Every row date must be on/before as_of in that timezone. Metadata is declared provenance, not independent verification of provider/licensing/adjustments.
- Annualization explicit252 or365 observations/year. Expected-return estimator is **arithmetic daily sample mean * frequency**, not geometric CAGR. Covariance is **sample covariance ddof1 * frequency**, no shrinkage/PSD repair. Singular/nonpositive or eigenvalue ratio <=1e-8 is refused. Upstream covariance must equal explicit sample covariance exactly.
- Objective is **minimize w.T @ annual_covariance @ w**, not maximize returns or Sharpe. Expected returns affect reported estimates, not the objective. Constraints: sum(w)=1 and0<=w<=1, no shorting/leverage. No sector, concentration, turnover, holdings, liquidity or investor-specific constraints are implied. These are tool-test defaults, not user investment preferences.
- Solver explicitly **CLARABEL**, no fallback; requested tolerances abs gap/relative gap/feasibility1e-10, no authored time limit. Accept only status `optimal`, refuse `optimal_inaccurate` even though upstream allows it. Check independent weight-sum/bound feasibility1e-7, KKT residual1e-7 and objective no worse than equal weights+1e-8. Raw weights are not clipped, rounded with clean_weights or renormalized; upstream does round raw solution to16 decimals internally. Numerical tolerance may admit tiny signed residuals, not a short-selling mandate.
- Reported annual mean w.T@mu, volatility sqrt(w.T@S@w), Sharpe=(mean-annual_rf)/volatility with annual rf explicitly fixed0. These are **in-sample model estimates**, not future performance or realized backtest. Expected mean is not a guarantee. Do not compound arithmetic estimates into a promised return.

Socket connect paths are disabled during command execution as defense in depth, not an OS firewall or hostile-code sandbox. No ticker/URL/benchmark or discrete allocation entrypoint exists. Dependency installation needs public downloads; normal module imports/solver initialization occur on the approved host, not during source preparation.

## Outputs

Manual artifact `minimum-variance-results-<run_id>`, retained7 days:

- `weights-and-model.csv`: asset order, raw optimized weight and annual arithmetic estimated return.
- `annual-sample-covariance.csv`: annual covariance in squared fractional-return units.
- `in-sample-returns.csv`: Date and fixed fitted weight dot each supplied return row. This is an in-sample diagnostic, **not** a trading strategy/backtest or executed portfolio.
- `summary.json`, `summary.txt`: declared dataset provenance, input/metadata SHA256, dates/count/order, explicit models/objective/constraints/rf/solver/options/status/iterations, raw weights, independent performance/constraint diagnostics, versions and caveats.
- Source commit/run id, installed versions, stdout/stderr, original command exit code and both joined logger exit codes. Command failure takes priority; when command succeeds either logger failure fails the step. Failed artifacts may be partial, not successful results.

The first fixture is512 invented weekdays2022-01-03 through2023-12-19. Three zero-correlation binary-sign patterns at vol scales.005/.010/.020 around means.0004/.0006/.0008 give analytic inverse-variance weights16/21,4/21,1/21. An independent scalar covariance and Gaussian elimination reference verifies outputs; another case exercises an active long-only bound. No market-data request is hidden in the fixture.

## Acceptance and protection

Source/issue/branch and independent source review first. Actual approved-host install/pip-check/test results must bind exact source. Bind strict required analyze status to the observed GitHub Actions App, review1/stale dismissal/last-push approval/admin enforcement/no force/delete; no author self-approval or bypass. After accepted protected merge, manually run the persistent command and inspect actual originals/scalars/constraints/solver status and all row/input/source joins. A build/source review is not a solver/test/manual result. No authored test/CI/subprocess timeout. No Jules, home execution, new spend/resource or provider/trading effect.

PyPortfolioOpt1.6.0 published wheel/API source and fresh compatible dependency candidates are recorded in `PROVENANCE.md`/`DEPENDENCIES.json`. Source-only state is UNRUN, not qualified. Separate reviewer repository Write/token inclusion must be authorized for this repository, not inferred from another tool's grant.
