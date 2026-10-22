"""从内容配置生成综述网站；全部配图使用 PDF 原稿导出的 SVG。

日常改动无需本地构建：推送到 main 后由 GitHub Actions 运行 `python src/build.py --skip-assets --public` 并发布。
"""
from __future__ import annotations

import argparse
import html
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C = json.loads((ROOT / 'src' / 'content.json').read_text())
# 与论文配图同一套色相；每章只用一种色相做小面积点缀（编号、数字、图号）。
HUES = {'blue': '#1c62c4', 'teal': '#0a7c88', 'orange': '#b74c12', 'green': '#2a7a37', 'purple': '#7436c2',
        'rasp': '#a33f6c', 'slate': '#3c4e66', 'rust': '#b93a26', 'navy': '#1f3a8a'}
SOFT = {'blue': '#e9f1fd', 'teal': '#e0f3f5', 'orange': '#fdeedf', 'green': '#e2f3e5', 'purple': '#f1e9fc', 'rasp': '#f8e3ec',
        'slate': '#e9eef5', 'rust': '#fbe5df', 'navy': '#e8eefc'}
e = html.escape

# 同一套线性图标只用于页面导航，不改变论文配图。
ICONS = {
    'data': '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
    'training': '<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3"/><circle cx="15" cy="17" r="3"/>',
    'models': '<rect x="6" y="6" width="12" height="12" rx="3"/><path d="M9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m-4 6h4m12-6h4m-4 6h4"/>',
    'agents': '<circle cx="12" cy="5" r="3"/><circle cx="5" cy="18" r="3"/><circle cx="19" cy="18" r="3"/><path d="m10.5 8-4 7m7-7 4 7M8 18h8"/>',
    'evaluation': '<path d="M4 3v18h17M8 16v-5m5 5V6m5 10V9"/>',
    'applications': '<path d="m12 2 8 3v6c0 5-4 8-8 11-4-3-8-6-8-11V5z"/><path d="m8 12 3 3 5-6"/>',
    'up': '<path d="M12 20V4m-6 6 6-6 6 6"/>',
    'overview': '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5z"/>',
    'directions': '<path d="M5 12h14m-6-6 6 6-6 6"/>',
    'cite': '<path d="M7 7h4v4c0 3-1.5 5-4 6M15 7h4v4c0 3-1.5 5-4 6"/>',
    'paper': '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6m-6 4h4"/>',
    'figures': '<rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="m3 16 5-5 4 4 3-3 6 6"/><circle cx="15.5" cy="8.5" r="1.5"/>',
    'zoom': '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4m-5-8v6m-3-3h6"/>',
}


def ui_icon(name: str) -> str:
    return f'<svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{ICONS[name]}</svg>'


def title(text: str) -> str:
    """卡片标题：连字号和短破折号后不断行（如 model–harness）。"""
    return e(text).replace('–', '–&#8288;').replace('-', '&#8209;')


def rich(text: str) -> str:
    """转义正文，并把 **...** 标成强调。"""
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', e(text))


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise SystemExit(f'不是 PNG：{path}')
    return struct.unpack('>II', data[16:24])


def lqip(path: Path) -> str:
    """由 800px WebP 缩出约 1KB 的预览，以 data URI 内嵌；清晰图加载完成后被覆盖。"""
    import base64
    from io import BytesIO
    from PIL import Image
    with Image.open(path) as image:
        small = image.convert('RGB').resize((48, max(1, round(image.height * 48 / image.width))), Image.LANCZOS)
    buf = BytesIO()
    small.save(buf, 'WEBP', quality=40, method=6)
    return 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def slug(pdf: str) -> str:
    return pdf.rsplit('.', 1)[0].lower().replace('cybersecurity_', '').replace('_', '-')


FIGNO: dict[str, str] = {}   # the paper's own figure numbers


def render_figures() -> None:
    from prepare_assets import prepare_figures, prepare_fonts
    prepare_figures(render=True)
    prepare_fonts()


