#!/bin/bash
# 轮询一个已发出生成请求的引擎 tab，抓结果图下载。需 web-access proxy 在 localhost:3456。
# 用法: poll-result.sh <TID> <doubao|qianwen> <输出png路径> [最多轮数=12]
# 关键: 后台 tab 图片懒加载，必须 /scroll 才渲染出 src——本脚本每轮先 scroll 再抓。
set -euo pipefail
P=http://localhost:3456
TID="${1:?need TID}"; ENGINE="${2:?doubao|qianwen}"; OUT="${3:?need out.png}"; MAX="${4:-12}"

if [ "$ENGINE" = "doubao" ]; then
  EXTRACT='(()=>{let u="";document.querySelectorAll("img").forEach(i=>{const s=i.src||i.currentSrc||"";if(/rc_gen_image/.test(s)&&!u)u=s;});return u;})()'
elif [ "$ENGINE" = "qianwen" ]; then
  # 结果=同宽出现≥3次的一组；排除被 re-host 的参考图(单张、异宽)
  EXTRACT='(()=>{const m={};document.querySelectorAll("img").forEach(i=>{const s=i.src||i.currentSrc||"";const r=i.getBoundingClientRect();if(/workspace-zb-cdn/.test(s)&&r.left>250&&r.width>100){const w=Math.round(r.width);(m[w]=m[w]||[]).push(s);}});for(const w of Object.keys(m)){if(m[w].length>=3)return m[w][0];}return "";})()'
else
  echo "engine must be doubao|qianwen" >&2; exit 2
fi

r=0
while [ "$r" -lt "$MAX" ]; do
  r=$((r+1))
  sleep 12
  curl -s "$P/scroll?target=$TID&direction=bottom" >/dev/null 2>&1
  URL=$(curl -s -X POST "$P/eval?target=$TID" -d "$EXTRACT" \
    | python3 -c "import sys,json;print(json.load(sys.stdin).get('value',''))" 2>/dev/null || true)
  if [ -n "$URL" ]; then
    curl -s -o "$OUT" "$URL"
    if file "$OUT" | grep -qiE "image"; then
      echo "OK $OUT ($(file -b "$OUT" | grep -oE '[0-9]+ x [0-9]+' | head -1)) round$r"
      exit 0
    else
      rm -f "$OUT"
    fi
  fi
  echo "[round $r] waiting..." >&2
done
echo "FAIL: no result after $MAX rounds (可能限流/被封，换引擎或等冷却)" >&2
exit 1
