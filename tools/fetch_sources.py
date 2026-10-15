from pathlib import Path
import urllib.request,concurrent.futures
root=Path(__file__).resolve().parents[1]
urls={
'pokedex-source.ts':'https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/pokedex.ts',
'learnsets-source.ts':'https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/learnsets.ts',
'moves-source.ts':'https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/moves.ts',
'names.csv':'https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/pokemon_species_names.csv',
'species.csv':'https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/pokemon_species.csv',
'SHOWDOWN-LICENSE':'https://raw.githubusercontent.com/smogon/pokemon-showdown/master/LICENSE',
'SPRITES-LICENSE':'https://raw.githubusercontent.com/PokeAPI/sprites/master/LICENCE.txt'}
def get(pair):
 name,url=pair
 try:
  d=urllib.request.urlopen(url,timeout=45).read();(root/'data'/name).write_bytes(d);return name,len(d)
 except Exception as e:return name,str(e)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 for r in ex.map(get,urls.items()):print(r,flush=True)