def figure(f: dict, sid: str, i: int, hidden: bool, tabbed: bool = True) -> str:
    s = slug(f['file'])
    source = f'assets/fig/{s}.svg'
    raster = f'assets/fig/{s}'
    for need in (source, raster + '-800.webp', raster + '-1200.webp', raster + '-2400.webp'):
        if not (ROOT / need).is_file():
            raise SystemExit(f'缺少配图文件：{need}')
    meta = json.loads((ROOT / 'src/figure_manifest.json').read_text())[s]
    image_width, image_height = meta['width'], meta['height']
    FIGNO.setdefault(s, f.get('no', str(len(FIGNO) + 1)))
    alt = e(f.get('alt') or f['caption'])
    label = 'Figure ' + FIGNO[s]
    shape = ' tall' if image_height > image_width * .9 else ''
    panel_attrs = f' role="tabpanel" aria-labelledby="{sid}-t{i}"' if tabbed else ''
    preview = lqip(ROOT / (raster + '-800.webp'))
    srcset = f'{raster}-800.webp 800w, {raster}-1200.webp 1200w'
    sizes = '(max-width: 680px) calc(100vw - 64px), (max-width: 1180px) calc(100vw - 102px), 1078px'
    image_attrs = f'width="{round(image_width)}" height="{round(image_height)}" alt="{alt}" decoding="async"'
    return f'''<figure class="fig{shape}" id="{sid}-f{i}"{' hidden' if hidden else ''}{panel_attrs}>
        <button class="zoom" type="button" data-full="{source}" data-fallback="{raster}-2400.webp" data-download="{s}.svg" aria-label="Explore figure: {e(f.get('tab', ''))}">
          <img class="deferred" src="{preview}" data-src="{raster}-1200.webp" data-srcset="{srcset}" sizes="{sizes}" {image_attrs}>
          <noscript><img src="{raster}-1200.webp" srcset="{srcset}" sizes="{sizes}" {image_attrs} loading="lazy"></noscript>
        </button>
        <figcaption><span class="fno">{label}</span><span class="fcap">{e(f.get('summary', f['caption']))}</span><button class="figure-expand" type="button" aria-label="Open high-resolution figure explorer">Explore <span aria-hidden="true">↗</span></button></figcaption>
      </figure>'''


def viewer(sec: dict) -> str:
    figs = sec.get('figures', [])
    if not figs:
        return ''
    if len(figs) > 1:
        tabs = f'<div class="tabs" role="tablist" aria-label="{e(sec["title"])} figures">' + ''.join(
            f'<button class="tab" id="{sec["id"]}-t{i}" type="button" role="tab" tabindex="{0 if i == 0 else -1}" '
            f'aria-controls="{sec["id"]}-f{i}" aria-selected="{"true" if i == 0 else "false"}">'
            f'<span class="tab-no">Fig. {e(f["no"])}</span>{e(f["tab"])}</button>' for i, f in enumerate(figs)) + '</div>'
    else:
        tabs = f'<span class="viewer-title"><span class="tab-no">Fig. {e(figs[0]["no"])}</span>{e(figs[0]["tab"])}</span>'
    body = '\n      '.join(figure(f, sec['id'], i, i > 0, len(figs) > 1) for i, f in enumerate(figs))
    hint = f'<span class="viewer-hint">{ui_icon("zoom")}Click to zoom</span>'
    return f'<div class="panel viewer reveal"><div class="viewer-bar">{tabs}{hint}</div>\n      {body}\n    </div>'


def points(sec: dict) -> str:
    ps = sec.get('points', [])
    cards = ''.join(f'<div class="point reveal" style="--i:{i}"><span class="point-no" aria-hidden="true">{i + 1:02d}</span>'
                    f'<h3>{title(p["head"])}</h3><p>{e(p["text"])}</p></div>' for i, p in enumerate(ps))
    return f'<div class="points n{len(ps)}">{cards}</div>' if ps else ''


def head(badge: str, sec: dict, extra: str = '') -> str:
    kicker = sec.get('paper_title') or sec['kicker'].split('·')[-1].strip()
    return f'''<div class="sec-head reveal{extra}">
      <div class="sec-kicker"><span class="badge" aria-hidden="true">{badge}</span>{e(kicker)}</div>
      <h2>{e(sec['title'])}</h2>
      <p class="lede">{e(sec['lede'])}</p>
    </div>'''


