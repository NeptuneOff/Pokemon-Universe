"""Restore editable PNG files from bundled resources (no network required)."""
from pathlib import Path
import json,base64
root=Path(__file__).resolve().parents[1]
out=root/'assets/pokemon';out.mkdir(parents=True,exist_ok=True)
count=0
for f in sorted((root/'assets').glob('pokemon-*.js')):
 s=f.read_text();data=json.loads(s.split('{},',1)[1].rsplit(');',1)[0])
 for name,value in data.items():
  if not value.startswith('data:image/png;base64,'):raise ValueError(name)
  (out/Path(name).name).write_bytes(base64.b64decode(value.split(',',1)[1]));count+=1
print(f'{count} PNG files restored in {out}')
