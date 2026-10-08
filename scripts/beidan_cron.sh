#!/bin/bash
# 北单看板定时抓取推送脚本（football-odds-api 仓库正式版，单源）
# 流程: gen_500_dashboard.py 抓 trade.500.com → xlsx; gen_beidan_html.py → 全量HTML
#       产物 force-push gh-pages 分支（GitHub Pages 发布源 = gh-pages）
# cron 入口: ~/.hermes/scripts/beidan_cron.sh (wrapper → exec 本文件)

set -e
export PATH=/data/data/com.termux/files/usr/bin:$PATH

SRC=/data/data/com.termux/files/home/football-odds-api
PUB=/data/data/com.termux/files/home/football-odds-api-pub

echo "=== 北单看板生成: $(date) ==="
cd "$SRC"

# 生成最新期 xlsx
OUTPUT=$(python3 scripts/gen_500_dashboard.py 2>&1)
echo "$OUTPUT"

# 重新生成 index.html（含所有期数 + 全部赛事 + 下拉选择）
python3 scripts/gen_beidan_html.py 2>&1

# 提取 xlsx 路径与期数
XLSX_PATH=$(echo "$OUTPUT" | grep -oP '/data/.*?\.xlsx' | tail -1)
if [ -z "$XLSX_PATH" ]; then
  echo "❌ 未找到生成的 xlsx 文件"
  exit 1
fi
echo "文件: $XLSX_PATH"
EXPECT=$(basename "$XLSX_PATH" | sed 's/beidan_//;s/_dashboard.xlsx//')
echo "期数: $EXPECT"

# 发布产物 → gh-pages 分支（force-push 单提交, 保持仓库轻量）
rm -rf "$PUB"
mkdir -p "$PUB"
cd "$PUB"
git init
git checkout -b gh-pages
cp "$XLSX_PATH" "beidan_${EXPECT}_dashboard.xlsx"
cp ~/beidan/beidan_dashboard.html index.html
git add -A
git commit -m "update: 北单${EXPECT}期看板 $(date +%Y-%m-%d) (index.html+xlsx)"
git remote add origin git@github.com:bily1258-design/football-odds-api.git

# 推送加护（2026-10-08）：手机网络/ssh 抖动会让单次 push 以 rc=128 中断
# （足彩链路 10-07、10-08 连续两次同因 "Connection to ssh.github.com closed by remote host"）。
# gh-pages 是 force-push 单提交，重试无增量风险；三次全败才判失败。
PUSH_OK=0
for i in 1 2 3; do
  if git push origin +gh-pages 2>&1; then
    PUSH_OK=1
    break
  fi
  if [ "$i" -lt 3 ]; then
    echo "⚠️ 推送失败(第 $i 次), 20s 后重试..."
    sleep 20
  else
    echo "❌ 推送三次均失败(ssh.github.com 抖动/网络)；产物已生成于 $PUB, 下次运行会重新生成并推送, 不需单独补推"
  fi
done
[ "$PUSH_OK" -eq 1 ] || exit 1
echo "✅ 已推送 football-odds-api gh-pages: beidan_${EXPECT}_dashboard.xlsx"
