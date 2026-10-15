import fs from 'node:fs';
import vm from 'node:vm';
import {stripTypeScriptTypes} from 'node:module';
const root=new URL('../',import.meta.url);
function parse(file,symbol){let src=fs.readFileSync(new URL('data/'+file,root),'utf8');src=stripTypeScriptTypes(src).replace('export const '+symbol,'globalThis.result');let ctx={};vm.runInNewContext(src,ctx);return ctx.result;}
const all=parse('pokedex-source.ts','Pokedex'),learn=parse('learnsets-source.ts','Learnsets'),moves=parse('moves-source.ts','Moves');
const keep={};
for(const [id,p] of Object.entries(all))if(p.num>0&&p.num<=1025&&!/Totem/.test(p.forme||'')&&((!p.forme||/^(Alola|Galar|Hisui|Paldea)/.test(p.forme||''))||/Mega/.test(p.forme||'')))keep[id]=p;
for(const p of Object.values(keep))if(p.baseSpecies){let id=p.baseSpecies.toLowerCase().replace(/[^a-z0-9]/g,'');if(all[id])keep[id]=all[id];}
const safeMoves={};
for(const [id,m]of Object.entries(moves))if(m.basePower>0&&m.basePower<=120&&m.category!=='Status'&&!m.isZ&&!m.isMax&&!m.isNonstandard&&!m.onModifyMove&&!m.damageCallback&&!m.damage&&!m.selfdestruct&&!m.multihit){safeMoves[id]={id,name:m.name,type:m.type,power:m.basePower,category:m.category,accuracy:m.accuracy===true?100:m.accuracy,pp:m.pp,priority:m.priority||0};}
const out={};
for(const[id,p]of Object.entries(keep)){
 let pool=new Set(),cur=p;
 for(let n=0;n<5&&cur;n++){
  const ls=learn[cur.name.toLowerCase().replace(/[^a-z0-9]/g,'')]?.learnset||{};
  for(const [mid,versions]of Object.entries(ls))if(safeMoves[mid]&&versions.some(v=>/^[1-9]/.test(v)))pool.add(mid);
  cur=all[(cur.prevo||cur.baseSpecies||'').toLowerCase().replace(/[^a-z0-9]/g,'')];
 }
 out[id]={id,num:p.num,name:p.name,types:p.types,stats:p.baseStats,base:p.baseSpecies? p.baseSpecies.toLowerCase().replace(/[^a-z0-9]/g,''):null,forme:p.forme||null,mega:/Mega/.test(p.forme||''),stone:p.requiredItem||null,ability:p.abilities[0],evolutions:(p.evos||[]).map(x=>x.toLowerCase().replace(/[^a-z0-9]/g,'')),evoLevel:p.evoLevel||null,evoType:p.evoType||null,evoItem:p.evoItem||null,prevo:p.prevo||null,moves:[...pool]};
}
fs.writeFileSync(new URL('data/pokemon-raw.json',root),JSON.stringify(out));
fs.writeFileSync(new URL('data/moves.json',root),JSON.stringify(safeMoves));
console.log({species:Object.keys(out).length,megas:Object.values(out).filter(p=>p.mega).length,moves:Object.keys(safeMoves).length});
