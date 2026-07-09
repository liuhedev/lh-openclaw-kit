---
name: lh-web-image-gen
description: >
  无 API key 时的网页版批量生图：搜参考图 → 驱动已登录的豆包/即梦/千问「图生图」重画 →
  落本地图库，批量生成风格统一的套图。当用户要「批量生成一套图 / 参考图重绘 / 照着这些图重画 /
  给这些角色画套图 / 做套贴纸打卡卡」，且没有图模型 API key，或指定用豆包/即梦/千问网页版时用。
  有 key 或单张图走 lh-image-gen；构造创意 prompt 走 lh-inline-diagram / lh-cover-image。
---

# lh-web-image-gen：网页版 AI 批量生图（参考图重绘）

**一句话**：没有图模型 API key 时，用浏览器自动化开着你已登录的豆包 / 千问，
把「一批主题 + 一个目标风格」批量生成风格统一的图，落到本地图库。

## 什么时候用本 skill vs lh-image-gen

| 场景 | 用谁 |
|---|---|
| 有 DASHSCOPE_API_KEY / ARK_API_KEY 等图模型 key | **lh-image-gen**（API，稳、可并发） |
| 没有任何图模型 key，但浏览器登录了豆包 / 千问 | **本 skill**（网页版兜底） |
| 要参考真实图片重绘成统一风格（角色套图、玩具化、白底化） | **本 skill**（参考图重绘是强项） |
| HTML/海报截图成 PNG | lh-image-gen 的 `provider: html` |

先确认有没有 key（`printenv DASHSCOPE_API_KEY ARK_API_KEY`）。有就走 lh-image-gen，别绕这条更慢的网页路。

## 前置：起 web-access CDP

全程依赖 [web-access](../web-access/SKILL.md) 的 CDP proxy（连你日常已登录的 Chrome，免 API key）。

```bash
node "$(find -L ~/.claude/skills ~/.agents/skills -maxdepth 3 -name check-deps.mjs -path '*web-access*' 2>/dev/null | head -1)" --browser chrome
```

`exit 0` → proxy 就绪，API 在 `http://localhost:3456`。所有页面操作走 `curl` 调 proxy（`/new` `/eval` `/setFiles` `/scroll` `/screenshot` `/close`）。**必须向用户展示 web-access 的账号封禁风险提示再动手。**

## 总流程（串行，别并行）

```
1. 定主题清单 + 目标风格 prompt 模板
2. 每个主题：百度搜参考图 → 挑干净单体图（scripts/baidu-refs.sh）
3. 每个主题：开引擎 tab → 传参考图 + 发 prompt → 轮询下载（scripts/poll-result.sh）
4. 落地本地图库；需要轮换/打印再包一层 HTML
```

> 🔴 **串行，一次一个。** 短时间并行触发多张（>3）会触发平台限流：豆包约十几张就封、后续请求静默不回；千问也会。并行省的时间会被重试全吃掉，还烧额度。一个主题跑完再下一个。

## 选引擎（关键差异，直接决定构图）

| 引擎 | 输出特性 | 何时选 |
|---|---|---|
| **豆包** create-image | **任意比例参考图都输出正方全身**；构图最统一 | 想要一整套正方全身、风格齐 |
| **千问** AI生图 | **输出跟随参考图比例**（竖版参考→竖版全身；16:9 参考→半身近景） | 豆包限流兜底；想要竖版全身就喂**竖版全身**参考图 |

**推论**：想要全身，喂全身参考图（尤其千问）。找不到干净全身参考图的主题，用豆包（它不挑）。

平台操作细节（选择器、注入文字的坑、结果 URL、限流表现）分别看：
- 百度搜参考图 → `references/baidu-image-search.md`
- 豆包网页版 → `references/doubao-web.md`
- 千问网页版 → `references/qianwen-web.md`

**第一次碰某平台，先读对应 reference**——里面每条都是踩过的坑，不读会重趟（比如千问的编辑器程序插字前端不认，必须合成 paste）。

## 脚本

两个脚本都打到 `http://localhost:3456`（web-access proxy 必须先起）。

### 1. 搜参考图并下载

```bash
scripts/baidu-refs.sh <TID> "<关键词>" <输出目录> [张数=4] [portrait]
# TID = 一个已打开 image.baidu.com 的 tab id（curl -X POST --data-raw 'https://image.baidu.com/' http://localhost:3456/new 拿到）
# portrait = 只要竖版（h>w，通常是全身单体图）
```
打印下载好的候选路径。**下完务必用 Read 逐张看**——百度会混进盒子图 / 场景截图 / 错角色，挑干净单体图再喂 AI。

### 2. 轮询下载生成结果

```bash
scripts/poll-result.sh <TID> <doubao|qianwen> <输出png路径>
# TID = 已发出生成请求的引擎 tab id
```
自动 `/scroll` 触发后台 tab 懒加载（**不 scroll 图 URL 永远是空的**，这是最大的坑），抓结果图 URL 下载。豆包认 `rc_gen_image`，千问认 `workspace-zb-cdn` 且排除参考图那张。

引擎 tab 的「传参考图 + 发 prompt」这步选择器易变、和平台强相关，不做成死脚本——照对应 reference 里的 eval 片段现拼，跑通后把新选择器回写 reference。

## Prompt 模板（参考图重绘）

```
参考图中【主题】的形象和结构，重绘成【目标风格：如高细节拟真玩具机甲】，
全身站姿，纯白背景，居中，正方形构图，【配色/材质关键词】，保留识别特征
```
风格词决定成品调性，配色词帮 AI 锁定，"保留识别特征"防它自由发挥跑偏。

## 落地图库 + 打印（可选）

生成的 PNG 放一个图库目录，HTML 里用 `object-fit:contain` 引用（兼容不同比例）。两种常见包装：
- 按日期自动轮换：`heroes` 数组 + `new Date()` 取当天 index。
- 批量打印：`<template>` 克隆 N 份，每份换一张图，`.sheet{break-after:page}` 各占一页。

## 边界

- ❌ 不构造创意 prompt（那是 lh-cover-image / lh-inline-diagram）；本 skill 只做「参考图重绘」这类明确 prompt。
- ❌ 不做 HTML 截图（走 lh-image-gen `provider: html`）。
- ❌ 有 API key 别用本 skill，走 lh-image-gen 更快更稳。
- ⚠️ 平台限流是硬约束：串行、一天几十张封顶；被封只能等冷却或换引擎。
