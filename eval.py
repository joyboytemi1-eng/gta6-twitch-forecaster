#!/usr/bin/env python3
"""Leave-one-launch-out pinball evaluation on practice comparable series."""
import json
import math
from pathlib import Path

from main import forecast

KIT = Path(__file__).resolve().parent.parent / 'gta6-twitch-ccu-forecast-01-kit'
LEVELS = (0.05, 0.25, 0.50, 0.75, 0.95)


def hour_map(comp):
    result = {}
    day = comp['day_start'][:10]
    from datetime import date
    d0 = date.fromisoformat(day)
    for row in comp.get('hourly') or []:
        dd = date.fromisoformat(row['from'][:10])
        h = (dd - d0).days * 24 + int(row['from'][11:13])
        result[h] = max(1.0, float(row['viewers']))
    return result


def evaluate(case):
    launches = case.get('comparables') or []
    totals = [0.0] * 23
    counts = [0] * 23
    cover = [0] * 23
    detail = []
    residuals = [[[] for _ in LEVELS] for _ in range(23)]
    for held in launches:
        actual = hour_map(held)
        if 0 not in actual or actual[0] <= 0:
            continue
        others = [c for c in launches if c is not held]
        pseudo = {
            'day_start': held['day_start'],
            'known': [{'viewers': actual[0]}],
            'comparables': others,
        }
        pred = forecast(pseudo)['hours']
        launch_loss = 0.0
        launch_n = 0
        for row in pred:
            y = actual.get(row['hour'] - 1)
            if y is None:
                continue
            ly = math.log(max(1.0, y))
            i = row['hour'] - 2
            local = 0.0
            for j, (tau, q) in enumerate(zip(LEVELS, row['q'])):
                d = ly - math.log(q)
                loss = 2.0 * max(tau * d, (tau - 1.0) * d)
                residuals[i][j].append(d)
                totals[i] += loss
                local += loss
                launch_loss += loss
                counts[i] += 1
                launch_n += 1
            if row['q'][0] <= y <= row['q'][4]:
                cover[i] += 1
            detail.append((i + 2, held['name'], local / 5.0,
                           ly - math.log(row['q'][2])))
        if launch_n:
            detail.append(('launch', held['name'], launch_loss / launch_n, 0.0))
    n = sum(counts)
    return (sum(totals) / n if n else float('nan'), n,
            [totals[i] / counts[i] if counts[i] else float('nan') for i in range(23)],
            [cover[i] / (counts[i] // 5) if counts[i] else float('nan') for i in range(23)], detail, residuals)


def main():
    for path in sorted((KIT / 'input').glob('p0[0-3].in')):
        case = json.loads(path.read_text(encoding='utf-8'))
        loss, count, by_hour, coverage, detail, residuals = evaluate(case)
        print(f"{case['id']}: mean_pinball_log={loss:.6f} scored_items={count}")
        if path.name == 'p00.in':
            print('  hour loss: ' + ' '.join(f'{h}:{v:.3f}' for h, v in enumerate(by_hour, 2)))
            print('  90% band:  ' + ' '.join(f'{h}:{v:.2f}' for h, v in enumerate(coverage, 2)))
            for j, tau in enumerate(LEVELS):
                offsets = []
                for i in range(23):
                    vals = sorted(residuals[i][j])
                    k = min(len(vals)-1, max(0, int(math.ceil(tau * len(vals)) - 1)))
                    offsets.append(vals[k] if vals else 0.0)
                print(f'  tau {tau:.2f} residual quantile: ' + ' '.join(f'{x:+.2f}' for x in offsets))
            launch_rows = [x for x in detail if x[0] == 'launch']
            launch_rows.sort(key=lambda x: -x[2])
            print('  worst launches: ' + '; '.join(f'{x[1]}={x[2]:.3f}' for x in launch_rows[:12]))


if __name__ == '__main__':
    main()
