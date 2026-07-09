# 千问网页版生图（AI生图）

`https://www.qianwen.com/`（通义会跳到这）。进 AI生图模式后有**参考图**上传 + **比例**选择。
**特性：输出跟随参考图比例**——竖版全身参考→竖版全身图；16:9 参考→半身近景。
所以想要全身就喂**竖版全身**参考图。豆包限流时用它兜底。需已登录（无「登录」按钮）。

## 进 AI生图模式

```bash
P=http://localhost:3456
# 更多 → AI生图
curl -s -X POST "$P/eval?target=$TID" -d '(()=>{const m=[...document.querySelectorAll("*")].find(e=>e.children.length===0&&/^更多$/.test((e.innerText||"").trim()));if(m)m.click();return 1})()'
sleep 1
curl -s -X POST "$P/eval?target=$TID" -d '(()=>{const b=[...document.querySelectorAll("*")].find(e=>e.children.length===0&&/^AI生图$/.test((e.innerText||"").trim()));if(b)b.click();return 1})()'
```

## 🔴 坑 1：编辑器是 Slate，程序插字前端不认

输入框有 `data-slate-editor` 属性。`execCommand('insertText')` 能让 DOM 显示文字，
但 **Slate 的内部模型不同步 → 发送按钮一直 disabled**（React 只认 isTrusted 事件）。
**解法：合成一个 `paste` 事件注入文字**（React 在 root 监听，不校验 isTrusted）：

```js
(()=>{
  const ed=document.querySelector('[contenteditable=true]');
  ed.focus();
  const dt=new DataTransfer();
  dt.setData('text/plain','参考图中X的形象，重绘成…全身站姿纯白背景居中');
  const ev=new ClipboardEvent('paste',{bubbles:true,cancelable:true});
  Object.defineProperty(ev,'clipboardData',{value:dt});
  ed.dispatchEvent(ev);
  return ed.innerText.length;   // >0 且发送按钮随即 enabled
})()
```

## 🔴 坑 2：顺序必须「先 paste 文字，再传参考图」

如果先传参考图、再往输入框注入文字（尤其中途 `selectAll+delete` 清空），**会把参考图一起清掉**，
结果变成纯文字生成（画出通用形象，不是你的角色）。正确顺序：

```
① paste 文字 → ② 点「参考图」→ setFiles → ③ 确认缩略图在、发送 enabled → ④ 发送
```

```bash
# ② 传参考图
curl -s -X POST "$P/eval?target=$TID" -d '(()=>{const b=[...document.querySelectorAll("*")].find(e=>e.children.length===0&&/^参考图$/.test((e.innerText||"").trim()));if(b)b.click();return 1})()'; sleep 2
curl -s -X POST "$P/setFiles?target=$TID" -d '{"selector":"input[type=file]","files":["/path/ref.jpg"]}'; sleep 5
# ④ 发送（按钮 aria-label=发送消息）
curl -s -X POST "$P/eval?target=$TID" -d '(()=>{const s=[...document.querySelectorAll("button")].find(b=>/发送消息/.test(b.getAttribute("aria-label")||"")&&!b.disabled);if(s){s.click();return "SENT"}return "disabled"})()'
```
> 发送若返回 disabled，多半是参考图还没上传完（时序）——sleep 久点重点一次即可。

## 抓结果

同样**要 `/scroll` 触发懒加载**。结果图在 `workspace-zb-cdn.qianwen.com`，一次 ~4 张。
**坑：上传的参考图也被 re-host 到同域**——它是第一张、和参考图同比例；结果是后面 4 张同宽的一组。
按「同宽出现 ≥3 次」挑结果组，排除参考图：

```bash
curl -s "$P/scroll?target=$TID&direction=bottom"
curl -s -X POST "$P/eval?target=$TID" -d '(()=>{const m={};document.querySelectorAll("img").forEach(i=>{const s=i.src||"";const r=i.getBoundingClientRect();if(/workspace-zb-cdn/.test(s)&&r.left>250&&r.width>100){const w=Math.round(r.width);(m[w]=m[w]||[]).push(s);}});for(const w of Object.keys(m)){if(m[w].length>=3)return m[w][0];}return "";})()'
```

轮询封装：`scripts/poll-result.sh <TID> qianwen <out.png>`。结果多为 3:4 / 768×1024 级别。

## 限流

千问也会限流（连发几张后不回复、页面只剩 prompt）。同样串行、被封等冷却。
