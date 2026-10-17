#!/usr/bin/env node
/**
 * minify_cf_function.js — build-time minifier + size gate for the CloudFront
 * Function viewer-request (10,240 B hard cap; discovered the cap the hard way
 * on v19: 10,525 B upload → FunctionSizeLimitExceeded, 218 B headroom left
 * at v18).
 *
 * The repo keeps the READABLE source (deploy/aws/cloudfront-functions/
 * viewer-request.js); the bytes uploaded via update-function are this
 * minified form. Method = conservative line-minification only (drop full-line
 * `//` comments + blank lines + leading/trailing indentation per line) —
 * no token joining, no string/regex inspection, so it cannot corrupt code
 * semantics; a stray inline comment in a future edit only makes output
 * bigger (the gate alarms), never wrong. Output is additionally
 * `node --check`ed — a syntax break (e.g. someone adds a multi-line
 * template literal containing a `//` line) fails loudly.
 *
 * Usage:
 *   node scripts/minify_cf_function.js            # minified JS to stdout
 *   node scripts/minify_cf_function.js --out F    # minified JS to file F
 *   node scripts/minify_cf_function.js --check    # gate: exit 1 if minified
 *                                                 # size > threshold (CI mode)
 *   --max N                                       # override threshold (B)
 *
 * Publish flow (manual, from repo root):
 *   node scripts/minify_cf_function.js --out /tmp/cf.min.js   # + --check gate
 *   node /tmp/cf_test_v19.js-style harness against /tmp/cf.min.js (72/72)
 *   ETAG=$(aws cloudfront describe-function --name vigyanllm-clean-urls-v6 --query ETag --output text)
 *   aws cloudfront update-function --name vigyanllm-clean-urls-v6 --if-match $ETAG \
 *     --function-code fileb:///tmp/cf.min.js \
 *     --function-config "Comment=vNN - ...",Runtime=cloudfront-js-2.0   # NO COMMA in Comment (shorthand list-split)
 *   aws cloudfront publish-function --name vigyanllm-clean-urls-v6 --if-match <new-dev-etag>
 *   verify: aws cloudfront get-function --stage LIVE /tmp/live.js && md5 /tmp/live.js /tmp/cf.min.js
 *           (LIVE byte-compares against the MINIFIED artifact, not the source)
 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const CF_SRC = path.join(__dirname, '..', 'deploy', 'aws', 'cloudfront-functions', 'viewer-request.js');
// Gate threshold: 440 B under the hard 10,240 B cap — alarms before the wall,
// leaves room for a normal v-entry (~150-300 B) without another crunch.
const DEFAULT_MAX = 9800;

function minifyLines(src) {
  const out = [];
  for (const raw of src.split('\n')) {
    const t = raw.trim();
    if (t === '' || t.startsWith('//')) continue; // blank or full-line comment
    out.push(t);
  }
  return out.join('\n') + '\n';
}

function main(argv) {
  let outFile = null;
  let checkOnly = false;
  let max = DEFAULT_MAX;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--out') outFile = argv[++i];
    else if (argv[i] === '--check') checkOnly = true;
    else if (argv[i] === '--max') max = parseInt(argv[++i], 10);
    else { console.error('unknown arg: ' + argv[i]); process.exit(2); }
  }

  const src = fs.readFileSync(CF_SRC, 'utf8');
  const min = minifyLines(src);

  // Corruption gate: the minified artifact must parse.
  const tmp = path.join(os.tmpdir(), 'cf_minify_check_' + process.pid + '.js');
  fs.writeFileSync(tmp, min);
  const chk = spawnSync(process.execPath, ['--check', tmp], { encoding: 'utf8' });
  fs.unlinkSync(tmp);
  if (chk.status !== 0) {
    console.error('FATAL: minified output fails node --check — do not publish.');
    console.error(chk.stderr || chk.stdout || '');
    process.exit(1);
  }

  const srcB = Buffer.byteLength(src, 'utf8');
  const minB = Buffer.byteLength(min, 'utf8');
  const over = minB > max;

  if (checkOnly) {
    const verdict = over ? 'OVER THRESHOLD' : 'OK';
    console.log(
      'cf-function size gate: source ' + srcB + ' B -> minified ' + minB +
      ' B (cap 10240, threshold ' + max + ') — ' + verdict + ' [node --check OK]'
    );
    process.exit(over ? 1 : 0);
  }

  if (outFile) {
    fs.writeFileSync(outFile, min);
    console.error('wrote ' + outFile + ' (' + minB + ' B; source ' + srcB + ' B)');
  } else {
    process.stdout.write(min);
  }
}

main(process.argv.slice(2));
