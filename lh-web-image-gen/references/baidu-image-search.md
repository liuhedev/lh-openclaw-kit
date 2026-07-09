# 百度图片搜参考图

用百度图片的 `acjson` 接口拿参考图 URL。**必须在一个已打开 image.baidu.com 的 tab 里 `fetch`**（带 cookie / Referer），纯 curl 外部调常被拦。

## 拿一个 baidu tab

```bash
BTID=$(curl -s -X POST --data-raw 'https://image.baidu.com/' http://localhost:3456/new \
  | python3 -c "import sys,json;print(json.load(sys.stdin).get('targetId',''))")
```

## 接口 + 解析（坑：控制字符）

acjson 返回里常有未转义控制字符，`JSON.parse` 会直接抛
`Bad control character in string literal`。**不要 JSON.parse 整包，用正则抽 `thumbURL`**：

```js
// 在 baidu tab 里 /eval 执行
(async()=>{
  const w = encodeURIComponent("炫卡斗士 喷射加仑 玩具");
  const u = "https://image.baidu.com/search/acjson?tn=resultjson_com&word="+w+"&pn=0&rn=30&ie=utf-8";
  const r = await fetch(u,{headers:{Referer:"https://image.baidu.com/"}});
  const t = await r.text();
  const m = [...t.matchAll(/"thumbURL":"(https:[^"]+?)"/g)].map(x=>x[1]);
  return JSON.stringify([...new Set(m)].slice(0,8));
})()
```

## 筛竖版（全身单体图）

`thumbURL` 自带 `?w=&h=` 尺寸参数，用它筛竖版——竖版通常是站姿全身单体图，
横版多是场景截图 / VS 拼图 / 盒子图。想要全身就筛 `h > w*1.15`：

```js
const tall = m.filter(url=>{
  const w=+(url.match(/[?&]w=(\d+)/)||[])[1];
  const h=+(url.match(/[?&]h=(\d+)/)||[])[1];
  return w && h && h > w*1.15;
});
```

## 关键词技巧

- 加 `玩具` / `手办` → 偏实拍产品图（干净白底概率高）。
- 加 `免抠` → 多为动画截图（16:9），慎用。
- 单个角色名可能被百度带偏成别的角色（如「暗影特工 手办」返回蓝色警车机器人）——**下完必须 Read 逐张核对角色对不对**。

## 下载 + 人工核对（必做）

```bash
curl -s -o /tmp/ref1.jpg '<thumbURL>'
```
然后 **Read 每张图**：剔除盒子图、零件图、多物摆拍、场景截图、错角色，只留清晰单体图。
参考图只要能看清角色形态即可，不用完美白底——AI 会重画，但角色必须对。

`scripts/baidu-refs.sh <TID> "<关键词>" <outdir> [n] [portrait]` 封装了以上取 URL + 下载。
