from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SKIP={'.git','node_modules','dist','build','.next','.venv','venv','__pycache__'}
legacy=''.join(('ki','mi'))
errors=[]
for path in ROOT.rglob('*'):
    rel=path.relative_to(ROOT)
    if any(part in SKIP for part in rel.parts):continue
    if legacy in rel.as_posix().casefold():errors.append(f'legacy filename: {rel}')
    if not path.is_file():continue
    try:text=path.read_text(encoding='utf-8')
    except (UnicodeDecodeError,OSError):continue
    if legacy in text.casefold():errors.append(f'legacy text: {rel}')
if errors:
    raise SystemExit('\n'.join(errors))
print('PASS: Orcha-only brand contract')
