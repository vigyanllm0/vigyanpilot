/**
 * qpcr-universal.js — Universal Format Engine (v1).
 *
 * QPCR_UNIVERSAL_FORMAT_SUPPORT_TASKS.md — any instrument file either parses
 * to a canonical Run or yields a format-doctor card that explains exactly what
 * was seen and what to do next.
 *
 * Ironlaw shape:
 *   file dropped → sniff (zip/ole/gzip/text — MAGIC BYTES, never the extension)
 *     → decode (UTF-8/UTF-16/BOM, any delimiter)
 *     → known fast paths (RDML / CFX / template headers)
 *     → universal layout reasoner (~90 column aliases → sections → blocks →
 *       sameWell merge)
 *     → format doctor when nothing matches.
 *
 * Ironclad rules (founder):
 *   - sniff content, not extension;
 *   - show detected instrument info, never reject on brand;
 *   - no dead ends — the doctor always explains + next step;
 *   - detection from data, not hard-coded brand checks;
 *   - analysis layer unchanged (analyzeRun runs exactly as before).
 *
 * Python mirror: tests/universal_mirror.py — tests/test_universal.py runs the
 * same fixtures through BOTH (this module via node subprocess) and compares
 * canonical runs. Keep every evidence string / constant in lockstep.
 */
import {
  canonicalChannel, detectFormat, guessReference, guessSampleType,
  makeChannel, makeRun, makeSample, makeTarget, makeWell,
  parseCfxCsv, parsePosition, parseRdml, parseTemplate,
} from './qpcr-engine.js';

export const QPCR_UNIVERSAL_VERSION = '1.0.0';

export const ROTOR_EXTS = ['qbd', 'qbg', 'qbt', 'rgd', 'rgx', 'rex'];

/** Formats the doctor's "what works here" list (identical in Python mirror). */
export const SUPPORTED_FORMATS = [
  'RDML (.rdml) — full curves + Cq',
  'Bio-Rad CFX CSV — sectioned or long-format',
  'Template CSV/TSV — Well, Sample, Target, Channel, Cq',
  'Any instrument CSV/TSV/TXT — universal layout reasoner',
  'Excel .xlsx — native (ZIP + XML)',
  'Legacy Excel .xls — native OLE2/BIFF8 reader',
  'ZIP — deep-probes inner .csv/.tsv/.txt/.rdml/.xlsx',
];

/** Thrown when the format doctor rejects a file. `.doctor` carries the card. */
export class FormatError extends Error {
  constructor(message, doctor) {
    super(message);
    this.name = 'FormatError';
    this.doctor = doctor || {};
  }
}

/* ─────────────────────────────────────────────────────────────────
   1. Container sniffing (magic bytes — never the extension)
   ───────────────────────────────────────────────────────────────── */

