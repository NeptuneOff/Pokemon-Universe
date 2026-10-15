from pathlib import Path
import json,csv,re,hashlib,subprocess
from PIL import Image
root=Path(__file__).resolve().parents[1]
src=root.parent/'sprite-source/src/sprites/gen5'
pokemon=json.loads((root/'data/pokemon-raw.json').read_text());moves=json.loads((root/'data/moves.json').read_text())
names={int(r['pokemon_species_id']):r['name'] for r in csv.DictReader((root/'data/names.csv').open()) if r['local_language_id']=='5'}
meta={int(r['id']):r for r in csv.DictReader((root/'data/species.csv').open())}
manifest={};missing=[]
normalize=lambda s:re.sub('[^a-z0-9]','',s.lower())
lookup={normalize(f.stem):f for f in src.iterdir() if f.suffix in ['.png','.gif']}
for id,p in pokemon.items():
 p['fr']=names.get(p['num'],p['name'])+(' · '+p['forme'] if p['forme'] else '')
 p['catchRate']=int(meta.get(p['num'],{}).get('capture_rate',45))
 p['legendary']=bool(int(meta.get(p['num'],{}).get('is_legendary',0)) or int(meta.get(p['num'],{}).get('is_mythical',0)))
 name=re.sub('[^a-z0-9]','',(p['name'].split('-')[0]).lower())
 # Smogon source format: s<species>-o<form>, with hyphens removed within forme.
 base=p['base'] or id
 forme=re.sub('[^a-z0-9]','',(p['forme'] or '').lower())
 stem='s'+base+('-o'+forme if forme else '')
 aliases={'nidoranf':'snidoranf','nidoranm':'snidoranm','mrmime':'smrmime','mimejr':'smimejr','typenull':'stypenull','tapu koko':'stapukoko','sirfetchd':'ssirfetchd','mrrime':'smrrime'}
 stem=aliases.get(id,stem)
 paths={}
 for back in [False,True]:
  suffix='-b' if back else ''
  candidates=[src/(stem+suffix+e) for e in ['.png','.gif']]
  f=next((x for x in candidates if x.exists()),None) or lookup.get(normalize(stem+suffix))
  if f:
   im=Image.open(f).convert('RGBA');bbox=im.getbbox()
   if bbox:im=im.crop(bbox)
   # Retain native pixels; never resample 3D renders or mix generational art.
   name=id+('-back' if back else '')+'.png';im.save(root/'assets/pokemon'/name)
   paths['back' if back else 'front']='assets/pokemon/'+name
   manifest[name]={'source':str(f.relative_to(src.parent.parent.parent.parent)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
 p['sprite']=paths.get('front');p['back']=paths.get('back')
 if not p['sprite']:missing.append(id)
moves['struggle']={'id':'struggle','name':'Lutte','type':'Normal','power':50,'category':'Physical','accuracy':100,'pp':1,'priority':0}
moves['focus']={'id':'focus','name':'Concentration','type':'Normal','power':0,'category':'Status','accuracy':100,'pp':15,'priority':0}
(root/'data/game-data.js').write_text('window.GAME_DATA='+json.dumps({'pokemon':pokemon,'moves':moves},ensure_ascii=False,separators=(',',':'))+';')
(root/'docs/sprites-manifest.json').write_text(json.dumps(manifest,indent=2))
(root/'docs/missing-sprites.json').write_text(json.dumps(missing,indent=2))
print(json.dumps({'base':sum(not p['forme'] for p in pokemon.values()),'forms':len(pokemon),'mega_variants':sum(p['mega'] for p in pokemon.values()),'missing':len(missing),'missing_examples':missing[:25],'sprites':len(manifest)}))
