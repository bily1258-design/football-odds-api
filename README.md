# 🏟 北单看板 — Beijing Dan (BD) Dashboard

北京单场让球胜平负 (bjdc) + 胜负过关 (bjdcsf) 数据看板，Excel + HTML 双形态。
**独立仓库**：本仓库 (football-odds-api) 只负责北单看板 —— 生成脚本、说明与部署产物均在此；
足彩价值投注分析系统（另一套）在 football-dashboard 仓库，两者互不混用。

## 📊 页面

GitHub Pages（发布源 **gh-pages** 分支）：
`https://bily1258-design.github.io/football-odds-api/`

- **HTML 看板**：两页数据 (playid=0 让球胜平负 + playid=3 胜负过关) 合并为一表；下拉切换全部期数；含联赛分布
- **Excel**：`beidan_{期号}_dashboard.xlsx`（页面下载链接指向 gh-pages 的 raw 文件）

## 🏗 架构

```
Termux cron (每日 13:25, ~/.hermes/scripts/beidan_cron.sh → wrapper)
  └─ exec scripts/beidan_cron.sh (本仓正式脚本, 单源)
       ├─ gen_500_dashboard.py  抓 trade.500.com (bjdc+bjdcsf) → ~/beidan/beidan_{期}_dashboard.xlsx
       ├─ gen_beidan_html.py    读全部期数 xlsx → ~/beidan/beidan_dashboard.html (全量13期+下拉)
       └─ force-push → gh-pages 分支 (单提交重建: index.html + 最新期 xlsx)
```

- main 分支 = 生成脚本 + 本说明（普通提交，不膨胀）
- gh-pages 分支 = 每日部署产物（force-push 单提交，仓库始终轻量）
- 数据不落库，直接解析页面

## 🚀 本地运行

```bash
cd ~/football-odds-api
python3 scripts/gen_500_dashboard.py          # 生成最新期 xlsx → ~/beidan/
python3 scripts/gen_beidan_html.py            # 生成全量 HTML → ~/beidan/beidan_dashboard.html
bash scripts/beidan_cron.sh                   # 上面两步 + force-push gh-pages（cron 每日执行）
```

依赖：`pip install openpyxl`（其余仅 Python 标准库）

## 🔎 数据源

- `https://trade.500.com/bjdc/`    让球胜平负（默认当前期）
- `https://trade.500.com/bjdcsf/`  胜负过关
- 原 zx.500.com 曾被腾讯云 EdgeOne bot 防护封锁，2026-09 起已迁 trade.500.com
- 无"皇冠历史相同亚盘"概率列（trade 源不提供，该列留空）

## ⏰ 定时任务（Hermes cron）

| Job ID | 时间 | 内容 |
|---|---|---|
| `1e16398ca909` | 每日 13:25 | `beidan_cron.sh`（wrapper）→ 本仓 `scripts/beidan_cron.sh` |

> 产物 xlsx/html 原始文件在 Termux `~/beidan/`（不入任何 git 仓库）。