function toBytes(buf) {
  if (buf instanceof Uint8Array) {
    if (buf.byteOffset === 0 && buf.byteLength === buf.buffer.byteLength) return buf;
    return new Uint8Array(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
  }
  return new Uint8Array(buf);
}

export function sniff(input) {
  const u8 = toBytes(input);
  if (u8.length >= 4) {
    if (u8[0] === 0x50 && u8[1] === 0x4B && u8[2] === 0x03 && u8[3] === 0x04) return 'zip';
    if (u8[0] === 0xD0 && u8[1] === 0xCF && u8[2] === 0x11 && u8[3] === 0xE0) return 'ole';
    if (u8[0] === 0x1F && u8[1] === 0x8B) return 'gzip';
  }
  const lim = Math.min(u8.length, 1000);
  let hasNul = false;
  for (let i = 0; i < lim; i++) { if (u8[i] === 0) { hasNul = true; break; } }
  if (hasNul) {
    if (lim >= 8) {
      let even = 0, odd = 0;
      for (let i = 0; i < lim - 1; i += 2) if (u8[i] === 0) even++;
      for (let i = 1; i < lim; i += 2) if (u8[i] === 0) odd++;
      const pairs = lim >> 1;
      if (pairs && (even > pairs * 0.3 || odd > pairs * 0.3) && Math.abs(even - odd) > pairs * 0.25) {
        return 'text';
      }
    }
    return 'binary';
  }
  return 'text';
}

export function extOf(fileName) {
  const base = String(fileName || '').split(/[\\/]/).pop() || '';
  if (!base.includes('.')) return '';
  return base.split('.').pop().toLowerCase();
}

/* ─────────────────────────────────────────────────────────────────
   2. Decoding (BOM-aware; UTF-16 no-BOM via NUL parity)
   ───────────────────────────────────────────────────────────────── */

export function decodeText(input) {
  const u8 = toBytes(input);
  if (u8.length >= 3 && u8[0] === 0xEF && u8[1] === 0xBB && u8[2] === 0xBF) {
    return new TextDecoder('utf-8').decode(u8.subarray(3));
  }
  if (u8.length >= 2 && u8[0] === 0xFF && u8[1] === 0xFE) {
    return new TextDecoder('utf-16le').decode(u8.subarray(2));
  }
  if (u8.length >= 2 && u8[0] === 0xFE && u8[1] === 0xFF) {
    return new TextDecoder('utf-16be').decode(u8.subarray(2));
  }
  // UTF-16 without BOM: NUL parity decides.
  // LE ASCII: char bytes at even indices, NULs at ODD. BE: NULs at EVEN.
  if (u8.length >= 4) {
    let hasNul = false;
    for (let i = 0; i < Math.min(u8.length, 200); i++) { if (u8[i] === 0) { hasNul = true; break; } }
    if (hasNul) {
      const lim = Math.min(u8.length, 1000);
      let even = 0, odd = 0;
      for (let i = 0; i < lim - 1; i += 2) if (u8[i] === 0) even++;
      for (let i = 1; i < lim; i += 2) if (u8[i] === 0) odd++;
      if (even > 40 && even > odd * 3) return new TextDecoder('utf-16be').decode(u8);
      if (odd > 40 && odd > even * 3) return new TextDecoder('utf-16le').decode(u8);
    }
  }
  return new TextDecoder('utf-8').decode(u8);
}

/** Numeric cell → number, or null (mirrors Python _num: full-string parse). */
export function num(v) {
  if (v === null || v === undefined || typeof v === 'boolean') return null;
  if (typeof v === 'number') return Number.isNaN(v) ? null : v;
  const s = String(v).trim();
  if (s === '') return null;
  const n = Number(s);
  return Number.isNaN(n) ? null : n;
}

/** Cell → string for header matching (1.0 → '1' via JS number formatting). */
export function s(v) {
  if (v === null || v === undefined) return '';
  return String(v).trim();
}

/* ─────────────────────────────────────────────────────────────────
   3. Delimiter detection + quote-aware row split
   ───────────────────────────────────────────────────────────────── */

function splitLine(line, delim) {
  const out = [];
  let cur = '';
  let inQ = false;
  let i = 0;
  while (i < line.length) {
    const ch = line[i];
    if (ch === '"') {
      if (inQ && i + 1 < line.length && line[i + 1] === '"') { cur += '"'; i++; }
      else inQ = !inQ;
    } else if (ch === delim && !inQ) {
      out.push(cur); cur = '';
    } else {
      cur += ch;
    }
    i++;
  }
  out.push(cur);
  return out;
}

export function splitRows(text, delim) {
  const rows = [];
  for (const raw of String(text).split('\n')) {
    const line = raw.replace(/\r$/, '');
    if (!line.trim()) continue;
    rows.push(splitLine(line, delim).map(c => (typeof c === 'string' ? c.trim() : c)));
  }
  return rows;
}

export function detectDelimiter(text) {
  const candidates = [',', '\t', ';', '|'];
  const lines = String(text).split('\n').filter(l => l.trim()).slice(0, 15);
  if (!lines.length) return ',';
  let best = ',', bestScore = 0;
  for (const d of candidates) {
    const counts = lines.map(l => splitLine(l, d).length);
    const modal = counts.slice().sort((a, b) =>
      counts.filter(c => c === b).length - counts.filter(c => c === a).length)[0];
    if (modal < 2) continue;
    const consistency = counts.filter(c => c === modal).length / counts.length;
    const score = consistency * 10 + Math.min(modal, 40) * 0.1;
    if (score > bestScore) { best = d; bestScore = score; }
  }
  return best;
}

/* ─────────────────────────────────────────────────────────────────
   4. Column alias table (~90 entries — data, not code)
      norm_key form: lowercase, non-alnum → single space, stripped
   ───────────────────────────────────────────────────────────────── */

export const COLUMN_ALIASES = [
  // well / position
  ['well', 'well'], ['well id', 'well'], ['well position', 'well'], ['well pos', 'well'],
  ['well name', 'well'], ['well label', 'well'], ['well no', 'well'], ['well number', 'well'],
  ['position', 'well'], ['pos', 'well'], ['pos id', 'well'], ['chamber', 'well'],
  ['chamber id', 'well'], ['location', 'well'],
  // sample
  ['sample', 'sample'], ['sample name', 'sample'], ['sample id', 'sample'],
  ['sample label', 'sample'], ['sample no', 'sample'], ['sample number', 'sample'],
  ['specimen', 'sample'], ['specimen name', 'sample'], ['name', 'sample'],
  ['sample s', 'sample'],
  // target / assay
  ['target', 'target'], ['target name', 'target'], ['target id', 'target'],
  ['assay', 'target'], ['assay name', 'target'], ['assay id', 'target'],
  ['gene', 'target'], ['gene name', 'target'], ['oligo', 'target'], ['oligo name', 'target'],
  ['detection', 'target'], ['detection name', 'target'], ['amplicon', 'target'],
  ['amplicon name', 'target'], ['target assay', 'target'],
  // dye / channel
  ['dye', 'dye'], ['dye name', 'dye'], ['fluor', 'dye'], ['fluorophore', 'dye'],
  ['reporter', 'dye'], ['channel', 'dye'], ['signal channel', 'dye'],
  ['fam', 'dye'], ['hex', 'dye'], ['vic', 'dye'], ['joe', 'dye'], ['tet', 'dye'],
  ['rox', 'dye'], ['texas red', 'dye'], ['texasred', 'dye'], ['cy5', 'dye'],
  ['cy 5', 'dye'], ['cy5 5', 'dye'], ['tamra', 'dye'], ['ned', 'dye'],
  ['quasar', 'dye'], ['quasar 670', 'dye'], ['quasar 705', 'dye'],
  ['sybr', 'dye'], ['sybr green', 'dye'], ['sybr green i', 'dye'],
  ['eva green', 'dye'], ['evagreen', 'dye'], ['lc green', 'dye'],
  ['cal gold 540', 'dye'], ['cal orange 560', 'dye'],
  // sample type
  ['type', 'stype'], ['sample type', 'stype'], ['content', 'stype'], ['task', 'stype'],
  ['category', 'stype'], ['class', 'stype'], ['sample class', 'stype'], ['role', 'stype'],
  ['sample role', 'stype'], ['well type', 'stype'],
  // quantity / concentration
  ['qty', 'qty'], ['quantity', 'qty'], ['conc', 'qty'], ['concentration', 'qty'],
  ['std quantity', 'qty'], ['standard quantity', 'qty'], ['copy number', 'qty'],
  ['copies', 'qty'], ['input quantity', 'qty'], ['amount', 'qty'], ['dilution', 'qty'],
  // Cq / Ct / Cp
  ['cq', 'cq'], ['ct', 'cq'], ['cp', 'cq'], ['cq mean', 'cq'], ['ct mean', 'cq'],
  ['threshold cycle', 'cq'], ['cq value', 'cq'], ['ct value', 'cq'],
  ['cq result', 'cq'], ['ct result', 'cq'],
  // Cq dispersion
  ['cq sd', 'cqsd'], ['cq std dev', 'cqsd'], ['cq stddev', 'cqsd'],
  ['ct sd', 'cqsd'], ['ct std dev', 'cqsd'], ['ct stddev', 'cqsd'],
  ['standard deviation', 'cqsd'], ['sd', 'cqsd'], ['cq std', 'cqsd'], ['ct std', 'cqsd'],
  // melt temperature (per-well Tm result)
  ['tm', 'tm'], ['tm 1', 'tm'], ['tm1', 'tm'], ['tm c', 'tm'],
  ['melt temp', 'tm'], ['melt temperature', 'tm'], ['melting temperature', 'tm'],
  ['melting temp', 'tm'], ['tm peak', 'tm'], ['melting point', 'tm'],
  // melt x-axis temperature (melt-long)
  ['temperature', 'temp'], ['temp', 'temp'], ['temp c', 'temp'], ['temperature c', 'temp'],
  // cycle index
  ['cycle', 'cycle'], ['cycles', 'cycle'], ['cycle no', 'cycle'], ['cycle number', 'cycle'],
  ['pcr cycle', 'cycle'], ['amplification cycle', 'cycle'], ['cycle index', 'cycle'],
  // per-cycle value (long tables)
  ['value', 'value'], ['fluorescence', 'value'], ['fluorescence value', 'value'],
  ['signal', 'value'], ['signal value', 'value'], ['rfu', 'value'], ['delta rn', 'value'],
  ['dn', 'value'], ['rf', 'value'], ['amplitude', 'value'],
  // metadata key/value
  ['instrument', 'meta'], ['instrument name', 'meta'], ['software', 'meta'],
  ['run date', 'meta'], ['date', 'meta'], ['operator', 'meta'], ['run name', 'meta'],
  ['experiment', 'meta'], ['experiment name', 'meta'], ['comments', 'meta'],
  ['comment', 'meta'], ['run', 'meta'], ['plate', 'meta'], ['plate id', 'meta'],
];
const ALIAS_MAP = new Map(COLUMN_ALIASES);

export function normKey(str) {
  let t = s(str);
  t = t.toLowerCase();
  t = t.replace(/[^a-z0-9]+/g, ' ');
  return t.replace(/\s+/g, ' ').trim();
}

/** Map column index → canonical kind for cells that hit the alias table. */
export function classifyHeader(cells) {
  const kinds = {};
  for (let i = 0; i < cells.length; i++) {
    const k = ALIAS_MAP.get(normKey(cells[i]));
    if (k && !(i in kinds)) kinds[i] = k;
  }
  return kinds;
}

/**
 * Ascending bare-numerics (→ cycles), "Cycle N" labels, M65.0 melt runs.
 * Qualification: ≥5 columns in both cases.
 */
export function detectHeaderRuns(cells) {
  const labeled = [];
  const meltCols = [];
  for (let i = 0; i < cells.length; i++) {
    const t = s(cells[i]);
    let m = t.match(/^cycle\s*(\d+)$/i);
    if (m) { labeled.push([i, parseInt(m[1], 10)]); continue; }
    m = t.match(/^m\s*(\d+(?:\.\d+)?)$/i);
    if (m) meltCols.push([i, parseFloat(m[1])]);
  }
  // bare numeric ascending runs (1,2,3,…,40)
  const runs = [];
  let run = [];
  let prev = null;
  for (let i = 0; i < cells.length; i++) {
    const t = s(cells[i]);
    if (/^\d+$/.test(t)) {
      const v = parseInt(t, 10);
      if (prev !== null && v === prev + 1) {
        run.push([i, v]);
      } else {
        if (run.length >= 5) runs.push(run);
        run = v === 1 ? [[i, v]] : [];
      }
      prev = v;
    } else {
      if (run.length >= 5) runs.push(run);
      run = []; prev = null;
    }
  }
  if (run.length >= 5) runs.push(run);
  let cycleCols;
  if (labeled.length >= 5) cycleCols = labeled;
  else {
    cycleCols = [];
    for (const r of runs) if (r.length > cycleCols.length) cycleCols = r;
  }
  const melt = meltCols.length >= 5 ? meltCols : [];
  return { cycle: cycleCols, melt };
}

/** → (kinds, runs) when the row looks like a header row, else ({}, empty runs). */
export function scoreHeader(cells) {
  const kinds = classifyHeader(cells);
  const runs = detectHeaderRuns(cells);
  if (Object.keys(kinds).length >= 2) return { kinds, runs };
  if (Object.keys(kinds).length === 1 && (runs.cycle.length || runs.melt.length)) {
    return { kinds, runs };
  }
  return { kinds: {}, runs: { cycle: [], melt: [] } };
}

/* ─────────────────────────────────────────────────────────────────
   5. Section splitting (banner rows = exactly-one-nonempty-cell)
   ───────────────────────────────────────────────────────────────── */

export function splitSections(rows) {
  let sections = [];
  let cur = { title: '', rows: [] };
  for (const row of rows) {
    const nonempty = row.filter(c => s(c));
    if (nonempty.length === 1) {
      sections.push(cur);
      cur = { title: s(nonempty[0]), rows: [] };
    } else {
      cur.rows.push(row);
    }
  }
  sections.push(cur);
  return sections.filter(sec => sec.rows.length);
}

const KIND_LABEL = {
  'amp-wide': 'amplification (wide Cycle N matrix)',
  'amp-long': 'amplification (long per-cycle table)',
  'melt-wide': 'melt (wide M##.## matrix)',
  'melt-long': 'melt (long per-temperature table)',
  'cq': 'Cq results table',
  'meta': 'metadata / key-value',
};

function classifySection(sec) {
  let headerIdx = null;
  let kinds = {};
  let runs = { cycle: [], melt: [] };
  for (let i = 0; i < sec.rows.length; i++) {
    const sc = scoreHeader(sec.rows[i]);
    if (Object.keys(sc.kinds).length) {
      headerIdx = i; kinds = sc.kinds; runs = sc.runs;
      break;
    }
  }
  if (headerIdx === null) {
    return { kind: 'meta', kinds: {}, runs: { cycle: [], melt: [] }, headerIdx: null, title: sec.title };
  }
  const kindValues = Object.values(kinds);
  let kind;
  if (runs.cycle.length) kind = 'amp-wide';
  else if (runs.melt.length) kind = 'melt-wide';
  else if (kindValues.includes('cycle') && kindValues.includes('value')) kind = 'amp-long';
  else if (kindValues.includes('temp') && kindValues.includes('value')) kind = 'melt-long';
  else if (kindValues.includes('cq')) kind = 'cq';
  else kind = 'meta';
  return { kind, kinds, runs, headerIdx, title: sec.title };
}

/* ─────────────────────────────────────────────────────────────────
   6. Block readers → fragments
   ───────────────────────────────────────────────────────────────── */

function cell(row, i) {
  return (i >= 0 && i < row.length) ? row[i] : null;
}

function fragFromRow(kinds, row) {
  const f = {
    pos: null, sample: null, target: null, dye: null, stype: null,
    qty: null, cq: null, cqsd: null, tm: null,
  };
  for (const i of Object.keys(kinds)) {
    const kind = kinds[i];
    const v = cell(row, Number(i));
    if (v === null || v === undefined || !s(v)) continue;
    if (kind === 'well') f.pos = s(v);
    else if (kind === 'sample') f.sample = s(v);
    else if (kind === 'target') f.target = s(v);
    else if (kind === 'dye') f.dye = s(v);
    else if (kind === 'stype') f.stype = s(v);
    else if (kind === 'qty') { const n = num(v); if (n !== null) f.qty = n; }
    else if (kind === 'cq') { const n = num(v); if (n !== null) f.cq = n; }
    else if (kind === 'cqsd') { const n = num(v); if (n !== null) f.cqsd = n; }
    else if (kind === 'tm') { const n = num(v); if (n !== null) f.tm = n; }
  }
  return f;
}

function hasIdentity(f) {
  return Boolean(f.pos || f.sample || f.target);
}

function readAmpWide(info, rows) {
  const frags = [];
  const runCols = info.runs.cycle;
  for (const row of rows.slice(info.headerIdx + 1)) {
    if (row.filter(c => s(c)).length < 2) continue;
    const f = fragFromRow(info.kinds, row);
    if (!hasIdentity(f)) continue;
    f.kind = 'amp';
    f.cycles = [];
    for (const [col, n] of runCols) {
      const v = num(cell(row, col));
      if (v !== null) f.cycles.push([n, v]);
    }
    frags.push(f);
  }
  return frags;
}

function groupAmp(frags) {
  const groups = new Map();
  const order = [];
  for (const f of frags) {
    const key = [
      f.pos ? f.pos.toUpperCase() : null,
      (f.sample || '').toLowerCase(),
      (f.target || '').toLowerCase(),
      (f.dye || '').toLowerCase(),
    ].join('\u0001');
    if (groups.has(key)) {
      const g = groups.get(key);
      g.cycles = g.cycles.concat(f.cycles);
      if (!g.cq && f.cq !== null) { g.cq = f.cq; g.cqsd = f.cqsd; g.tm = f.tm; }
    } else {
      groups.set(key, f);
      order.push(key);
    }
  }
  const out = [];
  for (const key of order) {
    const f = groups.get(key);
    f.cycles.sort((a, b) => a[0] - b[0]);
    out.push(f);
  }
  return out;
}

function readAmpLong(info, rows) {
  const cycleCol = Number(Object.keys(info.kinds).find(c => info.kinds[c] === 'cycle'));
  const valueCol = Number(Object.keys(info.kinds).find(c => info.kinds[c] === 'value'));
  const frags = [];
  for (const row of rows.slice(info.headerIdx + 1)) {
    if (row.filter(c => s(c)).length < 2) continue;
    const f = fragFromRow(info.kinds, row);
    if (!hasIdentity(f)) continue;
    const cyc = num(cell(row, cycleCol));
    const val = num(cell(row, valueCol));
    if (cyc === null || val === null) continue;
    f.kind = 'amp';
    f.cycles = [[Math.trunc(cyc), val]];
    frags.push(f);
  }
  return groupAmp(frags);
}

function readMeltWide(info, rows) {
  const frags = [];
  const runCols = info.runs.melt;
  for (const row of rows.slice(info.headerIdx + 1)) {
    if (row.filter(c => s(c)).length < 2) continue;
    const f = fragFromRow(info.kinds, row);
    if (!hasIdentity(f)) continue;
    const temps = [];
    const fluors = [];
    for (const [col, t] of runCols) {
      const v = num(cell(row, col));
      if (v !== null) { temps.push(t); fluors.push(v); }
    }
    if (!temps.length) continue;
    f.kind = 'melt';
    f.temps = temps;
    f.fluors = fluors;
    frags.push(f);
  }
  return frags;
}

function readMeltLong(info, rows) {
  const tempCol = Number(Object.keys(info.kinds).find(c => info.kinds[c] === 'temp'));
  const valueCol = Number(Object.keys(info.kinds).find(c => info.kinds[c] === 'value'));
  const frags = [];
  for (const row of rows.slice(info.headerIdx + 1)) {
    if (row.filter(c => s(c)).length < 2) continue;
    const f = fragFromRow(info.kinds, row);
    if (!hasIdentity(f)) continue;
    const t = num(cell(row, tempCol));
    const v = num(cell(row, valueCol));
    if (t === null || v === null) continue;
    f.kind = 'melt';
    f.temps = (f.temps || []).concat([t]);
    f.fluors = (f.fluors || []).concat([v]);
    frags.push(f);
  }
  return groupMelt(frags);
}

function groupMelt(frags) {
  /* Anti-duplicate: one fragment per (position|sample, target, dye), temps sorted. */
  const groups = new Map();
  const order = [];
  for (const f of frags) {
    const key = [
      f.pos ? f.pos.toUpperCase() : null,
      (f.sample || '').toLowerCase(),
      (f.target || '').toLowerCase(),
      (f.dye || '').toLowerCase(),
    ].join('\u0001');
    if (groups.has(key)) {
      const g = groups.get(key);
      g.temps = g.temps.concat(f.temps);
      g.fluors = g.fluors.concat(f.fluors);
    } else {
      groups.set(key, f);
      order.push(key);
    }
  }
  const out = [];
  for (const key of order) {
    const f = groups.get(key);
    const paired = f.temps.map((t, i) => [t, f.fluors[i]]);
    paired.sort((a, b) => a[0] - b[0]);
    f.temps = paired.map(p => p[0]);
    f.fluors = paired.map(p => p[1]);
    out.push(f);
  }
  return out;
}

function readCqTable(info, rows) {
  const frags = [];
  for (const row of rows.slice(info.headerIdx + 1)) {
    if (row.filter(c => s(c)).length < 2) continue;
    const f = fragFromRow(info.kinds, row);
    if (!hasIdentity(f)) continue;
    f.kind = 'cq';
    frags.push(f);
  }
  return frags;
}

function readMetaSection(info, rows) {
  const pairs = {};
  const start = info.headerIdx !== null ? info.headerIdx : 0;
  for (const row of rows.slice(start)) {
    const nonempty = [];
    for (let i = 0; i < row.length; i++) if (s(row[i])) nonempty.push([i, s(row[i])]);
    if (nonempty.length < 2) continue;
    const key = normKey(nonempty[0][1]);
    if (ALIAS_MAP.has(key) && ALIAS_MAP.get(key) !== 'meta') continue; // foreign table header
    pairs[key] = nonempty[1][1];
  }
  return pairs;
}

/* ─────────────────────────────────────────────────────────────────
   7. sameWell merge rule (replicate-safe)
   ───────────────────────────────────────────────────────────────── */

export function sameWell(a, b) {
  const pa = a.pos, pb = b.pos;
  if (pa && pb) return pa.toUpperCase() === pb.toUpperCase();
  const sa = (a.sample || '').trim().toLowerCase();
  const sb = (b.sample || '').trim().toLowerCase();
  if (!sa || !sb) return false;
  if (sa !== sb) return false;
  const ta = (a.target || '').trim().toLowerCase();
  const tb = (b.target || '').trim().toLowerCase();
  return !ta || !tb || ta === tb;
}

/* ─────────────────────────────────────────────────────────────────
   8. Assembly: fragments → canonical Run
   ───────────────────────────────────────────────────────────────── */

const STYPE_KEYWORDS = [
  [/ntc|negative|no template|blank|water/, 'ntc'],
  [/standard|std|stds|calibrat/, 'standard'],
  [/control|ctrl|ref|reference/, 'control'],
];

function typeFrom(stype, sampleName) {
  if (stype) {
    const low = stype.toLowerCase();
    for (const [pat, t] of STYPE_KEYWORDS) if (pat.test(low)) return t;
  }
  return guessSampleType(sampleName);
}

export function attachDetection(run, fmt, confidence, evidence) {
  run.detection = {
    format: fmt,
    confidence: Math.round(confidence * 100) / 100,
    evidence: evidence.slice(),
  };
  return run;
}

export function markCqOnly(run) {
  run.cqOnly = run.wells.length > 0
    && run.wells.every(w => (w.amplification ? w.amplification.length : 0) === 0);
  return run;
}

/**
 * The universal layout reasoner. Returns a canonical Run or null.
 * rows: array of arrays of cells (strings or numbers).
 */
export function reasonRows(rows, fileName, sourceFormat, sheetName) {
  sourceFormat = sourceFormat || 'universal';
  const sections = splitSections(rows);
  const classified = [];
  const metaPairs = {};
  for (const sec of sections) {
    const info = classifySection(sec);
    info._rows = sec.rows;
    if (info.kind === 'meta') Object.assign(metaPairs, readMetaSection(info, sec.rows));
    else classified.push(info);
  }
  let ampFrags = [];
  let meltFrags = [];
  let cqFrags = [];
  const evidence = [];
  for (const info of classified) {
    evidence.push(`Section "${info.title || '(untitled)'}" → ${KIND_LABEL[info.kind]}`);
    if (info.kind === 'amp-wide') {
      ampFrags = ampFrags.concat(readAmpWide(info, info._rows));
      const runCols = info.runs.cycle;
      if (runCols.length) {
        evidence.push(`Ascending bare-numeric cycle run: ${runCols[0][1]}..${runCols[runCols.length - 1][1]} (${runCols.length} columns)`);
      }
    } else if (info.kind === 'amp-long') {
      ampFrags = ampFrags.concat(readAmpLong(info, info._rows));
    } else if (info.kind === 'melt-wide') {
      meltFrags = meltFrags.concat(readMeltWide(info, info._rows));
      evidence.push(`M##.## melt-temperature run: ${info.runs.melt.length} columns`);
    } else if (info.kind === 'melt-long') {
      meltFrags = meltFrags.concat(readMeltLong(info, info._rows));
    } else if (info.kind === 'cq') {
      cqFrags = cqFrags.concat(readCqTable(info, info._rows));
    }
  }
  if (!ampFrags.length && !meltFrags.length && !cqFrags.length) return null;

  // instrument identity from metadata
  const instrument = metaPairs.instrument;

  // merge: amp base → melt → cq (replicate-safe sameWell)
  const order = [];
  const find = f => order.find(rec => sameWell(rec.frag, f)) || null;

  let mergedMelt = false;
  let mergedCq = false;
  for (const f of ampFrags) {
    const rec = find(f);
    if (rec) rec.frag.cycles = rec.frag.cycles.concat(f.cycles);
    else order.push({ frag: f, melt: null, cq: null });
  }
  for (const f of meltFrags) {
    const rec = find(f);
    if (rec && rec.melt === null) { rec.melt = f; mergedMelt = true; }
    else if (!rec) order.push({ frag: f, melt: f, cq: null });
  }
  for (const f of cqFrags) {
    const rec = find(f);
    if (rec) {
      if (rec.cq === null) {
        rec.cq = f;
        mergedCq = mergedCq || Boolean(rec.frag.cycles && rec.frag.cycles.length);
      }
    } else {
      order.push({ frag: f, melt: null, cq: f });
    }
  }

  // canonical registries
  const run = makeRun({ fileName, sourceFormat });
  if (instrument) {
    run.meta.instrument = instrument;
    evidence.push(`Instrument identity from file: ${instrument}`);
  }
  const sampleIds = new Map();
  const targetIds = new Map();
  const channelIds = new Map();

  const sampleIdFor = (name, qty) => {
    if (sampleIds.has(name)) {
      const sid = sampleIds.get(name);
      if (qty !== null && run.samples[sid].quantity === null) run.samples[sid].quantity = qty;
      return sid;
    }
    const sid = run.samples.length;
    run.samples.push(makeSample(sid, name, typeFrom(null, name), qty));
    sampleIds.set(name, sid);
    return sid;
  };
  const targetIdFor = (name) => {
    if (targetIds.has(name)) return targetIds.get(name);
    const tid = run.targets.length;
    run.targets.push(makeTarget(tid, name, null, guessReference(name)));
    targetIds.set(name, tid);
    return tid;
  };
  const channelIdFor = (dyeRaw) => {
    let canon = dyeRaw ? canonicalChannel(dyeRaw) : null;
    canon = canon || (dyeRaw ? dyeRaw.toUpperCase() : 'FAM');
    if (channelIds.has(canon)) return channelIds.get(canon);
    const cid = run.channels.length;
    run.channels.push(makeChannel(cid, dyeRaw || 'FAM', canon));
    channelIds.set(canon, cid);
    return cid;
  };

  let anyPos = false;
  let anyCq = false;
  let anyCycles = false;
  for (const rec of order) {
    const f = rec.frag;
    const cqRec = rec.cq;
    const base = Object.assign({}, f);
    if (cqRec) {
      for (const k of ['cq', 'cqsd', 'tm']) {
        if (cqRec[k] !== null && cqRec[k] !== undefined && base[k] === null) base[k] = cqRec[k];
      }
      if (!base.stype && cqRec.stype) base.stype = cqRec.stype;
      if (base.qty === null && cqRec.qty !== null) base.qty = cqRec.qty;
      if (!base.sample && cqRec.sample) base.sample = cqRec.sample;
      if (!base.target && cqRec.target) base.target = cqRec.target;
      if (!base.dye && cqRec.dye) base.dye = cqRec.dye;
    }
    const pos = base.pos || '';
    const sampleName = base.sample || pos || 'Unknown';
    const targetName = base.target || 'Unknown';
    const sid = sampleIdFor(sampleName, base.qty);
    const tid = targetIdFor(targetName);
    const cid = channelIdFor(base.dye);
    if (base.stype) run.samples[sid].type = typeFrom(base.stype, sampleName);
    const pp = pos
      ? parsePosition(pos, 96)
      : { row: Math.floor(run.wells.length / 12), col: run.wells.length % 12 };
    const well = makeWell(run.wells.length, pp.row, pp.col, '96');
    well.sampleId = sid;
    well.targetId = tid;
    well.channelId = cid;
    well.cq = base.cq;
    well.cqSD = base.cqsd;
    well.tm = base.tm;
    const cycles = (f.cycles || []).slice().sort((a, b) => a[0] - b[0]);
    well.amplification = new Float32Array(cycles.map(p => p[1]));
    if (rec.melt) {
      well.melt = {
        temps: (rec.melt.temps || []).slice(),
        fluores: (rec.melt.fluors || []).slice(),
      };
    }
    run.wells.push(well);
    if (pos) anyPos = true;
    if (well.cq !== null) anyCq = true;
    if (well.amplification.length > 0) anyCycles = true;
  }

  if (!run.channels.length) run.channels.push(makeChannel(0, 'FAM', 'FAM'));
  for (const t of run.targets) if (t.channelId == null) t.channelId = 0;

  // evidence + confidence
  const kindsHit = new Set();
  for (const info of classified) for (const k of Object.values(info.kinds)) kindsHit.add(k);
  if (kindsHit.size) evidence.push(`Header aliases matched: ${Array.from(kindsHit).sort().join(', ')}`);
  if (anyPos) evidence.push('Well positions parse as plate addresses (A1-style)');
  if (anyCq) evidence.push('Instrument-reported Cq values present');
  if (anyCycles) evidence.push('Per-cycle fluorescence present');
  if (mergedCq) {
    evidence.push('Cross-section merge: Cq table attached to amplification wells by well position');
  }
  if (mergedMelt) evidence.push('Cross-section merge: melt table attached to amplification wells');
  if (sheetName) evidence.push(`Worksheet "${sheetName}" read as grid rows`);

  let conf = 0;
  const structuredCycles = classified.some(info =>
    (info.kind === 'amp-wide' && info.runs.cycle.length >= 5) || info.kind === 'amp-long');
  if (structuredCycles) conf += 0.25;
  if (anyPos) conf += 0.2;
  if (anyCq) conf += 0.2;
  if (anyCycles) conf += 0.15;
  if (sampleIds.size) conf += 0.1;
  if (targetIds.size) conf += 0.05;
  markCqOnly(run);
  if (run.cqOnly) {
    evidence.push('Cq-only export: no per-cycle fluorescence — the amplification chart will state this honestly');
  }
  attachDetection(run, 'reasoner', Math.min(conf, 0.99), evidence);
  return run;
}

/** grids: [{name, grid: [[cells]]}] — first sheet that reasons wins. */
export function reasonGrids(grids, fileName, sourceFormat) {
  for (const g of grids) {
    const grid = g.grid || [];
    if (!grid.length) continue;
    const rows = grid.map(row => row.map(c => s(c)));
    const run = reasonRows(rows, fileName, sourceFormat || 'universal', g.name);
    if (run) return run;
  }
  return null;
}

/* ─────────────────────────────────────────────────────────────────
   9. OLE2 / CFB reader (spec T3.1)
   ───────────────────────────────────────────────────────────────── */

const ENDOFCHAIN = 0xFFFFFFFE;
const FREESECT = 0xFFFFFFFF;

export function readCfb(input) {
  const u8 = toBytes(input);
  const view = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  const sig = 'd0cf11e0a1b11ae1';
  for (let i = 0; i < 8; i++) {
    if (u8[i] !== parseInt(sig.substr(i * 2, 2), 16)) {
      throw new Error('not an OLE2 compound document (bad signature)');
    }
  }
  const sectorShift = view.getUint16(30, true);
  const sectorSize = 1 << sectorShift;
  if (sectorSize !== 512 && sectorSize !== 4096) throw new Error(`bad sector shift ${sectorShift}`);
  const numFat = view.getUint32(44, true);
  const firstDir = view.getUint32(48, true);
  const miniCutoff = view.getUint32(56, true);
  const firstMiniFat = view.getUint32(60, true);
  const firstDifat = view.getUint32(68, true);
  const numDifat = view.getUint32(72, true);

  const sector = (n) => {
    const off = 512 + n * sectorSize;
    if (off + sectorSize > u8.length) throw new Error(`sector ${n} beyond EOF`);
    return u8.subarray(off, off + sectorSize);
  };

  // DIFAT: header's 109 entries + chain
  const difat = [];
  for (let i = 0; i < 109; i++) difat.push(view.getUint32(76 + i * 4, true));
  let nxt = firstDifat;
  let guard = 0;
  while (numDifat > 0 && nxt !== ENDOFCHAIN && nxt !== FREESECT && guard < 10000) {
    guard++;
    const sd = sector(nxt);
    const sv = new DataView(sd.buffer, sd.byteOffset, sd.byteLength);
    for (let i = 0; i < sectorSize / 4 - 1; i++) difat.push(sv.getUint32(i * 4, true));
    nxt = sv.getUint32(sectorSize - 4, true);
  }
  const fat = [];
  for (const fs of difat) {
    if (fs === ENDOFCHAIN || fs === FREESECT) continue;
    const sd = sector(fs);
    const sv = new DataView(sd.buffer, sd.byteOffset, sd.byteLength);
    for (let i = 0; i < sectorSize / 4; i++) fat.push(sv.getUint32(i * 4, true));
    if (fat.length >= numFat * (sectorSize / 4)) break;
  }

  const chain = (start) => {
    const out = [];
    let n = start;
    let g = 0;
    while (n !== ENDOFCHAIN && n !== FREESECT && g < (1 << 20)) {
      g++;
      out.push(n);
      if (n >= fat.length) throw new Error('FAT chain escapes table');
      n = fat[n];
    }
    return out;
  };
  const streamBytes = (start, size) => {
    const parts = chain(start).map(sector);
    const total = parts.reduce((a, p) => a + p.length, 0);
    const out = new Uint8Array(total);
    let off = 0;
    for (const p of parts) { out.set(p, off); off += p.length; }
    return out.subarray(0, Math.min(size, total));
  };

  // directory
  const dirParts = chain(firstDir).map(sector);
  const dirTotal = dirParts.reduce((a, p) => a + p.length, 0);
  const dirData = new Uint8Array(dirTotal);
  { let off = 0; for (const p of dirParts) { dirData.set(p, off); off += p.length; } }
  const entries = new Map();
  let root = null;
  for (let i = 0; i < dirData.length / 128; i++) {
    const e = dirData.subarray(i * 128, (i + 1) * 128);
    const ev = new DataView(e.buffer, e.byteOffset, e.byteLength);
    const etype = e[66];
    if (etype !== 1 && etype !== 2 && etype !== 5) continue;
    const nameLen = ev.getUint16(64, true); // bytes, incl. UTF-16 null terminator
    const start = ev.getUint32(116, true);
    const size = Number(ev.getBigUint64(120, true));
    if (nameLen < 2) {
      if (etype === 5) root = { etype, start, size };
      continue;
    }
    let name = '';
    for (let k = 0; k < nameLen - 2; k += 2) {
      name += String.fromCharCode(e[k] | (e[k + 1] << 8));
    }
    const rec = { etype, start, size };
    entries.set(name, rec);
    if (etype === 5) root = rec;
  }
  if (!root) throw new Error('no Root Entry in CFB directory');

  // mini-stream + miniFAT
  const ministream = root.size ? streamBytes(root.start, root.size) : new Uint8Array(0);
  let miniFat = [];
  if (firstMiniFat !== ENDOFCHAIN && firstMiniFat !== FREESECT) {
    const mfParts = chain(firstMiniFat).map(sector);
    const mfTotal = mfParts.reduce((a, p) => a + p.length, 0);
    const mf = new Uint8Array(mfTotal);
    { let off = 0; for (const p of mfParts) { mf.set(p, off); off += p.length; } }
    const mv = new DataView(mf.buffer);
    for (let i = 0; i < mf.length / 4; i++) miniFat.push(mv.getUint32(i * 4, true));
  }
  const miniBytes = (start, size) => {
    const chunks = [];
    let n = start;
    let g = 0;
    while (n !== ENDOFCHAIN && n !== FREESECT && g < (1 << 20)) {
      g++;
      chunks.push(ministream.subarray(n * 64, (n + 1) * 64));
      if (n >= miniFat.length) throw new Error('miniFAT chain escapes table');
      n = miniFat[n];
    }
    const total = chunks.reduce((a, c) => a + c.length, 0);
    const out = new Uint8Array(total);
    { let off = 0; for (const c of chunks) { out.set(c, off); off += c.length; } }
    return out.subarray(0, Math.min(size, total));
  };

  const streams = {};
  for (const [name, rec] of entries) {
    if (rec.etype !== 2) continue;
    streams[name] = rec.size < miniCutoff ? miniBytes(rec.start, rec.size)
      : streamBytes(rec.start, rec.size);
  }
  if (!Object.keys(streams).length) throw new Error('CFB contains no streams');
  return streams;
}

/* ─────────────────────────────────────────────────────────────────
   10. BIFF8 record reader (spec T3.2; RK decode)
   ───────────────────────────────────────────────────────────────── */

/** Decode a BIFF8 RK value (bit0 fx100, bit1 integer-in-high-30). */
export function rkDecode(rk) {
  const u = rk >>> 0;
  let n;
  if (u & 2) {
    n = u >>> 2;
    if (n >= 0x20000000) n -= 0x40000000;
  } else {
    const dv = new DataView(new ArrayBuffer(8));
    dv.setUint32(4, (u & 0xFFFFFFFC) >>> 0, true);
    dv.setUint32(0, 0, true);
    n = dv.getFloat64(0, true);
  }
  if (u & 1) n /= 100;
  return n;
}

function* recordIter(buf, start, end) {
  const view = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  let off = start;
  const stop = end === undefined ? buf.length : end;
  while (off + 4 <= stop) {
    const rid = view.getUint16(off, true);
    const rlen = view.getUint16(off + 2, true);
    if (rid === 0 && rlen === 0) break;
    yield [rid, buf.subarray(off + 4, off + 4 + rlen), off];
    off += 4 + rlen;
  }
}

function xlStr(data, off, cch, grbit) {
  if (grbit & 0x01) {
    const bytes = data.subarray(off, off + cch * 2);
    return [new TextDecoder('utf-16le').decode(bytes), off + cch * 2];
  }
  const bytes = data.subarray(off, off + cch);
  let out = '';
  for (let i = 0; i < bytes.length; i++) out += String.fromCharCode(bytes[i]);
  return [out, off + cch];
}

function setCell(grid, rw, col, val) {
  while (grid.length <= rw) grid.push([]);
  const row = grid[rw];
  while (row.length <= col) row.push('');
  row[col] = val;
}

export function readBiff8(workbook) {
  const u8 = toBytes(workbook);
  const sheets = [];
  const strings = [];
  const boundsheets = [];
  for (const [rid, data] of recordIter(u8, 0)) {
    const dv = new DataView(data.buffer, data.byteOffset, data.byteLength);
    if (rid === 0x0085) { // BOUNDSHEET
      const pos = dv.getUint32(0, true);
      const cch = data[6];
      const grbit = data[7];
      const [name] = xlStr(data, 8, cch, grbit);
      boundsheets.push([name, pos]);
    } else if (rid === 0x00FC) { // SST (no CONTINUE in our corpus; tolerate truncation)
      const unique = dv.getUint32(4, true);
      let off = 8;
      try {
        for (let i = 0; i < unique; i++) {
          if (off + 3 > data.length) throw new Error('SST truncated');
          const cch = data[off] | (data[off + 1] << 8);
          const grbit = data[off + 2];
          const [text, next] = xlStr(data, off + 3, cch, grbit);
          strings.push(text);
          off = next;
        }
      } catch (e) {
        throw new Error('SST record unreadable: ' + e.message);
      }
    } else if (rid === 0x000A) {
      break;
    }
  }
  if (!boundsheets.length) throw new Error('no BOUNDSHEET records — no worksheet in workbook stream');

  for (const [name, pos] of boundsheets) {
    const grid = [];
    let sawCells = false;
    for (const [rid, data] of recordIter(u8, pos)) {
      const dv = new DataView(data.buffer, data.byteOffset, data.byteLength);
      if (rid === 0x000A) break;
      try {
        let rw, col, val;
        if (rid === 0x00FD && data.length >= 10) { // LABELSST
          rw = dv.getUint16(0, true); col = dv.getUint16(2, true);
          const isst = dv.getUint32(6, true);
          val = isst < strings.length ? strings[isst] : '';
        } else if (rid === 0x0204 && data.length >= 9) { // LABEL
          rw = dv.getUint16(0, true); col = dv.getUint16(2, true);
          const cch = dv.getUint16(6, true);
          const grbit = data[8];
          const [text] = xlStr(data, 9, cch, grbit);
          val = text;
        } else if (rid === 0x0203 && data.length >= 14) { // NUMBER
          rw = dv.getUint16(0, true); col = dv.getUint16(2, true);
          val = dv.getFloat64(6, true);
        } else if (rid === 0x027E && data.length >= 10) { // RK
          rw = dv.getUint16(0, true); col = dv.getUint16(2, true);
          val = rkDecode(dv.getUint32(6, true));
        } else if (rid === 0x00BD && data.length >= 8) { // MULRK
          rw = dv.getUint16(0, true);
          const col0 = dv.getUint16(2, true);
          const ncols = Math.floor((data.length - 6) / 6);
          for (let k = 0; k < ncols; k++) {
            setCell(grid, rw, col0 + k, rkDecode(dv.getUint32(4 + k * 6 + 2, true)));
          }
          sawCells = true;
          continue;
        } else if (rid === 0x0006 && data.length >= 20) { // FORMULA (cached result)
          rw = dv.getUint16(0, true); col = dv.getUint16(2, true);
          if (data[12] === 0xFF && data[13] === 0xFF) continue; // special (string/bool/error)
          val = dv.getFloat64(6, true);
        } else {
          continue;
        }
        setCell(grid, rw, col, val);
        sawCells = true;
      } catch (e) {
        throw new Error(`BIFF record 0x${rid.toString(16).padStart(4, '0')} unreadable: ${e.message}`);
      }
    }
    if (sawCells && grid.some(row => row.some(c => s(c)))) sheets.push({ name, grid });
  }
  if (!sheets.length) throw new Error('BIFF sheets contain no cells');
  return sheets;
}

/* ─────────────────────────────────────────────────────────────────
   11. XLSX grid reader (stdlib-free — same regexes as Python mirror)
   ───────────────────────────────────────────────────────────────── */

function xmlUnescape(str) {
  return str.replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, '&');
}

