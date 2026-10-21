"""从最终 PDF 无损提取 SVG，并准备自托管字体；默认只审计图源。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import fitz
import requests

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'finalimages/images'
FONT_SPECS = {
    'sora': ('Sora:wght@600..800', 'sora'),
    'inter': ('Inter:wght@400..800', 'inter'),
    'jetbrains-mono': ('JetBrains+Mono:wght@400..600', 'jetbrainsmono'),
}


def source_for(figure: dict) -> Path:
    if figure.get('source_pdf'):
        source = (ROOT / figure['source_pdf']).resolve()
    else:
        prefix = 'Cover_' if figure['no'] == 'Cover' else f'Fig{int(figure["no"]):02d}'
        matches = sorted(SOURCE.glob(prefix + '*.pdf'))
        if len(matches) != 1:
            raise ValueError(f'图源必须唯一：{prefix}，实际 {matches}')
        source = matches[0]
    if not source.is_file():
        raise FileNotFoundError(source)
    return source


def svg_from_page(page: fitz.Page) -> str:
    # 字形转为路径，避免读者机器缺字体导致替换；原有位图保持原生像素。
    svg = page.get_svg_image(text_as_path=True)
    root = ET.fromstring(svg)
    if root.tag != '{http://www.w3.org/2000/svg}svg':
        raise ValueError('导出结果不是 SVG')
    for node in root.iter():
        if node.tag.rsplit('}', 1)[-1] in {'script', 'foreignObject'}:
            raise ValueError('SVG 包含非图形节点')
        for name, value in node.attrib.items():
            if name.rsplit('}', 1)[-1] == 'href' and not value.startswith(('#', 'data:image/')):
                raise ValueError('SVG 包含外部依赖')
    return svg


WEBP_WIDTHS = (800, 1200, 2400)   # 正文用位图（按屏幕挑选）；放大查看时才加载 SVG
LQIP_WIDTH = 48                     # 内嵌在页面里的模糊预览，慢网下也能立即看到图的轮廓


def webp_set(page: fitz.Page) -> dict[int, bytes]:
    """按最大宽度栅格化一次，再用 Lanczos 缩出各档；白底不透明，2x 屏上文字清晰。"""
    from io import BytesIO
    from PIL import Image
    top = max(WEBP_WIDTHS)
    zoom = top / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    base = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    out = {}
    for width in WEBP_WIDTHS:
        image = base if width == top else base.resize((width, round(base.height * width / base.width)), Image.LANCZOS)
        buf = BytesIO()
        image.save(buf, 'WEBP', quality=86 if width == top else 82, method=6)
        out[width] = buf.getvalue()
    return out


def prepare_figures(render: bool = False) -> dict:
    from build import C, slug

    manifest = {}
    for section in C['sections']:
        for figure in section.get('figures', []):
            source = source_for(figure)
            with fitz.open(source) as doc:
                if len(doc) != 1:
                    raise ValueError(f'配图须为单页：{source}')
                page = doc[0]
                svg = svg_from_page(page)
                s = slug(figure['file'])
                record = {
                    'source': str(source.relative_to(ROOT.parent)),
                    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                    'svg_sha256': hashlib.sha256(svg.encode()).hexdigest(),
                    'width': round(page.rect.width, 3), 'height': round(page.rect.height, 3),
                    'text_spans': len(page.get_text('words')), 'vector_paths': len(page.get_drawings()),
                    'embedded_images': len(page.get_images()),
                    'svg_bytes': len(svg.encode()),
                }
                manifest[s] = record
                if render:
                    (ROOT / 'assets/fig' / f'{s}.svg').write_text(svg, encoding='utf-8')
                    for width, data in webp_set(page).items():
                        (ROOT / 'assets/fig' / f'{s}-{width}.webp').write_bytes(data)
                        record[f'webp_{width}_bytes'] = len(data)
                print(f'{figure["no"]:>5}: {record["vector_paths"]:4} paths, '
                      f'{record["text_spans"]:4} words, {record["embedded_images"]:3} images, '
                      f'{record["svg_bytes"] / 1024:7.1f} KiB SVG, '
                      f'{record.get("webp_1200_bytes", 0) / 1024:5.0f}/{record.get("webp_2400_bytes", 0) / 1024:5.0f} KiB WebP | {source.name}')
    if render:
        (ROOT / 'src/figure_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


def prepare_fonts() -> None:
    directory = ROOT / 'assets/fonts'
    directory.mkdir(exist_ok=True)
    session = requests.Session()
    session.headers['User-Agent'] = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                                     'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36')
    for filename, (family, license_dir) in FONT_SPECS.items():
        target = directory / f'{filename}-latin.woff2'
        license_path = directory / f'{filename}-OFL.txt'
        if not target.exists():
            response = session.get(f'https://fonts.googleapis.com/css2?family={family}&display=swap', timeout=30)
            response.raise_for_status()
            latin = re.search(r'/\* latin \*/\s*(@font-face\s*\{[^}]+\})', response.text)
            if not latin:
                raise ValueError(f'缺少 Latin 字体子集：{family}')
            url = re.search(r'url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)', latin[1])
            if not url:
                raise ValueError(f'字体 URL 格式不正确：{family}')
            font = session.get(url[1], timeout=30)
            font.raise_for_status()
            if font.content[:4] != b'wOF2':
                raise ValueError('字体不是 WOFF2')
            target.write_bytes(font.content)
        if not license_path.exists():
            response = session.get(f'https://raw.githubusercontent.com/google/fonts/main/ofl/{license_dir}/OFL.txt', timeout=30)
            response.raise_for_status()
            if 'SIL OPEN FONT LICENSE' not in response.text:
                raise ValueError('字体授权文件不正确')
            license_path.write_text(response.text, encoding='utf-8')
        print(f'自托管字体：{target.name} ({target.stat().st_size / 1024:.1f} KiB)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render', action='store_true', help='输出无损 SVG 与图源记录')
    parser.add_argument('--fonts', action='store_true', help='获取缺少的 WOFF2 字体和 OFL 许可证')
    args = parser.parse_args()
    prepare_figures(args.render)
    if args.fonts:
        prepare_fonts()
