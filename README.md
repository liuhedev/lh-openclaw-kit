# liuhedev-skills

Agent Skills 集合，每个技能一个独立目录。

## skills

| Skill | 说明 |
|-------|------|
| [gaokao-zhiyuan](gaokao-zhiyuan/) | 高考志愿填报顾问，基于教育部阳光高考权威数据做冲稳保院校专业组推荐，叠加就业方向分析，输出文本或 HTML 志愿报告 |
| [lh-web-image-gen](lh-web-image-gen/) | 无 API key 时的网页版批量生图：搜参考图 → 驱动已登录的豆包/即梦/千问「图生图」重画 → 落本地图库，批量生成风格统一的套图 |

## 安装

通过 [skills CLI](https://skills.sh) 一键安装到任意 AI Agent：

```bash
# 安装全部 skills
npx skills add liuhedev/liuhedev-skills

# 安装指定 skill
npx skills add liuhedev/liuhedev-skills --skill gaokao-zhiyuan
```

## 贡献

欢迎 PR，敏感信息（密钥、token）请通过环境变量传入，不要硬编码。