function colToIdx(ref) {
  const m = /^[A-Z]+/.exec(ref || '');
  if (!m) return 0;
  let n = 0;
  for (const ch of m[0]) n = n * 26 + (ch.charCodeAt(0) - 64);
  return n - 1;
}

export function readXlsxGrids(files) {
  // files: {entryName: text} — decoded ZIP contents
  const names = Object.keys(files);
  const strings = [];
  if (files['xl/sharedStrings.xml']) {
    const ss = files['xl/sharedStrings.xml'];
    const siRe = /<si>([\s\S]*?)<\/si>/g;
    let si;
    while ((si = siRe.exec(ss)) !== null) {
      const texts = [];
      const tRe = /<t[^>]*>([\s\S]*?)<\/t>/g;
      let t;
      while ((t = tRe.exec(si[1])) !== null) texts.push(t[1]);
      strings.push(texts.join(''));
    }
  }
  const sheetFiles = names.filter(n => /^xl\/worksheets\/sheet\d+\.xml$/.test(n));
  sheetFiles.sort((a, b) => parseInt(a.match(/(\d+)/)[1], 10) - parseInt(b.match(/(\d+)/)[1], 10));
  const grids = [];
  for (const sf of sheetFiles) {
    const xml = files[sf];
    const grid = [];
    const rowRe = /<row[^>]*>([\s\S]*?)<\/row>/g;
    let rm;
    while ((rm = rowRe.exec(xml)) !== null) {
      const row = [];
      const cellRe = /<c\s+r="([A-Z]+)\d+"(?:\s+t="(\w+)")?[^>]*?(?:\/>|>([\s\S]*?)<\/c>)/g;
      let cm;
      while ((cm = cellRe.exec(rm[1])) !== null) {
        const ref = cm[1];
        const ctype = cm[2] || 'n';
        const body = cm[3] || '';
        const idx = colToIdx(ref);
        let val = '';
        if (ctype === 'inlineStr') {
          const t = /<t[^>]*>([\s\S]*?)<\/t>/.exec(body);
          val = t ? xmlUnescape(t[1]) : '';
        } else if (ctype === 'str') {
          const v = /<v>([\s\S]*?)<\/v>/.exec(body);
          val = v ? xmlUnescape(v[1]) : '';
        } else {
          const v = /<v>([\s\S]*?)<\/v>/.exec(body);
          if (v) {
            const raw = xmlUnescape(v[1]);
            if (ctype === 's') {
              val = /^\d+$/.test(raw) ? (strings[parseInt(raw, 10)] ?? '') : '';
            } else {
              const n = num(raw);
              val = n === null ? raw : n;
            }
          }
        }
        while (row.length <= idx) row.push('');
        row[idx] = val;
      }
      grid.push(row);
    }
    if (grid.length) grids.push({ name: sf.split('/').pop(), grid });
  }
  if (!grids.length) throw new Error('XLSX contains no worksheets');
  return grids;
}

