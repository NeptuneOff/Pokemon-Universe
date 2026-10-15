"""Bundle PNG sprites into offline JavaScript resources, preserving exact bytes."""
from pathlib import Path
import base64,json
root=Path(__file__).resolve().parents[1]
files=sorted((root/'assets/pokemon').glob('*.png'))
if not files:raise SystemExit('No sprites: run unpack_sprites.py or prepare_data.py first')
for stale in (root/'assets').glob('pokemon-*.js'):stale.unlink()
chunks=[];chunk={};size=0
for f in files:
 data='data:image/png;base64,'+base64.b64encode(f.read_bytes()).decode()
 if size+len(data)>240000 and chunk:chunks.append(chunk);chunk={};size=0
 chunk['assets/pokemon/'+f.name]=data;size+=len(data)
if chunk:chunks.append(chunk)
for i,chunk in enumerate(chunks,1):
 (root/'assets'/f'pokemon-{i:02}.js').write_text('Object.assign(window.POKEMON_SPRITES ||= {},'+json.dumps(chunk,separators=(',',':'))+');\n')
index=root/'index.html';s=index.read_text();start='<!-- SPRITE BUNDLES -->';end='<!-- END SPRITE BUNDLES -->';block=start+'\n'+''.join(f'<script src="assets/pokemon-{i:02}.js"></script>\n' for i in range(1,len(chunks)+1))+end
if start in s:s=s[:s.index(start)]+block+s[s.index(end)+len(end):]
else:s=s.replace('<script src="data/game-data.js">',block+'\n<script src="data/game-data.js">')
if 'src/bind-sprites.js' not in s:s=s.replace('<script src="data/campaign.js">','<script src="src/bind-sprites.js"></script><script src="data/campaign.js">')
index.write_text(s)
print(f'{len(files)} images in {len(chunks)} bundles')