def stats(sec: dict) -> str:
    st = sec.get('stats', [])
    if not st:
        return ''
    return f'<div class="sec-stats n{len(st)} reveal">' + ''.join(
        f'<div><b>{e(x["value"])}</b><span>{e(x["label"])}</span></div>' for x in st) + '</div>'


def model_comparison(sec: dict) -> str:
    comparison = sec.get('comparison')
    if not comparison:
        return ''
    paths = []
    for path in comparison['paths']:
        steps = ''.join(f'<li><h4>{e(step["head"])}</h4><p>{e(step["text"])}</p></li>' for step in path['steps'])
        paths.append(f'<article class="model-path"><h3>{e(path["title"])}</h3><p class="path-subtitle">{e(path["subtitle"])}</p><ol>{steps}</ol></article>')
    return (f'<div class="model-comparison reveal"><div class="model-paths">{"".join(paths)}</div>'
            f'<div class="model-shared"><h3>{e(comparison["shared_title"])}</h3><p>{e(comparison["shared_text"])}</p></div>'
            f'<p class="comparison-source">{e(comparison["source"])}</p></div>')


def section(num: str, sec: dict) -> str:
    hue = sec.get('hue', 'blue')
    band = ' band' if int(num) % 2 == 1 else ''
    return f'''
  <section class="block chapter{band}" id="{sec['id']}" style="--hue:{HUES[hue]};--hue-soft:{SOFT[hue]}">
    <div class="wrap">
    {head(num.zfill(2), sec)}
    {viewer(sec)}{model_comparison(sec)}
    <div class="findings">{stats(sec)}{points(sec)}</div>
    {sec.get('extra_html', '')}
    </div>
  </section>'''


def hero_people(h: dict) -> str:
    authors = ', '.join(f'<span class="author">{e(a["name"])}<sup>{e(a["affil"])}</sup></span>' for a in h['authors'])
    affils = ''.join(f'<span><sup>{i}</sup>{e(a)}</span>' for i, a in enumerate(h['affiliations'], 1))
    from PIL import Image
    logos = []
    for logo in h['logos']:
        path = ROOT / f'assets/img/logos/{logo["file"]}.png'
        w, ht = png_size(path)
        compact = path.with_suffix('.webp')
        if not compact.exists() or compact.stat().st_mtime < path.stat().st_mtime:
            with Image.open(path) as image:
                image = image.convert('RGBA')
                image.thumbnail((round(w * 104 / ht), 104), Image.Resampling.LANCZOS)
                image.save(compact, 'WEBP', quality=90, method=6)
        logos.append(f'<img class="logo logo-{logo["file"]}" src="assets/img/logos/{logo["file"]}.webp" width="{w}" height="{ht}" '
                     f'alt="{e(logo["alt"])}" title="{e(logo["alt"])}" loading="eager" decoding="async">')
    c = h['contact']
    contact = f'<p class="contact"><sup>*</sup>{e(c["text"])} <a href="mailto:{e(c["email"])}">{e(c["email"])}</a></p>'
    return (f'<p class="authors">{authors}</p>\n    <p class="affils">{affils}</p>\n    {contact}\n'
            f'    <div class="seals">{"".join(logos)}</div>')