/* ─────────────────────────────────────────────────────────────────
   12. ZIP helpers (own central-directory walk — engine untouched)
   ───────────────────────────────────────────────────────────────── */

function findCentralDirectory(view) {
  for (let i = view.byteLength - 22; i >= 0; i--) {
    if (view.getUint32(i, true) === 0x06054b50) return view.getUint32(i + 16, true);
  }
  return -1;
}

/** → {name: uncompressedSize} for every central-directory entry. */
export function listZipEntries(input) {
  const u8 = toBytes(input);
  const view = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  const out = {};
  const cdOffset = findCentralDirectory(view);
  if (cdOffset < 0) return out;
  let offset = cdOffset;
  while (offset < u8.length - 4) {
    const sig = view.getUint32(offset, true);
    if (sig !== 0x02014b50) break;
    const nameLen = view.getUint16(offset + 28, true);
    const extraLen = view.getUint16(offset + 30, true);
    const commentLen = view.getUint16(offset + 32, true);
    const name = new TextDecoder().decode(u8.subarray(offset + 46, offset + 46 + nameLen));
    out[name] = view.getUint32(offset + 24, true);
    offset += 46 + nameLen + extraLen + commentLen;
  }
  return out;
}

let _hasNativeDeflateRaw;
function nativeDeflateRawSupported() {
  if (_hasNativeDeflateRaw === undefined) {
    try { new DecompressionStream('deflate-raw'); _hasNativeDeflateRaw = true; }
    catch (e) { _hasNativeDeflateRaw = false; }  // e.g. node < 20
  }
  return _hasNativeDeflateRaw;
}

