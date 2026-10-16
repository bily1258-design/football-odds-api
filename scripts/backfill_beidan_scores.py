#!/usr/bin/env python3
"""回填北单看板历史期「比分 / 赛果」（源: trade.500.com 让球页 + 过页）

背景（2026-10-16）: `gen_500_dashboard.py` 只抓**当期**、且当期只在开奖日 13:25 抓一次，
  之后完赛的场次比分永远进不了 xlsx → 看板比分列长期显示 '-'，用户报「看板上没有新的比分」。
  实测: 期26104 源页 109/109 有比分，本地 xlsx 仅 74/144 → 35 场可回填；26101 可回填 55 场。

口径:
  - 配对键 = (主队, 客队)（两玩法编号体系不同，不能按编号，见 skill beidan-dashboard）
  - 比分: 仅填空，**不覆盖**已有值
  - 赛果: 让球胜平负口径（主队净胜 + 让球 > 0 → 胜 / = 0 → 平 / < 0 → 负），实测历史 869 行 0 错
  - 让球为 0 且比分为 0:0 的 '＊' 特例（腰斩/取消）不判，留空

用法:
  python3 scripts/backfill_beidan_scores.py                 # 最近 12 期 + 当期
  python3 scripts/backfill_beidan_scores.py --periods 30
  python3 scripts/backfill_beidan_scores.py --dry-run
"""

import os
import re
import sys
import glob
import argparse

import openpyxl

BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))

from gen_500_dashboard import fetch_page, parse_matches, detect_current_expect  # noqa: E402

BEIDAN_DIR = os.path.expanduser('~/beidan')
SCORE_RE = re.compile(r'^(\d+):(\d+)$')


def hdcp_int(v):
    """让球 → int（'+1'/1 → 1, '-2' → -2）；非整数让球（球半等）返回 None"""
    if v is None or v == '':
        return None
    if isinstance(v, (int, float)):
        return int(v)
    m = re.match(r'^([+-]?)(\d+)$', str(v).strip())
    if not m:
        return None
    n = int(m.group(2))
    return -n if m.group(1) == '-' else n


def judge_result(score, hd):
    """让球胜平负赛果；无法判定返回 ''"""
    m = SCORE_RE.match(str(score or '').strip())
    h = hdcp_int(hd)
    if not m or h is None:
        return ''
    diff = (int(m.group(1)) + h) - int(m.group(2))
    return '胜' if diff > 0 else ('平' if diff == 0 else '负')


def list_periods(n):
    nums = []
    for p in glob.glob(os.path.join(BEIDAN_DIR, 'beidan_*_dashboard.xlsx')):
        m = re.search(r'beidan_(\d+)_dashboard\.xlsx$', os.path.basename(p))
        if m:
            nums.append(m.group(1))
    nums = sorted(set(nums), reverse=True)
    return nums[:n]


def fetch_scores(expect):
    """两玩法页 → {(主队,客队): 比分}（让球页优先，过页兜底）"""
    table = {}
    for playid in (0, 3):          # 过页先入，让球页覆盖（让球页比分更全）
        try:
            parsed = parse_matches(fetch_page(playid, expect), playid)
        except Exception as e:      # noqa: BLE001
            print(f'    ⚠️ 期{expect} playid={playid} 抓取失败: {e}')
            continue
        for v in parsed.values():
            sc = str(v.get('score') or '').strip()
            if not sc:
                continue
            key = (str(v.get('home') or '').strip(), str(v.get('away') or '').strip())
            if key and key != ('', ''):
                table[key] = sc
    return table


def backfill_one(expect, dry=False):
    path = os.path.join(BEIDAN_DIR, f'beidan_{expect}_dashboard.xlsx')
    if not os.path.exists(path):
        return (0, 0, 0)
    table = fetch_scores(expect)
    if not table:
        print(f'  期{expect}: 源页无比分（未开赛期正常）')
        return (0, 0, 0)

    wb = openpyxl.load_workbook(path)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    hdr_i = next((i for i, r in enumerate(rows) if r and any(
        isinstance(c, str) and '比分' in str(c) for c in r)), None)
    if hdr_i is None:
        print(f'  期{expect}: 找不到表头，跳过')
        return (0, 0, 0)
    hdr = [str(c).strip() if c else '' for c in rows[hdr_i]]
    c_score = next((i for i, h in enumerate(hdr) if h.startswith('比分')), 6)
    c_res = next((i for i, h in enumerate(hdr) if h.startswith('赛果')), 7)
    c_hd = next((i for i, h in enumerate(hdr) if h.startswith('让球')), 4)

    filled_s = filled_r = unmatched = 0
    for ri in range(hdr_i + 2, len(rows) + 1):      # 1-based 工作表行号（表头下一行起）
        r = rows[ri - 1]
        if not r or r[0] is None:
            continue
        home = str(r[3] or '').strip() if len(r) > 3 else ''
        away = str(r[5] or '').strip() if len(r) > 5 else ''
        sc = str(r[c_score] or '').strip() if len(r) > c_score else ''
        res = str(r[c_res] or '').strip() if len(r) > c_res else ''
        if sc and res:
            continue
        src = table.get((home, away))
        if not src:
            unmatched += 1
            continue
        if not sc:
            ws.cell(row=ri, column=c_score + 1).value = src
            sc = src
            filled_s += 1
        if not res and sc:
            jr = judge_result(sc, r[c_hd] if len(r) > c_hd else None)
            if jr:
                ws.cell(row=ri, column=c_res + 1).value = jr
                filled_r += 1
    if (filled_s or filled_r) and not dry:
        wb.save(path)
    print(f'  期{expect}: 源比分 {len(table)} 场 → 补比分 {filled_s} / 补赛果 {filled_r}'
          f' / 未匹配 {unmatched}' + ('（dry-run 未写盘）' if dry else ''))
    return (filled_s, filled_r, unmatched)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--periods', type=int, default=12, help='回填最近 N 期（默认 12）')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    periods = list_periods(args.periods)
    try:
        cur = str(detect_current_expect())
        if cur not in periods:
            periods.insert(0, cur)
    except Exception:      # noqa: BLE001
        pass
    print(f'回填期数: {", ".join(periods)}')

    tot_s = tot_r = 0
    for exp in periods:
        s, r, _ = backfill_one(exp, dry=args.dry_run)
        tot_s += s
        tot_r += r
    print(f'合计: 补比分 {tot_s} 场 / 补赛果 {tot_r} 场')
    return 0


if __name__ == '__main__':
    sys.exit(main())
