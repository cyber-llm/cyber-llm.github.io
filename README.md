# Large Language Models for Cybersecurity — project page

Source of https://cyber-llm.github.io/, the project page for the survey *Large Language Models for Cybersecurity:
A Survey of Data, Training, Models, Agent Systems, Evaluation, and Applications*.

每次推送到 `main`，GitHub Actions（`.github/workflows/pages.yml`）都会重新构建并发布，约 1–2 分钟后线上更新。
仓库里不提交 `index.html`，它由构建生成；请改源码，不要手改生成的页面。

## 改什么文件

| 想改的内容 | 文件 |
| --- | --- |
| 标题、作者与单位、摘要、各章节文字、要点、统计数字、未来方向、BibTeX | `src/content.json` |
| 版式、颜色、字号 | `assets/style.css` |
| 交互（图签切换、放大查看器、复制 BibTeX 等） | `assets/site.js` |
| 页面结构 | `src/build.py` |
| 机构标识 | `assets/img/logos/`，并在 `content.json` 的 `hero.logos` 中登记 |

页面上的每句话都应能在论文正文中找到出处；改动时请对照最新版论文。

## 最简单的协作方式

1. 在 GitHub 网页上打开 `src/content.json`，点铅笔图标直接编辑，提交到 `main`（或开 Pull Request 请人审阅）。
2. 在仓库的 **Actions** 页看到 “Build and deploy site” 变绿后，刷新 https://cyber-llm.github.io/ 即可。
3. 构建失败时页面保持上一版不变；在 Actions 日志里看报错（多为 JSON 少了逗号或引号）。

## 本地预览

```sh
pip install pillow
python3 src/build.py --skip-assets
python3 -m http.server 8000      # 打开 http://localhost:8000
```

`--public` 会额外把可发布的文件导出到 `public/`（与线上一致，只含页面实际引用的文件）。

## 配图

- 正文先显示内嵌的轻量预览，只加载距离视口 900px 内的当前图签，使用 800 / 1200px WebP；隐藏图签在悬停、键盘聚焦或切换时加载。
- 放大查看器立即复用正文已加载的图片，待 2400px WebP 解码后替换，保留当前缩放；只有点击 `Load vector` 或 `Save SVG` 才下载 SVG 原图。
- 禁用 JavaScript 时，所有配图仍可通过原生懒加载查看。机构标识在构建时从 PNG 生成高度不超过 104px 的 WebP，保留透明背景。
- 图号与图注以论文为准，登记在 `content.json` 的 `figures` 中；`src/figure_manifest.json` 记录尺寸与来源。
- 更新配图需要论文的单页图 PDF（不在本仓库）：维护者在本机放好 `source_pdf` 所指的文件后，运行
  `python3 src/build.py`（需 PyMuPDF、requests、Pillow），会重新导出 SVG 与 WebP，再提交 `assets/fig/` 和
  `src/figure_manifest.json`。

## 字体

参考 https://www.miaofs18.top/ 的排版，标题和正文使用 `Trebuchet MS, Helvetica, Arial, sans-serif`，BibTeX 使用本机等宽字体。无需下载网络字体；仓库内保留的旧字体不再导出到 `public/`。