async function inflateRawNative(data) {
  const ds = new DecompressionStream('deflate-raw');
  const writer = ds.writable.getWriter();
  writer.write(data);
  writer.close();
  const reader = ds.readable.getReader();
  const chunks = [];
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
  }
  const total = chunks.reduce((a, c) => a + c.length, 0);
  const result = new Uint8Array(total);
  let off = 0;
  for (const c of chunks) { result.set(c, off); off += c.length; }
  return result;
}

/* Pure-JS DEFLATE (RFC 1951) decoder — fallback when DecompressionStream
   lacks 'deflate-raw' (node < 20). Fixed/dynamic Huffman + stored blocks. */
const _LBASE = [3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35,
  43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258];
const _LEXT = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4,
  4, 4, 4, 5, 5, 5, 5, 0];
const _DBASE = [1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257,
  385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577];
const _DEXT = [0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9,
  9, 10, 10, 11, 11, 12, 12, 13, 13];

function inflateRawJS(data) {
  let pos = 0, bitBuf = 0, bitCnt = 0;
  let out = new Uint8Array(65536), outLen = 0;

  function bits(n) {
    while (bitCnt < n) {
      if (pos >= data.length) throw new Error('inflate: unexpected end of input');
      bitBuf |= data[pos++] << bitCnt;
      bitCnt += 8;
    }
    const v = bitBuf & ((1 << n) - 1);
    bitBuf >>>= n;
    bitCnt -= n;
    return v;
  }

  function buildTree(lengths) {
    let maxBits = 0;
    for (const l of lengths) if (l > maxBits) maxBits = l;
    const blCount = new Array(maxBits + 1).fill(0);
    for (const l of lengths) if (l) blCount[l]++;
    const nextCode = new Array(maxBits + 1).fill(0);
    let code = 0;
    for (let b = 1; b <= maxBits; b++) {
      code = (code + blCount[b - 1]) << 1;
      nextCode[b] = code;
    }
    const map = new Map();  // (len<<16)|code → symbol
    for (let sym = 0; sym < lengths.length; sym++) {
      const l = lengths[sym];
      if (l) map.set((l << 16) | nextCode[l]++, sym);
    }
    return { map, maxBits };
  }

  function decodeSym(tree) {
    let code = 0;
    for (let len = 1; len <= tree.maxBits; len++) {
      code = (code << 1) | bits(1);
      const s = tree.map.get((len << 16) | code);
      if (s !== undefined) return s;
    }
    throw new Error('inflate: invalid Huffman code');
  }

  let litTree = null, distTree = null;

  function inflateBlock() {
    for (;;) {
      const sym = decodeSym(litTree);
      if (sym < 256) {
        if (outLen >= out.length) {
          const n = new Uint8Array(out.length * 2);
          n.set(out);
          out = n;
        }
        out[outLen++] = sym;
      } else if (sym === 256) {
        return;
      } else {
        const li = sym - 257;
        if (li >= _LBASE.length) throw new Error('inflate: bad length symbol');
        const length = _LBASE[li] + bits(_LEXT[li]);
        const dsym = decodeSym(distTree);
        if (dsym >= _DBASE.length) throw new Error('inflate: bad distance symbol');
        const distance = _DBASE[dsym] + bits(_DEXT[dsym]);
        const start = outLen - distance;
        if (start < 0) throw new Error('inflate: distance before output start');
        for (let i = 0; i < length; i++) {
          if (outLen >= out.length) {
            const n = new Uint8Array(out.length * 2);
            n.set(out);
            out = n;
          }
          out[outLen++] = out[start + i];
        }
      }
    }
  }

  for (;;) {
    const bfinal = bits(1);
    const btype = bits(2);
    if (btype === 0) {
      bitBuf = 0; bitCnt = 0;  // align to byte boundary
      if (pos + 4 > data.length) throw new Error('inflate: truncated stored block');
      const len = data[pos] | (data[pos + 1] << 8);
      pos += 4;
      if (pos + len > data.length) throw new Error('inflate: truncated stored data');
      if (outLen + len > out.length) {
        let cap = out.length;
        while (outLen + len > cap) cap *= 2;
        const n = new Uint8Array(cap);
        n.set(out);
        out = n;
      }
      out.set(data.subarray(pos, pos + len), outLen);
      outLen += len;
      pos += len;
    } else if (btype === 1) {
      const lit = new Array(288);
      for (let i = 0; i < 144; i++) lit[i] = 8;
      for (let i = 144; i < 256; i++) lit[i] = 9;
      for (let i = 256; i < 280; i++) lit[i] = 7;
      for (let i = 280; i < 288; i++) lit[i] = 8;
      litTree = buildTree(lit);
      distTree = buildTree(new Array(30).fill(5));
      inflateBlock();
    } else if (btype === 2) {
      const hlit = bits(5) + 257;
      const hdist = bits(5) + 1;
      const hclen = bits(4) + 4;
      const order = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15];
      const clLen = new Array(19).fill(0);
      for (let i = 0; i < hclen; i++) clLen[order[i]] = bits(3);
      const clTree = buildTree(clLen);
      const all = new Array(hlit + hdist).fill(0);
      for (let i = 0; i < all.length;) {
        const s = decodeSym(clTree);
        if (s < 16) all[i++] = s;
        else if (s === 16) {
          if (i === 0) throw new Error('inflate: repeat with no previous code');
          const prev = all[i - 1];
          let r = 3 + bits(2);
          while (r-- > 0 && i < all.length) all[i++] = prev;
        } else if (s === 17) {
          let r = 3 + bits(3);
          while (r-- > 0 && i < all.length) all[i++] = 0;
        } else {
          let r = 11 + bits(7);
          while (r-- > 0 && i < all.length) all[i++] = 0;
        }
      }
      litTree = buildTree(all.slice(0, hlit));
      distTree = buildTree(all.slice(hlit));
      inflateBlock();
    } else {
      throw new Error('inflate: reserved block type');
    }
    if (bfinal) break;
  }
  return out.subarray(0, outLen);
}

