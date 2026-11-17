"""Forecast GTA VI launch-day Twitch viewers, hours 2..24 (standard library only, deterministic).

Method: for each past launch in `comparables`, take the log ratio of hour h's count to hour 1's count on its release
day (UTC). The median of those ratios, shrunk toward 0 (persistence) by a fixed weight, centres the forecast; the
spread is the larger of the empirical log spread and a floor, mixed with the house random-walk width. Quantiles come
from a normal in log space.
"""
import json, math, os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]
SIGMA = 0.15
SHRINK = 0.7
MIN_P1 = 500


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def median(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def ratios(case):
    """per hour: list of ln(count_h / count_1) from comparables' release days."""
    out = {h: [] for h in range(2, 25)}
    for c in case.get("comparables") or []:
        try:
            d0 = ts(c["day_start"])
            m = {ts(r["from"]): r["viewers"] for r in c["hourly"]}
        except Exception:
            continue
        p = m.get(d0)
        if p is None or p < MIN_P1:
            continue
        for h in out:
            y = m.get(d0 + timedelta(hours=h - 1))
            if y is not None and y > 0:
                out[h].append(math.log(y / p))
    return out


def forecast_case(case):
    p1 = max(1, case["known"][0]["viewers"])
    for k in case["known"]:
        if k["hour"] == 1:
            p1 = max(1, k["viewers"])
    rat = ratios(case)
    rows = []
    for row in case["forecast"]:
        h = row["hour"]
        base_sd = SIGMA * math.sqrt(h - 1)
        v = rat.get(h, [])
        if len(v) >= 3:
            mu = SHRINK * median(v)
            mean = sum(v) / len(v)
            emp = math.sqrt(sum((x - mean) ** 2 for x in v) / (len(v) - 1))
            sd = max(0.5 * base_sd, 0.5 * emp + 0.5 * base_sd)
        else:
            mu, sd = 0.0, base_sd
        q = [p1 * math.exp(mu + z * sd) for z in Z]
        q = [min(max(x, 1e-6), 1e9) for x in q]
        for i in range(1, 5):
            q[i] = max(q[i], q[i - 1])
        rows.append({"hour": h, "q": [round(x, 2) for x in q]})
    return {"hours": rows}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast_case(case), separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
