# 豆包网页版生图（create-image）

入口 `https://www.doubao.com/chat/create-image`。**特性：任意比例参考图都输出正方全身**，
构图最统一，是首选引擎。需要浏览器已登录豆包（页面出现用户名按钮=已登录）。

## 一次生成的完整步骤（对一个 create-image tab）

```bash
P=http://localhost:3456
TID=$(curl -s -X POST --data-raw 'https://www.doubao.com/chat/create-image' "$P/new" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['targetId'])")
sleep 4
# 1) 传参考图：直接塞 file input，绕过原生文件框
curl -s -X POST "$P/setFiles?target=$TID" \
  -d '{"selector":"input[type=file]","files":["/path/ref.jpg"]}'
sleep 5   # 等参考图上传出 blob 预览
# 2) 写 prompt：编辑器是 tiptap/ProseMirror，execCommand 能直接插字
curl -s -X POST "$P/eval?target=$TID" --data-raw \
 "(()=>{const ed=document.querySelector('div.tiptap.ProseMirror');ed.focus();document.execCommand('insertText',false,'参考这张X，重画成高细节拟真玩具机甲，全身站姿，纯白背景，居中，正方形');return ed.innerText.length})()"
sleep 1
# 3) 点发送
curl -s -X POST "$P/eval?target=$TID" -d \
 '(()=>{const w=document.querySelector("[class*=send-btn-wrapp]");const b=w&&(w.querySelector("button")||w);if(b){b.click();return "SENT"}return "NOBTN"})()'
```

## 抓结果（最大的坑：懒加载）

**后台 tab 的结果 `<img>` src 一直是空的，除非 `/scroll` 触发渲染。** 只 `/screenshot` 不够，
必须先 scroll 再读 src。结果图 URL 特征是 `rc_gen_image`（或显示态 `downsize_watermark`）：

```bash
curl -s "$P/scroll?target=$TID&direction=bottom"
curl -s -X POST "$P/eval?target=$TID" -d \
 '(()=>{let u="";document.querySelectorAll("img").forEach(i=>{const s=i.src||"";if(/rc_gen_image/.test(s)&&!u)u=s;});return u;})()'
```
拿到 URL 直接 `curl -o out.png`。豆包一次出 ~4 张候选，取第一张即可（都同风格）。

轮询封装：`scripts/poll-result.sh <TID> doubao <out.png>`。

## 限流表现（硬约束）

- 短时间触发多张（尤其并行 >3）→ 助手**只发一句"已生成"却不出图**，或**连文字都不回**（页面只剩你发的 prompt）。
- 密集触发约十几张后进入封禁，新请求静默不回，等冷却（通常隔天）恢复。
- 对策：**串行**、一次一个、跑完再下一个；被封就换千问兜底。

## 尺寸

结果多为 384×384 / 500 级别，够小图 / 打印用。要更大在页面点单图看大图另说，一般不需要。
