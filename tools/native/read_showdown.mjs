// Developer tool. Pinned data extraction; never executed by JOUER.bat.
import fs from 'node:fs';
import vm from 'node:vm';
import zlib from 'node:zlib';
import {stripTypeScriptTypes} from 'node:module';
const [input, output] = process.argv.slice(2);
if (!input || !output) throw Error('Usage: node read_showdown.mjs pokedex.ts[.gz] output.json');
const bytes = fs.readFileSync(input);
const source = stripTypeScriptTypes((input.endsWith('.gz') ? zlib.gunzipSync(bytes) : bytes).toString('utf8'));
if (!source.includes('export const Pokedex')) throw Error('Unexpected source format');
const context = Object.create(null);
vm.runInNewContext(source.replace('export const Pokedex', 'globalThis.result'), context,
  {timeout: 1000, contextCodeGeneration: {strings: false, wasm: false}});
if (!context.result || typeof context.result !== 'object') throw Error('Missing Pokedex');
fs.writeFileSync(output, JSON.stringify(context.result), {flag: 'wx'});
