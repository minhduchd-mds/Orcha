from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPLACEMENTS = [
    ('KimiK3 Studio.command', 'Orcha.command'),
    ('KimiK3 Studio.vbs', 'Orcha.vbs'),
    ('Stop KimiK3 Studio.command', 'Stop Orcha.command'),
    ('Stop KimiK3 Studio.vbs', 'Stop Orcha.vbs'),
    ('kimik3-lite-v3-quality', 'orcha-v3-quality'),
    ('kimik3-lite-v3-max', 'orcha-v3-max'),
    ('kimik3-lite-v3', 'orcha-v3'),
    ('kimik3_lite', 'orcha_core'),
    ('.kimik3ignore', '.orchaignore'),
    ('KimiK3-Lite', 'Orcha'),
    ('KimiK3 Lite', 'Orcha'),
    ('KimiK3', 'Orcha'),
    ('KIMIK3', 'ORCHA'),
    ('kimik3-lite', 'orcha'),
    ('kimik3', 'orcha'),
    ('Kimi', 'Orcha'),
    ('kimi', 'orcha'),
]

SKIP_DIRS = {'.git', 'node_modules', 'dist', 'build', '.next', '.venv', 'venv', '__pycache__'}


def replace_text(text: str) -> str:
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    text = text.replace("os.environ.get('ORCHA_DATA_DIR') or os.environ.get('ORCHA_DATA_DIR') or", "os.environ.get('ORCHA_DATA_DIR') or")
    text = text.replace("os.environ['ORCHA_DATA_DIR']=directory;os.environ['ORCHA_DATA_DIR']=directory", "os.environ['ORCHA_DATA_DIR']=directory")
    text = text.replace("${ORCHA_PORT:-${ORCHA_PORT:-11435}}", "${ORCHA_PORT:-11435}")
    text = re.sub(r"\$\{ORCHA_DATA_DIR:-\$\{ORCHA_DATA_DIR:-([^}]*)\}\}", r"${ORCHA_DATA_DIR:-\1}", text)
    text = text.replace("localStorage.getItem('orcha.project')||localStorage.getItem('orcha.project')", "localStorage.getItem('orcha.project')")
    text = text.replace('canonical Orcha-derived/Orcha tokens', 'canonical Orcha tokens')
    text = text.replace('Orcha-derived/Orcha tokens', 'Orcha tokens')
    return text


def text_files():
    for path in ROOT.rglob('*'):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        try:
            path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        yield path


def clean_verify():
    path = ROOT / 'scripts' / 'verify.py'
    if not path.exists():
        return
    lines = path.read_text(encoding='utf-8').splitlines()
    out=[];skip_next=False
    for line in lines:
        if skip_next:
            if 'raise AssertionError' in line and 'Retired Orcha product name' in line:
                skip_next=False
                continue
            skip_next=False
        if 'if re.search(' in line and 'index,re.I' in line and 'Orcha' in line:
            skip_next=True
            continue
        out.append(line)
    path.write_text('\n'.join(out)+'\n', encoding='utf-8', newline='\n')


def rename_paths():
    paths = sorted(
        [p for p in ROOT.rglob('*') if p.exists() and '.git' not in p.parts],
        key=lambda p: len(p.parts),
        reverse=True,
    )
    for path in paths:
        name = path.name
        new_name = replace_text(name)
        if new_name == name:
            continue
        target = path.with_name(new_name)
        if target.exists():
            if path.is_file():
                path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
            continue
        path.rename(target)


def write_brand_guard():
    path = ROOT / 'scripts' / 'check_brand.py'
    path.write_text("""from pathlib import Path\n\nROOT=Path(__file__).resolve().parents[1]\nSKIP={'.git','node_modules','dist','build','.next','.venv','venv','__pycache__'}\nlegacy=''.join(('ki','mi'))\nerrors=[]\nfor path in ROOT.rglob('*'):\n    rel=path.relative_to(ROOT)\n    if any(part in SKIP for part in rel.parts):continue\n    if legacy in rel.as_posix().casefold():errors.append(f'legacy filename: {rel}')\n    if not path.is_file():continue\n    try:text=path.read_text(encoding='utf-8')\n    except (UnicodeDecodeError,OSError):continue\n    if legacy in text.casefold():errors.append(f'legacy text: {rel}')\nif errors:\n    raise SystemExit('\\n'.join(errors))\nprint('PASS: Orcha-only brand contract')\n""", encoding='utf-8', newline='\n')


def main():
    for path in list(text_files()):
        text = path.read_text(encoding='utf-8')
        updated = replace_text(text)
        if updated != text:
            path.write_text(updated, encoding='utf-8', newline='\n')
    clean_verify()
    rename_paths()
    write_brand_guard()


if __name__ == '__main__':
    main()
