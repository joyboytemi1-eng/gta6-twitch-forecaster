# gta6-twitch-forecaster
Deterministic stdlib-only forecaster for GTA VI launch-day Twitch viewers (make.fun bounty)

## Method and practice backtest

The forecast aligns each comparable launch to hour 1, then applies the empirical distribution of its hourly log-viewer ratios to the case's observed hour-1 count. Five quantiles are produced per hour. When comparable data are sparse or malformed, the forecast falls back to a widening persistence prior. The leave-one-comparable-launch-out backtest (p00–p03) scored **0.709670** mean pinball loss on the log scale, versus **0.714936** before the tail calibration; outer 5%–95% band coverage rose from about 84% to about 88%. The evaluator reports the same result for each practice case because their comparable-launch sets are identical.