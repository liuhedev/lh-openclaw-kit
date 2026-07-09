#!/bin/bash
# 百度图片搜参考图并下载。需 web-access proxy 在 localhost:3456，且 TID 是一个已打开 image.baidu.com 的 tab。
# 用法: baidu-refs.sh <TID> "<关键词>" <输出目录> [张数=4] [portrait]
#   portrait: 只要竖版(h>w*1.15，通常是全身单体图)
# 输出: 下载到 <目录>/ref-N.jpg，并打印路径。下完请务必 Read 逐张核对角色！
set -euo pipefail
P=http://localhost:3456
TID="${1:?need TID}"; KW="${2:?need keyword}"; OUT="${3:?need outdir}"; N="${4:-4}"; MODE="${5:-all}"
mkdir -p "$OUT"

PORTRAIT="false"; [ "$MODE" = "portrait" ] && PORTRAIT="true"

URLS=$(curl -s -X POST "$P/eval?target=$TID" --data-raw "
(async()=>{
  const w=encodeURIComponent('$KW');
  const u='https://image.baidu.com/search/acjson?tn=resultjson_com&word='+w+'&pn=0&rn=30&ie=utf-8';
  const r=await fetch(u,{headers:{Referer:'https://image.baidu.com/'}});
  const t=await r.text();
  let m=[...t.matchAll(/\"thumbURL\":\"(https:[^\"]+?)\"/g)].map(x=>x[1]);
  if($PORTRAIT){m=m.filter(url=>{const w=+(url.match(/[?&]w=(\d+)/)||[])[1];const h=+(url.match(/[?&]h=(\d+)/)||[])[1];return w&&h&&h>w*1.15;});}
  return JSON.stringify([...new Set(m)].slice(0,$N));
})()" | python3 -c "import sys,json;print('\n'.join(json.loads(json.load(sys.stdin)['value'])))")

if [ -z "$URLS" ]; then echo "no refs found for: $KW" >&2; exit 1; fi

i=0
while IFS= read -r url; do
  [ -z "$url" ] && continue
  i=$((i+1))
  f="$OUT/ref-$i.jpg"
  curl -s -o "$f" "$url"
  if file "$f" | grep -qiE "image"; then echo "$f"; else rm -f "$f"; fi
done <<< "$URLS"
echo ">> 下完请 Read 逐张核对：剔除盒子图/场景图/错角色，只留干净单体图" >&2
