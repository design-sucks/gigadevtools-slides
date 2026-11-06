/* Decode an explicitly supplied EOT to a new private file; verify face and rights separately. */
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {eotToTtf,parseEotMetadata} from '../vendor/mtx-decompressor/index.mjs';
const [input,output,...rest]=process.argv.slice(2);
if(!input||!output||rest.length)throw Error('Usage: node decode_eot.mjs SOURCE.fntdata NEW_PRIVATE_OUTPUT.ttf');
const data=await fs.readFile(input),hash=buf=>createHash('sha256').update(buf).digest('hex');
const info=parseEotMetadata(data),result=eotToTtf(data,{maxOutputBytes:128*1024*1024});
await fs.writeFile(output,result,{flag:'wx'});
console.log(JSON.stringify({status:'decoded_unverified',inputSha256:hash(data),outputSha256:hash(result),bytes:result.length,compressed:info.compressed,encrypted:info.encrypted,notice:'Inspect actual names, face, glyphs and embedding permissions before use. Do not publish source fonts without permission.'}));
