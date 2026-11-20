#!/bin/sh
# 刷新火山方舟 ARK 消费台账并重新部署。
set -e
cd /workspace
export PATH="/usr/local/bin:$PATH"

if [ -f /workspace/.secrets/volc.env ]; then
  . /workspace/.secrets/volc.env
elif [ -f /root/.ve-env ]; then
  . /root/.ve-env
else
  echo "ERROR: 未找到火山引擎凭证配置" >&2
  exit 1
fi

python3 scripts/fetch_bills.py
python3 scripts/build_site.py

SITE_ID="37ktvtbrjtzkgcayg9a"
DEPLOY="/data/user/plugins/trae-remote-official/deployment/0.0.43/skills/deployment/scripts/trae-deploy"

ACTIVE="$(sh "$DEPLOY" deployments list --site-id "$SITE_ID" 2>/dev/null | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin); items=d.get("data",{}).get("items",[])
    print(1 if items and items[0].get("status") in range(1,9) else 0)
except Exception:
    print(0)')"
if [ "$ACTIVE" = "1" ]; then
  echo "已有进行中的部署，本次跳过创建。" >&2
  exit 0
fi

SRC="$(mktemp -d "${TMPDIR:-/tmp}/trae-deploy.XXXXXX")"
mkdir -p "$SRC/public"
cp public/index.html "$SRC/public/"
printf '{}' > "$SRC/exec.json"

OUT="$(sh "$DEPLOY" deployments create \
  --site-id "$SITE_ID" \
  --title "方舟项目账单台账（自动更新）" \
  --description "来源 /workspace，静态发布 public/index.html；火山方舟 ARK 按项目、按天消费账单台账，包含趋势图、项目汇总、明细台账与矩阵，供财务记录与核对。" \
  --type static-web \
  --source-dir "$SRC" \
  --execution-config "$SRC/exec.json" \
  --app-tags 123,234 2>&1)"

DEP_ID="$(printf '%s' "$OUT" | sed -n 's/.*"deployment_id":"\([^"]*\)".*/\1/p' | tail -1)"
if [ -z "$DEP_ID" ]; then
  echo "$OUT" >&2
  rm -rf "$SRC"
  echo "ERROR: 创建部署失败" >&2
  exit 1
fi

sh "$DEPLOY" deployments wait --deployment-id "$DEP_ID" | tail -1
rm -rf "$SRC"