def build() -> str:
    FIGNO.clear()
    h = C['hero']
    nav = ''.join(f'<a href="#{n["id"]}">{e(n["label"])}</a>' for n in C['nav'])
    ov = C['overview']
    abstract = ''.join(f'<p>{rich(t)}</p>' for t in ov['abstract'])
    insights = ''.join(f'<div class="insight reveal" style="--i:{i}"><span class="insight-no" aria-hidden="true">{i + 1:02d}</span>'
                       f'<h3>{title(x["head"])}</h3><p>{e(x["text"])}</p></div>' for i, x in enumerate(ov['insights']))
    dim_ids = ('data', 'training', 'models', 'agents', 'evaluation', 'applications')
    dims = ''.join(f'<a class="dim reveal" href="#{sid}" style="--c:{HUES[d["hue"]]};--c-soft:{SOFT[d["hue"]]};--i:{i}">'
                   f'<span class="dim-top"><span class="dim-icon">{ui_icon(sid)}</span><span class="dim-sec">§{e(d["section"])}</span></span>'
                   f'<b>{e(d["name"])}</b><span class="dim-description">{e(d["text"])}</span></a>'
                   for i, (sid, d) in enumerate(zip(dim_ids, ov['dimensions'])))
    overview = f'''
  <section class="block" id="overview" style="--hue:{HUES['blue']};--hue-soft:{SOFT['blue']}">
    <div class="wrap">
    <div class="sec-head reveal">
      <div class="sec-kicker"><span class="badge" aria-hidden="true">{ui_icon('overview')}</span>{e(ov['kicker'])}</div>
      <h2>{e(ov['title'])}</h2>
      <p class="lede">{e(ov['lede'])}</p>
    </div>
    <div class="abstract reveal">{abstract}</div>
    <div class="dims-head reveal"><h3>{e(ov['insights_title'])}</h3><span>Section 1.4 of the survey</span></div>
    <div class="insights">{insights}</div>
    <div class="dims-head reveal"><h3>Jump to a dimension</h3><span>Sections 3–8 of the survey</span></div>
    <div class="dims">{dims}</div>
    </div>
  </section>'''
    body = ''.join(section(s.get('num', str(i + 1)), s) for i, s in enumerate(C['sections']))
    dirs = C['directions']
    dir_html = ''.join(f'<div class="dir reveal" style="--i:{i}"><span class="dir-no" aria-hidden="true">{i + 1:02d}</span>'
                       f'<h3>{title(d["head"])}</h3><p>{e(d["text"])}</p></div>' for i, d in enumerate(dirs['items']))
    questions = ''.join(f'<li class="open-question"><span class="question-no">Q{i + 1}</span><div><h3>{e(q["head"])}</h3><p>{e(q["text"])}</p></div></li>' for i, q in enumerate(dirs.get('questions', [])))
    question_html = (f'<div class="open-questions reveal"><h3 class="questions-title">Five open questions</h3><ol>{questions}</ol></div>' if questions else '')
    directions = f'''
  <section class="block" id="directions" style="--hue:{HUES['blue']};--hue-soft:{SOFT['blue']}">
    <div class="wrap">
    {head(ui_icon('directions'), dirs, ' quote')}
    {question_html}
    <div class="dims-head reveal"><h3>Future directions</h3><span>Section 9.8 of the survey</span></div>
    <div class="dirs">{dir_html}</div>
    </div>
  </section>'''
    cite = C['cite']
    citation = f'''
  <section class="block band" id="cite" style="--hue:{HUES['blue']};--hue-soft:{SOFT['blue']}">
    <div class="wrap">
    {head(ui_icon('cite'), cite)}
    <div class="panel cite reveal"><div class="cite-toolbar"><span class="terminal-label">BibTeX</span><button class="copy" type="button">Copy</button></div><pre id="bibtex">{e(cite['bibtex'])}</pre></div>
    <p class="note">{e(cite['note'])}</p>
    </div>
  </section>'''
    paper_btn = (f'<a class="btn" href="{e(h["paper_url"])}">{ui_icon("paper")}Paper (PDF)</a>' if h.get('paper_url') else
                 f'<span class="btn" aria-disabled="true">{ui_icon("paper")}Paper <span class="soon">Coming soon</span></span>')
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(h['title'])}: {e(h['subtitle'])}</title>
<meta name="description" content="{e(h['tagline'])}">
<meta property="og:title" content="{e(h['title'])}">
<meta property="og:description" content="{e(h['tagline'])}">
<meta property="og:type" content="website">
<meta name="theme-color" content="#f6f8fc">
<link rel="icon" type="image/png" href="assets/img/favicon.png">
<link rel="stylesheet" href="assets/style.css">
<noscript><style>.fig[hidden] {{ display: block; }} .fig img.deferred, .tabs, .viewer-hint, .figure-expand {{ display: none; }} .reveal {{ opacity: 1; transform: none; }} .fig button.zoom::after {{ display: none; }}</style></noscript>
</head>
<body>
<a class="skip" href="#overview">Skip to content</a>
<nav class="nav" aria-label="Sections">
  <div class="nav-in">
    <a class="brand" href="#top"><span class="brand-mark"><img src="assets/img/mascot-256.png" alt="" width="28" height="28"></span><span>LLMs for Cybersecurity</span></a>
    <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="section-nav"><span class="mt-label">Sections</span><span aria-hidden="true">+</span></button>
    <div class="nav-links" id="section-nav">{nav}</div>
    <div class="reading-progress" role="progressbar" aria-label="Reading progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><span></span></div>
  </div>
