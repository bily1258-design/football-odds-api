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
git push origin +gh-pages 2>&1
echo "✅ 已推送 football-odds-api gh-pages: beidan_${EXPECT}_dashboard.xlsx"