async function inflateRaw(data) {
  if (nativeDeflateRawSupported()) return inflateRawNative(data);
  return inflateRawJS(data);
}

/** Read ONE entry's decoded text (stored or deflate), sizes from central dir. */
export async function readZipEntry(input, wantName) {
  const u8 = toBytes(input);
  const view = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  const cdOffset = findCentralDirectory(view);
  if (cdOffset < 0) throw new Error('Not a valid ZIP file');
  let offset = cdOffset;
  while (offset < u8.length - 4) {
    const sig = view.getUint32(offset, true);
    if (sig !== 0x02014b50) break;
    const method = view.getUint16(offset + 10, true);
    const compressedSize = view.getUint32(offset + 20, true);
    const nameLen = view.getUint16(offset + 28, true);
    const extraLen = view.getUint16(offset + 30, true);
    const commentLen = view.getUint16(offset + 32, true);
    const localHeaderOffset = view.getUint32(offset + 42, true);
    const name = new TextDecoder().decode(u8.subarray(offset + 46, offset + 46 + nameLen));
    if (name === wantName) {
      const localSig = view.getUint32(localHeaderOffset, true);
      if (localSig !== 0x04034b50) throw new Error(`bad local header for ${name}`);
      const localNameLen = view.getUint16(localHeaderOffset + 26, true);
      const localExtraLen = view.getUint16(localHeaderOffset + 28, true);
      const dataOffset = localHeaderOffset + 30 + localNameLen + localExtraLen;
      if (method === 0) {
        return new TextDecoder().decode(u8.subarray(dataOffset, dataOffset + compressedSize));
      }
      if (method === 8) {
        const compressed = u8.subarray(dataOffset, dataOffset + compressedSize);
        return new TextDecoder().decode(await inflateRaw(compressed));
      }
      throw new Error(`unsupported ZIP method ${method} for ${name}`);
    }
    offset += 46 + nameLen + extraLen + commentLen;
  }
  throw new Error(`ZIP entry not found: ${wantName}`);
}

