#!/usr/bin/env node
/**
 * qpcr_universal_node.mjs — node ESM harness for the universal engine parity
 * tests (QPCR_UNIVERSAL_FORMAT_SUPPORT_TASKS.md T6.2).
 *
 * Usage:
 *   node tests/qpcr_universal_node.mjs <file1> [file2 ...]
 *
 * Prints one JSON line per input file:
 *   {"file": <name>, "run": <canonical run>}     on success
 *   {"file": <name>, "error": {"message", "doctor"}}  on FormatError / throw
 *
 * The canonical run is JSON-safe: amplification Float32Array → plain array,
 * melt arrays copied. Compared against tests/universal_mirror.py output by
 * tests/test_universal.py (float tolerance for RK/Float32 truncation).
 */
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';
import { parseFileUniversal } from '../frontend/qpcr/qpcr-universal.js';

function serializeRun(name, run) {
  return {
    file: name,
    run: {
      meta: run.meta,
      channels: run.channels,
      targets: run.targets,
      samples: run.samples,
      wells: run.wells.map(w => ({
        id: w.id, row: w.row, col: w.col, layout: w.layout, position: w.position,
        sampleId: w.sampleId, targetId: w.targetId, channelId: w.channelId,
        cq: w.cq, cqSD: w.cqSD, tm: w.tm, tmPeaks: w.tmPeaks,
        amplification: Array.from(w.amplification),
        melt: w.melt ? { temps: Array.from(w.melt.temps), fluores: Array.from(w.melt.fluores) } : null,
      })),
      detection: run.detection,
      cqOnly: run.cqOnly === undefined ? null : run.cqOnly,
    },
  };
}

for (const path of process.argv.slice(2)) {
  const name = basename(path);
  try {
    const buf = readFileSync(path);
    const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
    const run = await parseFileUniversal(name, ab);
    console.log(JSON.stringify(serializeRun(name, run)));
  } catch (e) {
    console.log(JSON.stringify({
      file: name,
      error: { message: String(e && e.message || e), doctor: (e && e.doctor) || null },
    }));
  }
}
