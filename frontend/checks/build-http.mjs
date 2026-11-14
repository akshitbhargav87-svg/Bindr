import {createRequire} from 'node:module';import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url);const env={...process.env,VITE_USE_MOCK:'false'};
execFileSync(process.execPath,[require.resolve('typescript/bin/tsc'),'-b'],{stdio:'inherit',env});
execFileSync(process.execPath,[fileURLToPath(new URL('../node_modules/vite/bin/vite.js',import.meta.url)),'build','--outDir','dist-http'],{stdio:'inherit',env});