/* ─────────────────────────────────────────────────────────────────
   13. Format doctor + Rotor-Gene guided card
   ───────────────────────────────────────────────────────────────── */

function printableSnippet(u8, n) {
  const lim = Math.min((u8 && u8.length) || 0, n || 72);
  let out = '';
  for (let i = 0; i < lim; i++) {
    out += (u8[i] >= 32 && u8[i] < 127) ? String.fromCharCode(u8[i]) : '·';
  }
  return out;
}

export function diagnose(input, text, fileName) {
  const u8 = input === null || input === undefined ? null : toBytes(input);
  const kind = u8 ? sniff(u8) : 'text';
  const ext = extOf(fileName) || '(none)';
  const findings = [
    `Container (magic bytes): ${kind}`,
    `Size: ${u8 ? u8.length : 0} bytes`,
    `Extension: .${ext}`,
    `First bytes: ${u8 ? printableSnippet(u8) : '(empty)'}`,
  ];
  const guidance = [];
  let title;
  if (kind === 'gzip') {
    title = 'Compressed (gzip) container';
    findings.push('This file is gzip-compressed, not a data table');
    guidance.push('Extract the archive first, then drop the inner file here.');
  } else if (kind === 'binary') {
    title = 'Binary payload — not a recognized container';
    let nul = 0;
    if (u8) for (let i = 0; i < Math.min(u8.length, 1000); i++) if (u8[i] === 0) nul++;
    findings.push(`NUL bytes in first 1 KB: ${nul} (not text)`);
    guidance.push('Content is binary and is neither ZIP, OLE2, gzip nor text — no data table can be read from these bytes as-is.');
    if (ROTOR_EXTS.includes(ext)) {
      guidance.push('This extension is in the Rotor-Gene family — see the family export guidance for the CSV/RDML export menu.');
    }
  } else if (kind === 'zip') {
    title = 'ZIP archive without readable data files';
    guidance.push('Extract the archive and drop the inner .csv/.tsv/.txt/.rdml/.xlsx file directly.');
  } else {
    title = 'No recognizable data table in this text';
    findings.push(`Decoded ${text ? text.length : 0} characters of text`);
    if (text && text.trim()) {
      const first = text.trim().split('\n')[0].slice(0, 72);
      findings.push(`First line: ${first}`);
      const delim = detectDelimiter(text);
      const fields = splitLine(text.trim().split('\n')[0], delim).length;
      findings.push(`Detected delimiter: ${delim === '\t' ? 'tab' : delim} (${fields} fields on first line)`);
      const rows = splitRows(text, delim);
      const kinds = new Set();
      for (const row of rows.slice(0, 10)) {
        for (const k of Object.values(classifyHeader(row))) kinds.add(k);
      }
      if (kinds.size) findings.push(`Recognized column names: ${Array.from(kinds).sort().join(', ')}`);
      else findings.push('No recognized column names in the first rows');
    }
    guidance.push('Supported header vocabulary: Well/Position/Chamber · Sample/Specimen · Target/Assay · Dye/Reporter/Channel · Cq/Ct · Tm · Cycle · Signal/Fluorescence/Value (any language spelling of these works — the reasoner matches column names, not brands).');
  }
  return {
    title,
    findings,
    guidance,
    supported: SUPPORTED_FORMATS.slice(),
  };
}

export function rotorGuided(fileName, probe) {
  const ext = extOf(fileName);
  return {
    title: 'Rotor-Gene-family file — structure read, data not in a table',
    findings: [
      `Extension .${ext} is in the Rotor-Gene family (.qbd/.qbg/.qbt/.rgd/.rgx/.rex)`,
      `Probed content first: ${probe}`,
      'These files are written by Corbett Rotor-Gene Q software and the Genes2Me machines that ship it (OnePCR, RapiCycler) — one file family, several brands. The instrument name inside is metadata, not a format.',
    ],
    guidance: [
      'The payload here is proprietary binary — no data table could be read from it, so there is nothing to plot rather than guess at it.',
      'Export a data table from your instrument software: File → Export (or Save As) → CSV/Excel, or RDML if offered — in OnePCR/RapiCycler choose the export menu, not a print-to-file.',
      'Drop that export here — CSV, TSV, TXT, XLS or XLSX from any machine is read directly by the layout reasoner. No manual reformatting, no data retyping.',
    ],
    supported: SUPPORTED_FORMATS.slice(),
  };
}

function formatError(doctor, message) {
  return new FormatError(message || doctor.title || 'format error', doctor);
}

/* ─────────────────────────────────────────────────────────────────
   14. Text dispatch: fast paths → reasoner → doctor
   ───────────────────────────────────────────────────────────────── */

function strictTemplateHeader(text) {
  const lines = String(text || '').split('\n').slice(0, 5);
  return lines.some(l => /well[,\t].*sample/i.test(l))
    && lines.some(l => /target/i.test(l))
    && lines.some(l => /channel/i.test(l));
}