</nav>
<canvas class="cursor-comet" id="cursor-comet" aria-hidden="true"></canvas>
<header class="hero" id="top">
  <div class="hero-art" aria-hidden="true"><div class="hero-aurora"></div><span class="blob b1"></span><span class="blob b2"></span><span class="blob b3"></span></div>
  <div class="wrap hero-inner">
    <h1>{h['title_html'].replace('class="accent"', 'class="accent g"')}</h1>
    <p class="subtitle">{e(h['subtitle'])}</p>
    {hero_people(h)}
    <div class="actions">
      <a class="btn primary" href="#overview">{ui_icon("figures")}Explore the survey</a>
      {paper_btn}
      <a class="btn" href="#cite">{ui_icon("cite")}BibTeX</a>
    </div>
  </div>
</header>
<main>{overview}{body}{directions}{citation}
</main>
<footer>
  <div class="wrap">
    <span class="footer-brand"><span class="brand-mark"><img src="assets/img/mascot-256.png" alt="" width="28" height="28"></span><span>{e(h['title'])}<small>{e(h['footer_date'])}</small></span></span>
    <div class="footer-links"><a href="#overview">Overview</a><a href="#directions">Outlook</a><a href="#cite">Citation</a><a href="#top">Back to top ↑</a></div>
  </div>
</footer>
<a class="back-top" href="#top" aria-label="Back to top" hidden>{ui_icon('up')}</a>
<dialog class="lightbox" id="lightbox" aria-label="Figure explorer" aria-describedby="lb-caption">
  <div class="lb-toolbar">
    <span class="lb-title">Figure explorer <small class="lb-quality" aria-live="polite">Preview</small></span>
    <div class="lb-controls" role="group" aria-label="Zoom controls">
      <button class="lb-out" type="button" aria-label="Zoom out">−</button>
      <output class="lb-scale" aria-live="polite">100%</output>
      <button class="lb-in" type="button" aria-label="Zoom in">+</button>
      <button class="lb-fit" type="button">Fit</button>
      <button class="lb-vector" type="button">Load vector</button>
      <a class="lb-download" download>Save SVG</a>
      <button class="lb-close" type="button" aria-label="Close figure explorer">Close</button>
    </div>
  </div>
  <div class="lb-viewport" tabindex="0" aria-label="Figure canvas; use zoom buttons and scroll to explore">
    <div class="lb-stage"><img alt="" draggable="false"></div>
  </div>
  <div class="lb-footer"><p class="lb-cap" id="lb-caption"></p><span>Zoom · drag to explore</span></div>
</dialog>
<script src="assets/site.js"></script>
</body>
</html>
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='生成综述网站；--public 输出可直接发布的 public/')
    parser.add_argument('--public', action='store_true', help='输出无口令的公开版到 public/（直接打开主页）')
    parser.add_argument('--skip-assets', action='store_true', help='保留现有 SVG 和字体，仅重建页面')
    args = parser.parse_args()
    if not args.skip_assets:
        render_figures()
    out = build()
    (ROOT / 'index.html').write_text(out, encoding='utf-8')
    print('index.html', len(out.encode('utf-8')), 'bytes;', len(FIGNO), 'figures')
    if args.public:
        from public import export_public
        export_public(ROOT, C['hero'].get('site_url', ''))