/** Paste/upload text → canonical Run (fast paths → reasoner → FormatError). */
export function parseUniversalText(text, fileName) {
  const t = String(text || '').trim();
  if (!t) throw formatError(diagnose(null, text, fileName), 'Empty file — nothing to read');
  const fmt = detectFormat(text, fileName);
  if (fmt === 'rdml') {
    let run;
    try {
      run = parseRdml(text, fileName);
    } catch (e) {
      throw formatError({
        title: 'RDML parse failed',
        findings: [
          `First line: ${t.split('\n')[0].slice(0, 72)}`,
          `Parse error: ${e.message}`,
          'RDML structure expected: <rdml> → <experiment> → <run> → <react>.',
        ],
        guidance: ['Re-export as RDML 1.2 from your instrument software, or export CSV and drop that instead.'],
        supported: SUPPORTED_FORMATS.slice(),
      });
    }
    markCqOnly(run);
    attachDetection(run, 'rdml', 0.98, ['RDML XML document (<rdml> root)']);
    return run;
  }
  if (fmt === 'cfx_csv') {
    const run = parseCfxCsv(text, fileName);
    markCqOnly(run);
    attachDetection(run, 'cfx_csv', 0.9, ['CFX-style table (header fingerprints matched)']);
    return run;
  }
  if (fmt === 'template') {
    const run = parseTemplate(text, fileName);
    markCqOnly(run);
    attachDetection(run, 'template', 0.95, ['Template header: Well + Sample + Target + Channel']);
    return run;
  }
  const delim = detectDelimiter(text);
  const rows = splitRows(text, delim);
  const run = reasonRows(rows, fileName, 'universal');
  if (run) {
    if (delim === ';') run.detection.evidence.push("Detected ';' delimiter");
    else if (delim === '\t') run.detection.evidence.push('Detected tab delimiter');
    return run;
  }
  throw formatError(diagnose(textToBytes(text), text, fileName));
}

function textToBytes(text) {
  return new TextEncoder().encode(String(text || ''));
}

/* ─────────────────────────────────────────────────────────────────
   15. Master entry: sniff → dispatch
   ───────────────────────────────────────────────────────────────── */

function doctorOle(sheets) {
  return {
    title: 'OLE2 document read, but no recognizable data table',
    findings: [
      `Compound document parsed; ${sheets.length} worksheet(s) found: ${sheets.map(x => x.name || '?').join(', ')}`,
      'No header row matched the known column vocabulary.',
    ],
    guidance: ['Open the sheet in Excel/Sheets and re-save as CSV, or check the header row spelling — Well/Sample/Target/Cq/Cycle columns are recognized automatically.'],
    supported: SUPPORTED_FORMATS.slice(),
  };
}

function doctorOleError(err) {
  return {
    title: 'OLE2/BIFF document unreadable',
    findings: [
      'Container: OLE2 compound document (magic bytes)',
      `Reader stopped at: ${err.message || err}`,
      'BIFF record classes understood: BOF, BOUNDSHEET, SST, LABEL, LABELSST, NUMBER, RK, MULRK, FORMULA(cached numeric).',
    ],
    guidance: ['Re-save from Excel as .xlsx or CSV — the data table itself is portable; only this container’s record mix was not.'],
    supported: SUPPORTED_FORMATS.slice(),
  };
}

function gridToCsvText(grid) {
  return grid.map(row => row.map((c) => {
    let str = s(c);
    if (str.includes(',') || str.includes('"')) str = '"' + str.replace(/"/g, '""') + '"';
    return str;
  }).join(',')).join('\n');
}

async function parseZip(fileName, u8) {
  const ext = extOf(fileName);
  let entries;
  try {
    entries = listZipEntries(u8);
    if (!Object.keys(entries).length) throw new Error('empty central directory');
  } catch (e) {
    throw formatError({
      title: 'ZIP archive unreadable',
      findings: [String(e.message || e)],
      guidance: ['The file starts with ZIP magic bytes but the central directory cannot be read — it may be truncated. Re-download or re-export it.'],
      supported: SUPPORTED_FORMATS.slice(),
    });
  }
  const names = Object.keys(entries);
  const sheetSuffix = n => `${n} sheet${n === 1 ? '' : 's'}`;

  // 1) XLSX
  if (entries['xl/workbook.xml'] !== undefined) {
    try {
      const files = {};
      for (const n of names) {
        if (/^xl\/worksheets\/sheet\d+\.xml$/.test(n) || n === 'xl/sharedStrings.xml') {
          files[n] = await readZipEntry(u8, n);
        }
      }
      const grids = readXlsxGrids(files);
      const text = gridToCsvText(grids[0].grid);
      if (strictTemplateHeader(text)) {
        const run = parseTemplate(text, fileName);
        run.meta.sourceFormat = 'xlsx';
        markCqOnly(run);
        attachDetection(run, 'xlsx', 0.95,
          [`ZIP container → XLSX workbook (${sheetSuffix(grids.length)}, strict template header)`]);
        return run;
      }
      const run = reasonGrids(grids, fileName, 'xlsx');
      if (run) {
        run.meta.sourceFormat = 'xlsx';
        run.detection.format = 'xlsx';
        run.detection.evidence.unshift(
          `ZIP container → XLSX workbook (${sheetSuffix(grids.length)}, layout reasoner)`);
        return run;
      }
    } catch (e) {
      if (e instanceof FormatError) throw e;
      throw formatError({
        title: 'XLSX workbook unreadable',
        findings: [String(e.message || e)],
        guidance: ['Re-save the sheet as CSV and drop that file here.'],
        supported: SUPPORTED_FORMATS.slice(),
      });
    }
  }

  // 2) RDML inside
  for (const n of names) {
    const low = n.toLowerCase();
    if (!(low.endsWith('.rdml') || (low.endsWith('.xml') && !low.includes('macosx')))) continue;
    let inner;
    try { inner = await readZipEntry(u8, n); } catch (e) { continue; }
    if (!inner.includes('<rdml')) continue;
    let run;
    try { run = parseRdml(inner, n); } catch (e) { continue; }
    run.meta.sourceFormat = 'rdml';
    markCqOnly(run);
    attachDetection(run, 'rdml', 0.96, [`ZIP container → RDML entry ${n}`]);
    return run;
  }

  // 3) deep probe: inner .csv/.tsv/.txt ≤ 1 MB
  for (const n of names.slice().sort()) {
    const low = n.toLowerCase();
    if (low.includes('macosx') || low.endsWith('/')) continue;
    if (!low.endsWith('.csv') && !low.endsWith('.tsv') && !low.endsWith('.txt')) continue;
    if (entries[n] > 1_000_000) continue;
    let inner;
    try { inner = await readZipEntry(u8, n); } catch (e) { continue; }
    let run;
    try { run = parseUniversalText(inner, n); } catch (e) { continue; }
    run.detection.evidence.unshift(`ZIP deep-probe → inner data file ${n}`);
    return run;
  }

  if (ROTOR_EXTS.includes(ext)) {
    throw formatError(rotorGuided(fileName, 'ZIP archive (wrapped) — no readable data tables inside'));
  }
  throw formatError(diagnose(u8, null, fileName));
}

/**
 * Master entry (mirror of tests/universal_mirror.parse_file_universal).
 * @param {string} fileName — original file name (evidence only, never gating)
 * @param {ArrayBuffer|Uint8Array} buffer — raw file bytes
 * @returns {Promise<object>} canonical Run
 * @throws {FormatError} with `.doctor` card when nothing matches
 */
export async function parseFileUniversal(fileName, buffer) {
  const u8 = toBytes(buffer);
  const kind = sniff(u8);
  const ext = extOf(fileName);

  if (kind === 'ole') {
    try {
      const streams = readCfb(u8);
      const key = ('Workbook' in streams) ? 'Workbook'
        : ('Book' in streams) ? 'Book' : Object.keys(streams)[0];
      const sheets = readBiff8(streams[key]);
      const run = reasonGrids(sheets, fileName, 'xls');
      if (!run) throw formatError(doctorOle(sheets));
      run.meta.sourceFormat = 'xls';
      run.detection.format = 'xls-biff8';
      run.detection.evidence.unshift(
        `OLE2 compound document → BIFF8 worksheet read (${sheetSuffixCount(sheets.length)})`);
      run.detection.confidence = Math.max(run.detection.confidence, 0.9);
      return run;
    } catch (e) {
      if (e instanceof FormatError) throw e;
      throw formatError(doctorOleError(e));
    }
  }

  if (kind === 'zip') return parseZip(fileName, u8);

  if (kind === 'gzip') throw formatError(diagnose(u8, null, fileName));

  if (kind === 'binary') {
    if (ROTOR_EXTS.includes(ext)) {
      throw formatError(rotorGuided(fileName, 'proprietary binary payload (not ZIP/OLE2/gzip/text)'));
    }
    throw formatError(diagnose(u8, null, fileName));
  }

  // text container → fast paths → reasoner → doctor
  const text = decodeText(u8);
  let run;
  try {
    run = parseUniversalText(text, fileName);
  } catch (e) {
    if (e instanceof FormatError) throw e;
    throw formatError(diagnose(u8, text, fileName));
  }
  if (ext === 'xls' || ext === 'xlsx' || ext === 'qbd' || ext === 'qbg') {
    run.detection.evidence.push(
      `Text container despite .${ext} extension — parsed by content, not by name`);
  }
  return run;
}

function sheetSuffixCount(n) {
  return `${n} sheet${n === 1 ? '' : 's'}`;
}
