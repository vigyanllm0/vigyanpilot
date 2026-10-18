/**
 * qpcr-engine.js — PURE: parsers → canonical model → analysis → QC.
 * Zero DOM, zero dependencies. Testable. Python-mirrorable.
 *
 * Canonical Data Model (the contract every module builds against):
 *
 * Run {
 *   meta: { fileName, sourceFormat, instrument?, runDate?, chemistry? }
 *   channels: [{ id, canonical: FAM|HEX|ROX|CY5|CY55, label, aliases[] }]
 *   targets:  [{ id, name, channelId, isReference? }]
 *   samples:  [{ id, name, type: unknown|standard|ntc|control, quantity? }]
 *   wells: [{
 *     id, row, col, layout: 96|384|strip|rotor, position,
 *     sampleId, targetId, channelId,
 *     cq?, cqSD?,            // instrument-reported (v1 never re-computes)
 *     tm?, tmPeaks[],
 *     amplification: Float32Array,     // FRET per cycle
 *     melt?: { temps[], fluores[] }
 *   }]
 * }
 * Analysis {
 *   standardCurves: { per target: slope, intercept, r2, efficiencyPct }
 *   expression:     { per sample×target: dCq, ddCq, fold, foldSD, method }
 *   qc:             { per well + per run: flags[] }
 * }
 */

/* ───────────────────────────────────────────────────────────────
   1. Channel canonicalization
   ─────────────────────────────────────────────────────────────── */
const CHANNEL_ALIASES = {
  FAM:     ['FAM', 'SYBR', 'SYBR GREEN', 'SYBR GREEN I', 'SYBRGREEN', 'GREEN', 'EVA GREEN', 'EVAGREEN', 'LC GREEN', 'LCGREEN'],
  HEX:     ['HEX', 'VIC', 'TET', 'JOE', 'FAM', 'CAL GOLD 540', 'CALGOLD540'],
  ROX:     ['ROX', 'TEXAS RED', 'TEXASRED', 'TAMRA', 'CAL ORANGE 560', 'CALORANGE560'],
  CY5:     ['CY5', 'CY 5', 'QUASAR 670', 'QUASAR670', 'CY5 5', 'Cy5'],
  CY55:    ['CY5.5', 'CY55', 'CY 5.5', 'QUASAR 705', 'QUASAR705'],
};

/**
 * Canonicalize a raw channel name to one of FAM|HEX|ROX|CY5|CY55.
 * Returns null if no match.
 */
export function canonicalChannel(raw) {
  if (!raw) return null;
  const key = String(raw).trim().toUpperCase().replace(/[_\-]/g, ' ');
  for (const [canon, aliases] of Object.entries(CHANNEL_ALIASES)) {
    for (const a of aliases) {
      if (key === a.toUpperCase().replace(/[_\-]/g, ' ')) return canon;
    }
  }
  // substring fallback
  if (key.includes('FAM') || key.includes('SYBR')) return 'FAM';
  if (key.includes('HEX') || key.includes('VIC') || key.includes('TET') || key.includes('JOE')) return 'HEX';
  if (key.includes('ROX') || key.includes('TAMRA') || key.includes('TEXAS')) return 'ROX';
  if (key.includes('CY5.5') || key.includes('CY 5.5')) return 'CY55';
  if (key.includes('CY5') || key.includes('QUASAR')) return 'CY5';
  return null;
}

/* ───────────────────────────────────────────────────────────────
   2. Data model factories
   ─────────────────────────────────────────────────────────────── */

export function makeRun(meta) {
  return {
    meta: Object.assign({
      fileName: '',
      sourceFormat: 'unknown',
      instrument: null,
      runDate: null,
      chemistry: null,
    }, meta || {}),
    channels: [],
    targets: [],
    samples: [],
    wells: [],
  };
}

export function makeChannel(id, raw, canonical) {
  return { id, canonical: canonical || canonicalChannel(raw) || raw, label: raw || id, aliases: [] };
}

export function makeTarget(id, name, channelId, isReference) {
  return { id, name, channelId, isReference: !!isReference };
}

export function makeSample(id, name, type, quantity) {
  return { id, name, type: type || 'unknown', quantity: quantity != null ? quantity : null };
}

export function makeWell(id, row, col, layout) {
  return {
    id, row, col, layout: layout || '96', position: row * 12 + col,
    sampleId: null, targetId: null, channelId: null,
    cq: null, cqSD: null,
    tm: null, tmPeaks: [],
    amplification: new Float32Array(0),
    melt: null,
  };
}

export function makeAnalysis() {
  return { standardCurves: {}, expression: {}, qc: {} };
}

/* ───────────────────────────────────────────────────────────────
   3. Parsers
   ─────────────────────────────────────────────────────────────── */

/**
 * Auto-detect format from file content.
 * Returns one of: 'rdml', 'cfx_csv', 'template', 'unknown'
 */
export function detectFormat(text, fileName, buffer) {
  // Magic-byte sniffing (content-based, not extension-based)
  if (buffer && buffer.byteLength >= 4) {
    const view = new DataView(buffer);
    // ZIP container (PK\\x03\\x04)
    if (view.getUint8(0) === 0x50 && view.getUint8(1) === 0x4B && view.getUint8(2) === 0x03 && view.getUint8(3) === 0x04) {
      // Check inner contents
      try {
        // Quick check: does it contain xl/workbook.xml?
        const files = extractZipSync(buffer);
        if (files['xl/workbook.xml']) return 'xlsx';
        // Check for RDML in zip
        if (Object.keys(files).some(f => f.endsWith('.rdml') || f.endsWith('.xml'))) return 'zip-rdml';
        // Multiple data files → zip-batch
        const dataFiles = Object.keys(files).filter(f => /\\.(csv|tsv|rdml|xlsx|txt)$/i.test(f));
        if (dataFiles.length > 1) return 'zip-batch';
        if (dataFiles.length === 1) return detectFormat('', dataFiles[0]);
      } catch (e) {}
      return 'zip';
    }
    // OLE compound document (D0 CF 11 E0)
    if (view.getUint8(0) === 0xD0 && view.getUint8(1) === 0xCF && view.getUint8(2) === 0x11 && view.getUint8(3) === 0xE0) {
      return 'xls'; // legacy Excel (or possibly .qbg — spike needed)
    }
  }
  // Check file extension
  if (fileName) {
    const ext = fileName.toLowerCase().split('.').pop();
    if (ext === 'pcrd') return 'pcrd';
    if (ext === 'rdml') return 'rdml';
    if (ext === 'xlsx') return 'xlsx';
    if (ext === 'xls') return 'xls';
    if (ext === 'qbg') return 'qbg';
    if (ext === 'zip') return 'zip';
    if (ext === 'csv') {
      // Could be CFX or generic; fall through to content detection
    }
  }
  // Text-based detection
  const t = (text || '').trim();
  if (!t) return 'unknown';
  if (t.startsWith('<?xml') || t.startsWith('<rdml') || t.includes('<rdml')) return 'rdml';
  // First few lines are enough to identify a table header (case-insensitive, comma or tab)
  const headLines = t.split(/\r?\n/).slice(0, 5);
  const head = headLines.join('\n');
  const hasHead = (re) => headLines.some(l => re.test(l));
  // Template TSV/CSV: Well + Sample + Target + Channel (check FIRST — CFX has no Sample column)
  if (hasHead(/well[,\t].*sample/i) && hasHead(/target/i) && hasHead(/channel/i)) return 'template';
  // CFX-style summary table: Well + Fluor/Target (comma or tab delimited)
  if (hasHead(/well[,\t].*fluor/i) || hasHead(/well[,\t].*target/i)) return 'cfx_csv';
  // Sectioned CFX export (any case)
  if (/amplification data/i.test(t) && /well/i.test(head)) return 'cfx_csv';
  // Long-format per-cycle table: Well + Cycle + Value/Fluorescence/Signal header
  if (hasHead(/well/i) && hasHead(/cycle/i) && hasHead(/\bvalue\b|fluorescen|signal/i)) return 'cfx_csv';
  // Cq-first headers (QuantStudio style)
  if (hasHead(/cq[,\t].*well/i) || hasHead(/well[,\t].*cq/i)) return 'cfx_csv';
  return 'unknown';
}

/**
 * Parse RDML 1.2 XML → canonical Run.
 * RDML structure: <rdml> → <experiment> → <run> → <react> (wells)
 * Each react has: position, sample, target, data (amplification + cq)
 */
export function parseRdml(text, fileName) {
  const run = makeRun({ fileName: fileName || 'rdml', sourceFormat: 'rdml' });
  try {
    const getTag = (xml, tag) => {
      // Word-boundary safe: '<cq' must not match '<cqStartFluor'
      const b = tag + '(?=[\\s>])';
      // Handle self-closing tags with id attribute: <tag id="val"/>
      let m = xml.match(new RegExp('<' + b + '[^>]*?\\bid=["\']([^"\']+)["\']', 'i'));
      if (m) return m[1].trim();
      const re = new RegExp('<' + b + '[^>]*>([\\s\\S]*?)</' + tag + '>', 'i');
      m = xml.match(re);
      return m ? m[1].trim() : null;
    };
    const getAllTags = (xml, tag) => {
      const b = tag + '(?=[\\s>])';
      const re = new RegExp('<' + b + '[^>]*>([\\s\\S]*?)</' + tag + '>', 'gi');
      const results = [];
      let m;
      while ((m = re.exec(xml)) !== null) results.push(m[1].trim());
      return results;
    };
    // Nested block elements: returns inner content of each <tag ...>...</tag>
    const getAllBlocks = (xml, tag) => {
      const re = new RegExp('<' + tag + '\\b([^>]*)>([\\s\\S]*?)</' + tag + '>', 'gi');
      const results = [];
      let m;
      while ((m = re.exec(xml)) !== null) results.push(m[2].trim());
      return results;
    };

    const instrument = getTag(text, 'instrument');
    if (instrument) run.meta.instrument = instrument;
    const date = getTag(text, 'date') || getTag(text, 'runDate');
    if (date) run.meta.runDate = date;

    const targetsSeen = new Set();
    const samplesSeen = new Set();
    const channelsSeen = new Set();

    // Top-level sample definitions: <sample id="s1"><name>Sample 1</name></sample>
    const sampleNameById = {};
    const sampleDefRe = /<sample\s+id=["']([^"']+)["'][^>]*>([\s\S]*?)<\/sample>/gi;
    let sd;
    while ((sd = sampleDefRe.exec(text)) !== null) {
      if (sd[2].includes('<')) {
        const nm = getTag(sd[2], 'name');
        if (nm) sampleNameById[sd[1]] = nm;
      }
    }

    // Extract nested <dye> blocks with child data (multiplex: one block per dye/channel).
    // Plain <dye>FAM</dye> text values are NOT data blocks — skipped.
    const getDyeBlocks = (xml) => {
      const blocks = [];
      const re = /<dye\b([^>]*)>([\s\S]*?)<\/dye>/gi;
      let m;
      while ((m = re.exec(xml)) !== null) {
        const inner = m[2];
        if (!inner.includes('<')) continue;
        const idm = (m[1] || '').match(/\bid=["']([^"']+)["']/i);
        blocks.push({ id: idm ? idm[1] : '', xml: inner });
      }
      return blocks;
    };

    // Amplification extraction — supports:
    //   1. <adp><cyc>1</cyc><tmp>60</tmp><fluor>0.1</fluor></adp>  (standard RDML data points)
    //   2. <adp cyc="1" fluor="0.1"/>                               (attribute form)
    //   3. <ad cycle="1">0.1</ad>                                   (alternate instrument exports)
    //   4. <amplificationData>0.1 0.2 ...</amplificationData>       (flat text)
    const extractAmp = (scope) => {
      const adps = getAllBlocks(scope, 'adp');
      if (adps.length) {
        const pts = [];
        for (const a of adps) {
          const c = parseFloat(getTag(a, 'cyc'));
          const f = parseFloat(getTag(a, 'fluor'));
          if (isFinite(f)) pts.push({ c: isFinite(c) ? c : pts.length + 1, f });
        }
        if (pts.length) {
          pts.sort((p1, p2) => p1.c - p2.c);
          return new Float32Array(pts.map(p => p.f));
        }
      }
      // attribute-form self-closing adp
      const adpAttrRe = /<adp\s([^>]*?)\/>/gi;
      const attrPts = [];
      let am;
      while ((am = adpAttrRe.exec(scope)) !== null) {
        const cm = am[1].match(/\bcycle=["']([^"']+)["']/i) || am[1].match(/\bcyc=["']([^"']+)["']/i);
        const fm = am[1].match(/\bfluor=["']([^"']+)["']/i) || am[1].match(/\bvalue=["']([^"']+)["']/i);
        if (fm) {
          const f = parseFloat(fm[1]);
          if (isFinite(f)) attrPts.push({ c: cm ? parseFloat(cm[1]) : attrPts.length + 1, f });
        }
      }
      if (attrPts.length) {
        attrPts.sort((p1, p2) => p1.c - p2.c);
        return new Float32Array(attrPts.map(p => p.f));
      }
      // <ad cycle="N">value</ad>
      const adRe = /<ad\s([^>]*)>([\s\S]*?)<\/ad>/gi;
      const adPts = [];
      while ((am = adRe.exec(scope)) !== null) {
        const cm = am[1].match(/\bcycle=["']([^"']+)["']/i);
        const v = parseFloat(am[2].replace(/<[^>]+>/g, ''));
        if (isFinite(v)) adPts.push({ c: cm ? parseFloat(cm[1]) : adPts.length + 1, f: v });
      }
      if (adPts.length) {
        adPts.sort((p1, p2) => p1.c - p2.c);
        return new Float32Array(adPts.map(p => p.f));
      }
      // Flat text blob: <amplificationData>0.05 0.06 ...</amplificationData> (or bare-text <data>)
      const ampRaw = getTag(scope, 'amplificationData') || getTag(scope, 'data');
      if (ampRaw && !ampRaw.includes('<')) {
        const vals = ampRaw.split(/[\s,;]+/).map(Number).filter(v => !isNaN(v));
        if (vals.length) return new Float32Array(vals);
      }
      return new Float32Array(0);
    };

    // Melt extraction — supports:
    //   1. <mdp><tmp>60.0</tmp><fluor>1.51</fluor></mdp>  (standard RDML melt data points)
    //   2. <meltData>/<melt> containing temperature/fluorescence tags (flat/legacy)
    const extractMelt = (scope) => {
      const mdps = getAllBlocks(scope, 'mdp');
      if (mdps.length) {
        const temps = [], fluores = [];
        for (const m of mdps) {
          const t = parseFloat(getTag(m, 'tmp'));
          const f = parseFloat(getTag(m, 'fluor'));
          if (isFinite(t) && isFinite(f)) { temps.push(t); fluores.push(f); }
        }
        if (temps.length) return { temps, fluores };
      }
      const meltRaw = getTag(scope, 'meltData') || getTag(scope, 'melt');
      if (meltRaw) {
        const temps = getAllTags(meltRaw, 'temperature').concat(getAllTags(meltRaw, 'temp')).concat(getAllTags(meltRaw, 't')).map(Number).filter(v => isFinite(v));
        const fluores = getAllTags(meltRaw, 'fluorescence').concat(getAllTags(meltRaw, 'fluor')).concat(getAllTags(meltRaw, 'f')).map(Number).filter(v => isFinite(v));
        if (temps.length) return { temps, fluores };
      }
      return null;
    };

    // Build one well from a scope (a <dye> block for multiplex, else the whole <react>)
    const addWell = (pos, reactXml, scopeXml, dyeIdOverride) => {
      if (!pos) return;
      const { row, col } = parsePosition(pos, 96);

      const sampleIdRaw = getTag(reactXml, 'sample') || getTag(reactXml, 'sampleId') || 'Unknown';
      const sampleName = sampleNameById[sampleIdRaw] || sampleIdRaw;
      const targetName = getTag(scopeXml, 'target') || getTag(scopeXml, 'targetId') || 'Unknown';

      if (!samplesSeen.has(sampleName)) {
        samplesSeen.add(sampleName);
        run.samples.push(makeSample(run.samples.length, sampleName, guessSampleType(sampleName)));
      }
      if (!targetsSeen.has(targetName)) {
        targetsSeen.add(targetName);
        run.targets.push(makeTarget(run.targets.length, targetName, null, guessReference(targetName)));
      }
      const sampleId = run.samples.findIndex(s => s.name === sampleName);
      const targetId = run.targets.findIndex(t => t.name === targetName);

      const rawDye = (dyeIdOverride != null && dyeIdOverride !== '') ? dyeIdOverride
        : (getTag(scopeXml, 'dye') || getTag(scopeXml, 'fluor') || getTag(scopeXml, 'channel') || '');
      const canon = canonicalChannel(rawDye) || 'FAM';
      if (!channelsSeen.has(canon)) {
        channelsSeen.add(canon);
        run.channels.push(makeChannel(run.channels.length, rawDye, canon));
      }
      const channelId = run.channels.findIndex(c => c.canonical === canon);

      const cqRaw = getTag(scopeXml, 'cq') || getTag(scopeXml, 'Cq') || getTag(scopeXml, 'ct');
      const cq = cqRaw ? parseFloat(cqRaw) : null;
      const amp = extractAmp(scopeXml);
      const melt = extractMelt(scopeXml);
      const tmRaw = getTag(scopeXml, 'tm') || getTag(scopeXml, 'Tm');
      const tm = tmRaw ? parseFloat(tmRaw) : null;

      const well = makeWell(run.wells.length, row, col, '96');
      well.sampleId = sampleId;
      well.targetId = targetId;
      well.channelId = channelId;
      well.cq = isFinite(cq) ? cq : null;
      well.tm = isFinite(tm) ? tm : null;
      well.amplification = amp;
      well.melt = melt;
      run.wells.push(well);
    };

    // Find react elements: support both <react id="A1"> and <react><position>A1</position>
    const reacts = [];
    const reactRegex1 = /<react\s+id="([^"]+)"[^>]*>([\s\S]*?)<\/react>/gi;
    let rm;
    while ((rm = reactRegex1.exec(text)) !== null) {
      reacts.push({ id: rm[1].trim(), xml: rm[2].trim() });
    }
    if (reacts.length === 0) {
      const reactRegex2 = /<react[^>]*>([\s\S]*?)<\/react>/gi;
      while ((rm = reactRegex2.exec(text)) !== null) {
        const posMatch = rm[1].match(/<position[^>]*>(.*?)<\/position>/i);
        if (posMatch) reacts.push({ id: posMatch[1].trim(), xml: rm[1].trim() });
      }
    }
    for (const react of reacts) {
      const pos = react.id;
      const reactXml = react.xml;
      if (!pos) continue;
      const dyeBlocks = getDyeBlocks(reactXml);
      if (dyeBlocks.length) {
        for (const b of dyeBlocks) addWell(pos, reactXml, b.xml, b.id);
      } else {
        addWell(pos, reactXml, reactXml, null);
      }
    }

    if (run.channels.length === 0) {
      run.channels.push(makeChannel(0, 'FAM', 'FAM'));
    }
    for (const t of run.targets) {
      if (t.channelId == null) t.channelId = 0;
    }
  } catch (e) {
    throw new Error('RDML parse failed: ' + e.message);
  }
  return run;
}

// Quote-aware CSV line splitter
function splitCsvLine(line) {
  if (line.indexOf('"') === -1) return line.split(',').map(c => c.trim());
  const out = [];
  let cur = '';
  let inQ = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQ) {
      if (ch === '"') {
        if (line[i + 1] === '"') { cur += '"'; i++; }
        else inQ = false;
      } else cur += ch;
    } else {
      if (ch === '"') inQ = true;
      else if (ch === ',') { out.push(cur); cur = ''; }
      else cur += ch;
    }
  }
  out.push(cur);
  return out.map(c => c.trim());
}

export function parseCfxCsv(text, fileName) {
  const run = makeRun({ fileName: fileName || 'cfx_csv', sourceFormat: 'cfx_csv' });
  try {
    const lines = text.split(/\r?\n/).filter(l => l.trim());
    if (lines.length === 0) throw new Error('Empty file');

    // ── Section markers (CFX "Export to CSV" puts curves in separate sections) ──
    const markerIdx = (re) => lines.findIndex(l => re.test(l.replace(/^"|"$/g, '').trim()));
    const ampMarker = markerIdx(/^amplification data/i);
    const meltMarker = markerIdx(/^melt data/i);
    const markers = [ampMarker, meltMarker].filter(x => x >= 0);
    const summaryEnd = markers.length ? Math.min(...markers) : lines.length;

    // Find header row within summary region
    let headerIdx = -1;
    let headers = [];
    for (let i = 0; i < summaryEnd; i++) {
      const cols = splitCsvLine(lines[i]);
      if (cols.some(c => /well/i.test(c)) && cols.some(c => /fluor|channel|dye/i.test(c))) { headerIdx = i; headers = cols; break; }
      if (cols.some(c => /well/i.test(c)) && cols.some(c => /target/i.test(c))) { headerIdx = i; headers = cols; break; }
    }

    const targetsSeen = new Set();
    const samplesSeen = new Set();
    const channelsSeen = new Set();

    // Register sample/target/channel + push a well (shared by all paths)
    const pushWellMeta = (meta) => {
      const { row, col, rawFluor, sampleName, targetName, cq, cqSd, tm, amp, melt } = meta;
      if (!samplesSeen.has(sampleName)) {
        samplesSeen.add(sampleName);
        run.samples.push(makeSample(run.samples.length, sampleName, guessSampleType(sampleName)));
      }
      if (!targetsSeen.has(targetName)) {
        targetsSeen.add(targetName);
        run.targets.push(makeTarget(run.targets.length, targetName, null, guessReference(targetName)));
      }
      const canon = canonicalChannel(rawFluor) || 'FAM';
      if (!channelsSeen.has(canon)) {
        channelsSeen.add(canon);
        run.channels.push(makeChannel(run.channels.length, rawFluor, canon));
      }
      const sampleId = run.samples.findIndex(s => s.name === sampleName);
      const targetId = run.targets.findIndex(t => t.name === targetName);
      const channelId = run.channels.findIndex(c => c.canonical === canon);

      const well = makeWell(run.wells.length, row, col, '96');
      well.sampleId = sampleId;
      well.targetId = targetId;
      well.channelId = channelId;
      well.cq = isFinite(cq) ? cq : null;
      well.cqSD = isFinite(cqSd) ? cqSd : null;
      well.tm = isFinite(tm) ? tm : null;
      well.amplification = amp || new Float32Array(0);
      well.melt = melt || null;
      run.wells.push(well);
      return well;
    };

    const finish = () => {
      if (run.channels.length === 0) run.channels.push(makeChannel(0, 'FAM', 'FAM'));
      for (const t of run.targets) if (t.channelId == null) t.channelId = 0;
    };

    // Parse a section ("Amplification Data" / "Melt Data") → { "row,col,canon": [{x,v}] }
    const parseSection = (marker) => {
      if (marker < 0) return null;
      let si = marker + 1;
      if (si >= lines.length) return null;
      const sHeaders = splitCsvLine(lines[si]);
      const sIdx = (re) => sHeaders.findIndex(h => re.test(h));
      const sWell = sIdx(/well/i);
      if (sWell < 0) return null;
      const sFluor = sIdx(/fluor|channel|dye/i);
      const sCycle = sIdx(/cycle/i);
      const sTemp = sIdx(/temp|temperature/i);
      const sValue = sIdx(/^value$|fluorescen|signal|^data$/i);
      if (sValue < 0) return null;
      const byKey = {};
      for (let i = si + 1; i < lines.length; i++) {
        const raw = lines[i].trim();
        if (/^(amplification data|melt data)/i.test(raw.replace(/^"|"$/g, ''))) break; // next section
        const cols = splitCsvLine(lines[i]);
        if (cols.length < 2) continue;
        const wellName = (cols[sWell] || '').trim();
        if (!wellName) continue;
        const { row, col } = parsePosition(wellName, 96);
        const canon = sFluor >= 0 ? (canonicalChannel(cols[sFluor] || '') || 'FAM') : '';
        const v = parseFloat(cols[sValue]);
        if (!isFinite(v)) continue;
        let x = sTemp >= 0 ? parseFloat(cols[sTemp]) : (sCycle >= 0 ? parseFloat(cols[sCycle]) : NaN);
        if (!isFinite(x)) x = byKey[row + ',' + col + ',' + canon] ? byKey[row + ',' + col + ',' + canon].pts.length + 1 : 1;
        const key = row + ',' + col + ',' + canon;
        if (!byKey[key]) byKey[key] = { row, col, canon, pts: [] };
        byKey[key].pts.push({ x, v });
      }
      return byKey;
    };

    // Attach parsed section points to existing wells
    const attachSection = (byKey, kind) => {
      if (!byKey) return;
      for (const w of run.wells) {
        const ch = run.channels[w.channelId];
        const canon = ch ? ch.canonical : '';
        const entry = byKey[w.row + ',' + w.col + ',' + canon] || byKey[w.row + ',' + w.col + ','] || byKey[w.row + ',' + w.col + ',FAM'];
        if (!entry) continue;
        const pts = entry.pts.slice().sort((a, b) => a.x - b.x);
        if (kind === 'amp') {
          if (w.amplification.length === 0) w.amplification = new Float32Array(pts.map(p => p.v));
        } else {
          if (!w.melt) w.melt = { temps: pts.map(p => p.x), fluores: pts.map(p => p.v) };
        }
      }
    };

    // ── No summary header: pure section file (amplification-only or melt-only export) ──
    if (headerIdx === -1) {
      const section = parseSection(ampMarker >= 0 ? ampMarker : meltMarker);
      if (section) {
        for (const key of Object.keys(section)) {
          const e = section[key];
          const pts = e.pts.slice().sort((a, b) => a.x - b.x);
          const wellName = String.fromCharCode(65 + e.row) + (e.col + 1);
          pushWellMeta({
            row: e.row, col: e.col, rawFluor: e.canon,
            sampleName: wellName, targetName: 'Unknown',
            cq: NaN, cqSd: NaN, tm: NaN,
            amp: ampMarker >= 0 ? new Float32Array(pts.map(p => p.v)) : new Float32Array(0),
            melt: meltMarker >= 0 ? { temps: pts.map(p => p.x), fluores: pts.map(p => p.v) } : null
          });
        }
        finish();
        return run;
      }
      // legacy fallback: first line as header
      headerIdx = 0;
      headers = splitCsvLine(lines[0]);
    }

    const colIndex = (name) => headers.findIndex(h => new RegExp(name, 'i').test(h));

    const wellCol = colIndex('well');
    const fluorCol = colIndex('fluor|channel|dye');
    const targetCol = colIndex('target');
    const contentCol = colIndex('content');
    const cqCol = colIndex('cq|ct');
    const cqSdCol = colIndex('cq.*std|std.*dev|cqsd');
    const tmCol = colIndex('tm|melt');
    const cycleCol = colIndex('cycle');
    const valueCol = colIndex('^value$|fluorescen|signal|^data$');
    // wide cycle columns: "Cycle 1"... or bare numeric "1","2",...
    const ampCols = [];
    for (let i = 0; i < headers.length; i++) {
      if (/^cycle\s*\d+$/i.test(headers[i]) || /^\d+$/.test(headers[i])) ampCols.push(i);
    }

    // ── Long-format table: one row per cycle (Well,Fluor,Cycle,Value) ──
    if (wellCol >= 0 && cycleCol >= 0 && valueCol >= 0) {
      const pointsByKey = {};
      const metaByKey = {};
      for (let i = headerIdx + 1; i < summaryEnd; i++) {
        const cols = splitCsvLine(lines[i]);
        if (cols.length < 2) continue;
        const wellName = (cols[wellCol] || '').trim();
        if (!wellName) continue;
        const { row, col } = parsePosition(wellName, 96);
        const rawFluor = fluorCol >= 0 ? (cols[fluorCol] || '') : '';
        const canon = canonicalChannel(rawFluor) || 'FAM';
        const key = row + ',' + col + ',' + canon;
        const cyc = parseFloat(cols[cycleCol]);
        const val = parseFloat(cols[valueCol]);
        if (!pointsByKey[key]) pointsByKey[key] = [];
        if (isFinite(cyc) && isFinite(val)) pointsByKey[key].push({ c: cyc, v: val });
        if (!metaByKey[key]) {
          const cqRaw = cqCol >= 0 ? (cols[cqCol] || '') : '';
          metaByKey[key] = {
            row, col, rawFluor,
            sampleName: contentCol >= 0 && cols[contentCol] ? cols[contentCol] : wellName,
            targetName: targetCol >= 0 && cols[targetCol] ? cols[targetCol] : 'Unknown',
            cq: cqRaw ? parseFloat(cqRaw) : NaN
          };
        }
      }
      for (const key of Object.keys(pointsByKey)) {
        const meta = metaByKey[key];
        const pts = pointsByKey[key].slice().sort((a, b) => a.c - b.c);
        pushWellMeta({ ...meta, cqSd: NaN, tm: NaN, amp: new Float32Array(pts.map(p => p.v)), melt: null });
      }
      attachSection(parseSection(ampMarker), 'amp');
      attachSection(parseSection(meltMarker), 'melt');
      finish();
      return run;
    }

    // ── Summary table (one row per well) ──
    for (let i = headerIdx + 1; i < summaryEnd; i++) {
      const cols = splitCsvLine(lines[i]);
      if (cols.length < 2) continue;
      const wellName = wellCol >= 0 ? (cols[wellCol] || '') : '';
      if (!wellName) continue;

      const { row, col } = parsePosition(wellName, 96);
      const rawFluor = fluorCol >= 0 ? (cols[fluorCol] || '') : '';
      const targetName = targetCol >= 0 ? (cols[targetCol] || '') : 'Unknown';
      const content = contentCol >= 0 ? (cols[contentCol] || '') : '';
      const cqRaw = cqCol >= 0 ? (cols[cqCol] || '') : '';
      const cq = cqRaw ? parseFloat(cqRaw) : NaN;
      const cqSdRaw = cqSdCol >= 0 ? (cols[cqSdCol] || '') : '';
      const cqSd = cqSdRaw ? parseFloat(cqSdRaw) : NaN;
      const tmRaw = tmCol >= 0 ? (cols[tmCol] || '') : '';
      const tm = tmRaw ? parseFloat(tmRaw) : NaN;

      const ampVals = ampCols.map(ci => parseFloat(cols[ci])).filter(v => !isNaN(v));
      const amp = new Float32Array(ampVals);

      pushWellMeta({
        row, col, rawFluor,
        sampleName: content || wellName,
        targetName: targetName || 'Unknown',
        cq, cqSd, tm, amp, melt: null
      });
    }

    // ── Attach curve/melt sections (long tables after markers) ──
    attachSection(parseSection(ampMarker), 'amp');
    attachSection(parseSection(meltMarker), 'melt');

    finish();
  } catch (e) {
    throw new Error('CFX CSV parse failed: ' + e.message);
  }
  return run;
}

/**
 * Parse generic template (TSV/CSV) → canonical Run.
 * Template columns: Well, Sample, Target, Channel, Content, Cq, CqSD, Tm, Amplification (semicolon-separated)
 */
export function parseTemplate(text, fileName) {
  const run = makeRun({ fileName: fileName || 'template', sourceFormat: 'template' });
  try {
    const lines = text.split(/\r?\n/).filter(l => l.trim());
    if (lines.length === 0) throw new Error('Empty file');

    // detect delimiter
    const delim = lines[0].includes('\t') ? '\t' : ',';
    const splitRow = (line) => delim === ',' ? splitCsvLine(line) : line.split(delim).map(c => c.trim().replace(/^"|"$/g, ''));
    const headers = splitRow(lines[0]);

    const colIndex = (name) => headers.findIndex(h => new RegExp(name, 'i').test(h));
    const wellCol = colIndex('well');
    const sampleCol = colIndex('sample');
    const targetCol = colIndex('target');
    const channelCol = colIndex('channel|fluor|dye');
    const contentCol = colIndex('content');
    const cqCol = colIndex('cq|ct');
    const cqSdCol = colIndex('cqsd|cq.*sd|std');
    const tmCol = colIndex('tm|melt');
    const ampCol = colIndex('amplif|data|curve');
    // wide cycle columns: "Cycle 1"... or bare numeric "1","2",...
    const ampCols = [];
    for (let i = 0; i < headers.length; i++) {
      if (/^cycle\s*\d+$/i.test(headers[i]) || /^\d+$/.test(headers[i])) ampCols.push(i);
    }

    const targetsSeen = new Set();
    const samplesSeen = new Set();
    const channelsSeen = new Set();

    for (let i = 1; i < lines.length; i++) {
      const cols = splitRow(lines[i]);
      if (cols.length < 2) continue;
      const wellName = wellCol >= 0 ? cols[wellCol] : cols[0];
      if (!wellName) continue;

      const { row, col } = parsePosition(wellName, 96);
      const sampleName = (sampleCol >= 0 ? cols[sampleCol] : '') || wellName;
      const targetName = targetCol >= 0 ? cols[targetCol] : 'Unknown';
      const rawChannel = channelCol >= 0 ? cols[channelCol] : 'FAM';
      const content = contentCol >= 0 ? cols[contentCol] : '';
      const cqRaw = cqCol >= 0 ? cols[cqCol] : '';
      const cq = cqRaw ? parseFloat(cqRaw) : null;
      const cqSdRaw = cqSdCol >= 0 ? cols[cqSdCol] : '';
      const cqSd = cqSdRaw ? parseFloat(cqSdRaw) : null;
      const tmRaw = tmCol >= 0 ? cols[tmCol] : '';
      const tm = tmRaw ? parseFloat(tmRaw) : null;

      if (!samplesSeen.has(sampleName)) {
        samplesSeen.add(sampleName);
        run.samples.push(makeSample(run.samples.length, sampleName, guessSampleType(sampleName)));
      }
      if (!targetsSeen.has(targetName)) {
        targetsSeen.add(targetName);
        run.targets.push(makeTarget(run.targets.length, targetName, null, guessReference(targetName)));
      }
      const canon = canonicalChannel(rawChannel) || 'FAM';
      if (!channelsSeen.has(canon)) {
        channelsSeen.add(canon);
        run.channels.push(makeChannel(run.channels.length, rawChannel, canon));
      }

      const sampleId = run.samples.findIndex(s => s.name === sampleName);
      const targetId = run.targets.findIndex(t => t.name === targetName);
      const channelId = run.channels.findIndex(c => c.canonical === canon);

      let amp = new Float32Array(0);
      if (ampCol >= 0 && cols[ampCol]) {
        const vals = cols[ampCol].split(/[;|\s]+/).map(Number).filter(v => !isNaN(v));
        amp = new Float32Array(vals);
      } else if (ampCols.length) {
        const vals = ampCols.map(ci => parseFloat(cols[ci])).filter(v => !isNaN(v));
        if (vals.length) amp = new Float32Array(vals);
      }

      const well = makeWell(run.wells.length, row, col, '96');
      well.sampleId = sampleId;
      well.targetId = targetId;
      well.channelId = channelId;
      well.cq = isFinite(cq) ? cq : null;
      well.cqSD = isFinite(cqSd) ? cqSd : null;
      well.tm = isFinite(tm) ? tm : null;
      well.amplification = amp;
      run.wells.push(well);
    }

    if (run.channels.length === 0) run.channels.push(makeChannel(0, 'FAM', 'FAM'));
    for (const t of run.targets) if (t.channelId == null) t.channelId = 0;
  } catch (e) {
    throw new Error('Template parse failed: ' + e.message);
  }
  return run;
}

/**
 * Main parse entry point — auto-detect + dispatch.
 */
export function parseRun(text, fileName) {
  const fmt = detectFormat(text, fileName);
  switch (fmt) {
    case 'rdml': return parseRdml(text, fileName);
    case 'cfx_csv': return parseCfxCsv(text, fileName);
    case 'template': return parseTemplate(text, fileName);
    case 'xlsx': throw new Error('Excel .xlsx requires binary parsing. Use parseXlsxAsync() with an ArrayBuffer, or save as CSV (File → Save As → CSV).');
    case 'xls': throw new Error('Legacy Excel .xls detected. Please re-save as .xlsx (File → Save As → .xlsx) or export as CSV. Most instruments that produce .xls can re-save in 10 seconds.');
    case 'qbg': throw new Error('Qiagen Rotor-Gene .qbg is a proprietary binary format. Please export from Rotor-Gene Q software: File → Export → Excel/CSV. See the export guide below.');
    case 'pcrd': throw new Error('Bio-Rad .pcrd is a proprietary binary format. Please export from CFX Maestro: File → Export → RDML or CSV. See the export guide below.');
    case 'zip': throw new Error('ZIP archive detected. Please extract the file and upload individually, or use the ZIP upload feature.');
    case 'zip-batch': throw new Error('ZIP archive with multiple files. Use the ZIP upload feature to select which file to analyze.');
    case 'zip-rdml': throw new Error('ZIP archive containing RDML. Please extract and upload the .rdml file directly.');
    default: throw new Error('Unknown format. Try the generic template or check your export.');
  }
}

/**
 * Parse XLSX from an ArrayBuffer. Async (uses DecompressionStream).
 * Returns a canonical Run.
 */
export async function parseXlsxAsync(buffer, fileName) {
  const run = makeRun({ fileName: fileName || 'xlsx', sourceFormat: 'xlsx' });
  try {
    // 1. Parse ZIP to extract XML files
    const files = await extractZip(buffer);
    const sharedStringsXml = files['xl/sharedStrings.xml'] || '';
    const strings = sharedStringsXml ? parseSharedStrings(sharedStringsXml) : [];
    const sheetXml = files['xl/worksheets/sheet1.xml'] || files['xl/worksheets/sheet2.xml'] || '';

    // 3. Parse sheet data
    const rows = parseSheetXml(sheetXml, strings);

    if (rows.length === 0) throw new Error('No data found in spreadsheet');

    // 4. Detect header row
    const headers = rows[0].map(h => String(h || '').trim());
    const colIndex = (name) => headers.findIndex(h => new RegExp(name, 'i').test(h));

    const wellCol = colIndex('well');
    const sampleCol = colIndex('sample');
    const targetCol = colIndex('target');
    const channelCol = colIndex('channel|fluor|dye');
    const contentCol = colIndex('content');
    const cqCol = colIndex('cq|ct');
    const cqSdCol = colIndex('cqsd|cq.*sd|std');
    const tmCol = colIndex('tm|melt');
    const ampCol = colIndex('amplif|data|curve');
    // wide cycle columns: "Cycle 1"... or bare numeric "1","2",...
    const ampCols = [];
    for (let i = 0; i < headers.length; i++) {
      if (/^cycle\s*\d+$/i.test(headers[i]) || /^\d+$/.test(headers[i])) ampCols.push(i);
    }

    const targetsSeen = new Set();
    const samplesSeen = new Set();
    const channelsSeen = new Set();

    for (let i = 1; i < rows.length; i++) {
      const cols = rows[i];
      if (!cols || cols.length === 0) continue;
      const wellName = wellCol >= 0 ? String(cols[wellCol] || '') : String(cols[0] || '');
      if (!wellName) continue;

      const { row, col } = parsePosition(wellName, 96);
      const sampleName = sampleCol >= 0 ? String(cols[sampleCol] || wellName) : wellName;
      const targetName = targetCol >= 0 ? String(cols[targetCol] || 'Unknown') : 'Unknown';
      const rawChannel = channelCol >= 0 ? String(cols[channelCol] || 'FAM') : 'FAM';
      const content = contentCol >= 0 ? String(cols[contentCol] || '') : '';
      const cqRaw = cqCol >= 0 ? cols[cqCol] : '';
      const cq = cqRaw !== '' && cqRaw != null ? parseFloat(cqRaw) : null;
      const cqSdRaw = cqSdCol >= 0 ? cols[cqSdCol] : '';
      const cqSd = cqSdRaw !== '' && cqSdRaw != null ? parseFloat(cqSdRaw) : null;
      const tmRaw = tmCol >= 0 ? cols[tmCol] : '';
      const tm = tmRaw !== '' && tmRaw != null ? parseFloat(tmRaw) : null;

      if (!samplesSeen.has(sampleName)) {
        samplesSeen.add(sampleName);
        run.samples.push(makeSample(run.samples.length, sampleName, guessSampleType(sampleName)));
      }
      if (!targetsSeen.has(targetName)) {
        targetsSeen.add(targetName);
        run.targets.push(makeTarget(run.targets.length, targetName, null, guessReference(targetName)));
      }
      const canon = canonicalChannel(rawChannel) || 'FAM';
      if (!channelsSeen.has(canon)) {
        channelsSeen.add(canon);
        run.channels.push(makeChannel(run.channels.length, rawChannel, canon));
      }

      const sampleId = run.samples.findIndex(s => s.name === sampleName);
      const targetId = run.targets.findIndex(t => t.name === targetName);
      const channelId = run.channels.findIndex(c => c.canonical === canon);

      let amp = new Float32Array(0);
      if (ampCol >= 0 && cols[ampCol]) {
        const val = String(cols[ampCol]);
        const vals = val.split(/[;,\s|]/).map(Number).filter(v => !isNaN(v));
        amp = new Float32Array(vals);
      } else if (ampCols.length) {
        const vals = ampCols.map(ci => parseFloat(cols[ci])).filter(v => !isNaN(v));
        if (vals.length) amp = new Float32Array(vals);
      }

      const well = makeWell(run.wells.length, row, col, '96');
      well.sampleId = sampleId;
      well.targetId = targetId;
      well.channelId = channelId;
      well.cq = isFinite(cq) ? cq : null;
      well.cqSD = isFinite(cqSd) ? cqSd : null;
      well.tm = isFinite(tm) ? tm : null;
      well.amplification = amp;
      run.wells.push(well);
    }

    if (run.channels.length === 0) run.channels.push(makeChannel(0, 'FAM', 'FAM'));
    for (const t of run.targets) if (t.channelId == null) t.channelId = 0;
  } catch (e) {
    throw new Error('XLSX parse failed: ' + e.message);
  }
  return run;
}

// ── ZIP / XLSX helpers ──

function extractZipSync(buffer) {
  const files = {};
  const view = new DataView(buffer);
  const cdOffset = findCentralDirectory(view);
  if (cdOffset < 0) return files;
  let offset = cdOffset;
  while (offset < buffer.byteLength - 4) {
    const sig = view.getUint32(offset, true);
    if (sig !== 0x02014b50) break;
    const nameLen = view.getUint16(offset + 28, true);
    const extraLen = view.getUint16(offset + 30, true);
    const commentLen = view.getUint16(offset + 32, true);
    const nameBytes = new Uint8Array(buffer, offset + 46, nameLen);
    const name = new TextDecoder().decode(nameBytes);
    files[name] = true; // just store name, not content
    offset += 46 + nameLen + extraLen + commentLen;
  }
  return files;
}

async function extractZip(buffer) {
  const files = {};
  const view = new DataView(buffer);
  // Find central directory
  const cdOffset = findCentralDirectory(view);
  if (cdOffset < 0) throw new Error('Not a valid ZIP file');

  let offset = cdOffset;
  while (offset < buffer.byteLength - 4) {
    const sig = view.getUint32(offset, true);
    if (sig !== 0x02014b50) break; // central directory file header
    const nameLen = view.getUint16(offset + 28, true);
    const extraLen = view.getUint16(offset + 30, true);
    const commentLen = view.getUint16(offset + 32, true);
    const localHeaderOffset = view.getUint32(offset + 42, true);
    const compressedSize = view.getUint32(offset + 20, true);
    const method = view.getUint16(offset + 10, true);
    const nameBytes = new Uint8Array(buffer, offset + 46, nameLen);
    const name = new TextDecoder().decode(nameBytes);

    // Read local file
    const localSig = view.getUint32(localHeaderOffset, true);
    if (localSig !== 0x04034b50) { offset += 46 + nameLen + extraLen + commentLen; continue; }
    const localNameLen = view.getUint16(localHeaderOffset + 26, true);
    const localExtraLen = view.getUint16(localHeaderOffset + 28, true);
    const dataOffset = localHeaderOffset + 30 + localNameLen + localExtraLen;

    if (method === 0) {
      // Stored
      files[name] = new TextDecoder().decode(new Uint8Array(buffer, dataOffset, compressedSize));
    } else if (method === 8) {
      // Deflated
      const compressed = new Uint8Array(buffer, dataOffset, compressedSize);
      const decompressed = await inflate(compressed);
      files[name] = new TextDecoder().decode(decompressed);
    }
    offset += 46 + nameLen + extraLen + commentLen;
  }
  return files;
}

function findCentralDirectory(view) {
  // Search from end for EOCD signature
  for (let i = view.byteLength - 22; i >= 0; i--) {
    if (view.getUint32(i, true) === 0x06054b50) {
      return view.getUint32(i + 16, true);
    }
  }
  return -1;
}

async function inflate(data) {
  const ds = new DecompressionStream('deflate-raw');
  const writer = ds.writable.getWriter();
  writer.write(data);
  writer.close();
  const reader = ds.readable.getReader();
  const chunks = [];
  while (true) {
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

function parseSharedStrings(xml) {
  const strings = [];
  const siRegex = /<si>([\s\S]*?)<\/si>/gi;
  let m;
  while ((m = siRegex.exec(xml)) !== null) {
    const tMatch = m[1].match(/<t[^>]*>([\s\S]*?)<\/t>/);
    strings.push(tMatch ? tMatch[1] : '');
  }
  return strings;
}

function parseSheetXml(xml, strings) {
  const rows = [];
  const rowRegex = /<row[^>]*>([\s\S]*?)<\/row>/gi;
  let rowMatch;
  while ((rowMatch = rowRegex.exec(xml)) !== null) {
    const cells = [];
    const cellRegex = /<c\s+r="([A-Z]+)(\d+)"(?:\s+t="(\w+)")?[^>]*>(?:<v>([\s\S]*?)<\/v>)?/gi;
    let cellMatch;
    // Parse all cells in this row
    const cellMap = {};
    // Handle inlineStr: <c r="A1" t="inlineStr"><is><t>value</t></is></c>
    const inlineRe = /<c\s+r="([A-Z]+)(\d+)"\s+t="inlineStr"[^>]*><is><t[^>]*>([\s\S]*?)<\/t><\/is><\/c>/gi;
    let im;
    while ((im = inlineRe.exec(rowMatch[1])) !== null) {
      cellMap[im[1]] = im[3];
    }
    // Handle shared strings and numbers
    const re = /<c\s+r="([A-Z]+)(\d+)"(?:\s+t="(\w+)")?[^>]*>(?:<v>([\s\S]*?)<\/v>)?/gi;
    let cm;
    while ((cm = re.exec(rowMatch[1])) !== null) {
      const col = cm[1];
      if (cellMap[col] !== undefined) continue;
      const type = cm[3] || 'n';
      const val = cm[4] || '';
      let cellValue;
      if (type === 's') {
        cellValue = strings[parseInt(val)] || '';
      } else if (type === 'str') {
        cellValue = val;
      } else {
        cellValue = val !== '' ? (isNaN(parseFloat(val)) ? val : parseFloat(val)) : '';
      }
      cellMap[col] = cellValue;
    }
    // Convert cell map to array by column letter
    const cols = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    const maxCol = Math.max(...Object.keys(cellMap).map(c => cols.indexOf(c[0]) + 1), 0);
    const rowArr = [];
    for (let ci = 0; ci < maxCol; ci++) {
      const colLetter = cols[ci];
      rowArr.push(cellMap[colLetter] !== undefined ? cellMap[colLetter] : '');
    }
    rows.push(rowArr);
  }
  return rows;
}

/* ───────────────────────────────────────────────────────────────
   4. Helpers
   ─────────────────────────────────────────────────────────────── */

export function parsePosition(pos, layoutSize) {
  pos = String(pos).trim();
  // "A1" style
  const m = pos.match(/^([A-Za-z]+)(\d+)$/);
  if (m) {
    const row = m[1].toUpperCase().charCodeAt(0) - 65;
    const col = parseInt(m[2], 10) - 1;
    return { row: Math.max(0, row), col: Math.max(0, col) };
  }
  // numeric index
  const n = parseInt(pos, 10);
  if (!isNaN(n)) {
    const cols = layoutSize === 384 ? 24 : 12;
    return { row: Math.floor((n - 1) / cols), col: (n - 1) % cols };
  }
  return { row: 0, col: 0 };
}

export function guessSampleType(name) {
  const n = (name || '').toLowerCase();
  if (n.includes('ntc') || n.includes('no template') || n.includes('neg')) return 'ntc';
  if (n.includes('std') || n.includes('standard') || n.includes('calib')) return 'standard';
  if (n.includes('ctrl') || n.includes('control') || n.includes('ref')) return 'control';
  return 'unknown';
}

export function guessReference(name) {
  const n = (name || '').toLowerCase();
  return n.includes('gapdh') || n.includes('actb') || n.includes('beta') || n.includes('18s') || n.includes('rpl') || n.includes('tbp');
}

/* ───────────────────────────────────────────────────────────────
   5. Analysis — Standard Curve
   ─────────────────────────────────────────────────────────────── */

/**
 * Linear regression: y = mx + b
 * Returns { slope, intercept, r2 }
 */
export function linearRegression(xs, ys) {
  const n = xs.length;
  if (n < 2) return null;
  let sx = 0, sy = 0, sxx = 0, sxy = 0, syy = 0;
  for (let i = 0; i < n; i++) {
    sx += xs[i]; sy += ys[i];
    sxx += xs[i] * xs[i]; sxy += xs[i] * ys[i]; syy += ys[i] * ys[i];
  }
  const denom = n * sxx - sx * sx;
  if (denom === 0) return null;
  const slope = (n * sxy - sx * sy) / denom;
  const intercept = (sy - slope * sx) / n;
  const ssRes = syy - 2 * slope * sxy - 2 * intercept * sy + slope * slope * sxx + 2 * slope * intercept * sx + n * intercept * intercept;
  const ssTot = syy - (sy * sy) / n;
  const r2 = ssTot === 0 ? 1 : 1 - ssRes / ssTot;
  return { slope, intercept, r2: Math.max(0, Math.min(1, r2)) };
}

/**
 * Efficiency from slope: E% = (10^(-1/m) - 1) × 100
 */
export function efficiencyFromSlope(slope) {
  if (slope === 0) return null;
  return (Math.pow(10, -1 / slope) - 1) * 100;
}

/**
 * Compute standard curves per target.
 * Standards are wells where sample.type === 'standard' and cq != null and quantity != null.
 */
export function computeStandardCurves(run) {
  const curves = {};
  const targets = run.targets;
  for (const t of targets) {
    const stdWells = run.wells.filter(w => {
      if (w.targetId !== t.id) return false;
      if (w.cq == null) return false;
      const s = run.samples[w.sampleId];
      return s && s.type === 'standard' && s.quantity != null && s.quantity > 0;
    });
    if (stdWells.length < 2) {
      curves[t.id] = null;
      continue;
    }
    const xs = stdWells.map(w => Math.log10(run.samples[w.sampleId].quantity));
    const ys = stdWells.map(w => w.cq);
    const reg = linearRegression(xs, ys);
    if (!reg) { curves[t.id] = null; continue; }
    curves[t.id] = {
      slope: reg.slope,
      intercept: reg.intercept,
      r2: reg.r2,
      efficiencyPct: efficiencyFromSlope(reg.slope),
      n: stdWells.length,
    };
  }
  return curves;
}

/**
 * Quantify unknowns using standard curve: Q = 10^((Cq - b) / m)
 */
export function quantifyUnknowns(run, curves) {
  const result = {};
  for (const w of run.wells) {
    const s = run.samples[w.sampleId];
    if (!s || s.type !== 'unknown') continue;
    if (w.cq == null) continue;
    const curve = curves[w.targetId];
    if (!curve) continue;
    const q = Math.pow(10, (w.cq - curve.intercept) / curve.slope);
    result[w.id] = q;
  }
  return result;
}

/* ───────────────────────────────────────────────────────────────
   6. Analysis — Expression
   ─────────────────────────────────────────────────────────────── */

/**
 * Compute ΔCq, ΔΔCq, fold change per sample×target.
 *
 * method: 'livak' | 'pfaffl'
 * referenceTargets: array of target IDs
 * controlSample: sample ID (calibrator)
 * curves: standard curves (for Pfaffl efficiency)
 */
export function computeExpression(run, curves, referenceTargets, controlSample, method) {
  method = method || 'pfaffl';
  const expr = {};
  const refTargets = (referenceTargets || []).length ? referenceTargets : run.targets.filter(t => t.isReference).map(t => t.id);
  if (refTargets.length === 0) return expr;

  // group wells by sample
  const bySample = {};
  for (const w of run.wells) {
    if (w.cq == null) continue;
    const sid = w.sampleId;
    if (!bySample[sid]) bySample[sid] = [];
    bySample[sid].push(w);
  }

  // per-sample mean Cq per target
  const sampleTargetCq = {}; // sampleId -> targetId -> { mean, sd, n }
  for (const [sid, wells] of Object.entries(bySample)) {
    sampleTargetCq[sid] = {};
    const byTarget = {};
    for (const w of wells) {
      if (!byTarget[w.targetId]) byTarget[w.targetId] = [];
      byTarget[w.targetId].push(w.cq);
    }
    for (const [tid, cqs] of Object.entries(byTarget)) {
      const mean = cqs.reduce((a, b) => a + b, 0) / cqs.length;
      const sd = cqs.length > 1
        ? Math.sqrt(cqs.reduce((s, v) => s + (v - mean) ** 2, 0) / (cqs.length - 1))
        : 0;
      sampleTargetCq[sid][tid] = { mean, sd, n: cqs.length };
    }
  }

  const control = sampleTargetCq[controlSample];
  if (!control) return expr;

  for (const [sid, stc] of Object.entries(sampleTargetCq)) {
    for (const t of run.targets) {
      const tid = t.id;
      if (stc[tid] == null) continue;
      // ΔCq = Cq(target) - mean Cq(ref targets)
      const refCqs = refTargets.map(rt => stc[rt]?.mean).filter(v => v != null);
      if (refCqs.length === 0) continue;
      const refMean = refCqs.reduce((a, b) => a + b, 0) / refCqs.length;
      const refSd = refCqs.length > 1
        ? Math.sqrt(refCqs.reduce((s, v) => s + (v - refMean) ** 2, 0) / (refCqs.length - 1))
        : 0;

      const dCq = stc[tid].mean - refMean;
      const dCqSd = Math.sqrt(stc[tid].sd ** 2 + refSd ** 2);

      // control ΔCq
      const ctrlRefCqs = refTargets.map(rt => control[rt]?.mean).filter(v => v != null);
      const ctrlRefMean = ctrlRefCqs.length ? ctrlRefCqs.reduce((a, b) => a + b, 0) / ctrlRefCqs.length : 0;
      const ctrlDCq = control[tid] ? control[tid].mean - ctrlRefMean : 0;

      const ddCq = dCq - ctrlDCq;

      // fold
      let fold, foldSD;
      if (method === 'pfaffl') {
        const tEff = curves[tid]?.efficiencyPct != null ? (curves[tid].efficiencyPct / 100 + 1) : 2;
        const rEff = refTargets.map(rt => curves[rt]?.efficiencyPct != null ? (curves[rt].efficiencyPct / 100 + 1) : 2);
        const rEffMean = rEff.reduce((a, b) => a + b, 0) / rEff.length;
        const targetRatio = Math.pow(tEff, ctrlDCq - dCq); // E_target^(ΔCq_target_control - ΔCq_target_sample)
        const refRatio = Math.pow(rEffMean, ctrlRefMean - refMean);
        fold = targetRatio / refRatio;
        // approximate SD
        foldSD = Math.abs(fold * Math.log(2) * dCqSd);
      } else {
        fold = Math.pow(2, -ddCq);
        foldSD = Math.abs(fold * Math.log(2) * dCqSd);
      }

      expr[`${sid}_${tid}`] = {
        sampleId: sid,
        targetId: tid,
        dCq,
        dCqSd,
        ddCq,
        fold,
        foldSD,
        method,
        n: stc[tid].n,
      };
    }
  }
  return expr;
}

/* ───────────────────────────────────────────────────────────────
   7. QC Flags
   ─────────────────────────────────────────────────────────────── */

export function computeQc(run, curves, thresholds) {
  thresholds = thresholds || {};
  const t = {
    ntcCq: thresholds.ntcCq || 35,
    replicateSd: thresholds.replicateSd || 0.5,
    effMin: thresholds.effMin || 90,
    effMax: thresholds.effMax || 110,
    r2Min: thresholds.r2Min || 0.99,
    lateCq: thresholds.lateCq || 35,
  };
  const qc = { wells: {}, run: [] };

  // per-well flags
  for (const w of run.wells) {
    const flags = [];
    const s = run.samples[w.sampleId];
    // NTC amplification
    if (s && s.type === 'ntc' && w.cq != null) {
      flags.push({ code: 'NTC_AMP', severity: w.cq < t.ntcCq ? 'strong' : 'weak', detail: `NTC Cq = ${w.cq}` });
    }
    // late Cq
    if (w.cq != null && w.cq > t.lateCq) {
      flags.push({ code: 'LATE_CQ', severity: 'info', detail: `Cq ${w.cq} > ${t.lateCq}` });
    }
    // no amplification
    if (w.cq == null && (w.amplification.length === 0 || Math.max(...w.amplification) < 1)) {
      flags.push({ code: 'NO_AMP', severity: 'info', detail: 'No amplification detected' });
    }
    // melt multi-peak
    if (w.tmPeaks && w.tmPeaks.length > 1) {
      flags.push({ code: 'MULTI_PEAK', severity: 'warning', detail: `${w.tmPeaks.length} melt peaks` });
    }
    qc.wells[w.id] = flags;
  }

  // per-run flags: replicate SD
  const bySampleTarget = {};
  for (const w of run.wells) {
    if (w.cq == null) continue;
    const key = `${w.sampleId}_${w.targetId}`;
    if (!bySampleTarget[key]) bySampleTarget[key] = [];
    bySampleTarget[key].push(w.cq);
  }
  for (const [key, cqs] of Object.entries(bySampleTarget)) {
    if (cqs.length < 2) continue;
    const mean = cqs.reduce((a, b) => a + b, 0) / cqs.length;
    const sd = Math.sqrt(cqs.reduce((s, v) => s + (v - mean) ** 2, 0) / (cqs.length - 1));
    if (sd > t.replicateSd) {
      qc.run.push({ code: 'HIGH_REPLICATE_SD', severity: 'warning', detail: `${key}: SD = ${sd.toFixed(2)} > ${t.replicateSd}` });
    }
  }

  // efficiency flags
  for (const [tid, curve] of Object.entries(curves)) {
    if (!curve) continue;
    if (curve.efficiencyPct < t.effMin || curve.efficiencyPct > t.effMax) {
      qc.run.push({ code: 'EFFICIENCY_OUT_OF_RANGE', severity: 'warning', detail: `Target ${tid}: E = ${curve.efficiencyPct.toFixed(1)}%` });
    }
    if (curve.r2 < t.r2Min) {
      qc.run.push({ code: 'LOW_R2', severity: 'warning', detail: `Target ${tid}: R² = ${curve.r2.toFixed(4)}` });
    }
  }

  return qc;
}

/* ───────────────────────────────────────────────────────────────
   8. Melt derivative (Savitzky-Golay window 7)
   ─────────────────────────────────────────────────────────────── */

export function savitzkyGolayDerivative(temps, fluores, windowSize) {
  windowSize = windowSize || 7;
  const n = temps.length;
  if (n < windowSize) return { temps: temps.slice(), derivative: fluores.map(() => 0) };
  const half = Math.floor(windowSize / 2);
  const deriv = new Array(n).fill(0);
  // central difference with SG smoothing
  for (let i = half; i < n - half; i++) {
    let num = 0, den = 0;
    for (let j = -half; j <= half; j++) {
      const w = 1 - Math.abs(j) / (half + 1); // triangular weight (simplified SG)
      num += w * (fluores[i + j] - fluores[i - j]) / (2 * (temps[i + j] - temps[i - j] || 1));
      den += w;
    }
    deriv[i] = den > 0 ? num / den : 0;
  }
  // negate for -dF/dT convention
  return { temps: temps.slice(), derivative: deriv.map(v => -v) };
}

/**
 * Detect Tm peaks from melt derivative.
 * Returns array of { temp, height } for peaks above threshold.
 */
export function detectTmPeaks(temps, derivative, threshold) {
  threshold = threshold || 0.1;
  const peaks = [];
  const maxD = Math.max(...derivative.map(Math.abs));
  const thr = maxD * threshold;
  for (let i = 1; i < derivative.length - 1; i++) {
    if (derivative[i] > derivative[i - 1] && derivative[i] > derivative[i + 1] && derivative[i] > thr) {
      peaks.push({ temp: temps[i], height: derivative[i] });
    }
  }
  return peaks;
}

/* ───────────────────────────────────────────────────────────────
   9. Full analysis pipeline
   ─────────────────────────────────────────────────────────────── */

export function analyzeRun(run, settings) {
  settings = settings || {};
  const curves = computeStandardCurves(run);
  const quantified = quantifyUnknowns(run, curves);
  const refTargets = settings.referenceTargets || run.targets.filter(t => t.isReference).map(t => t.id);
  const controlSample = settings.controlSample != null ? settings.controlSample : (run.samples.find(s => s.type === 'control')?.id ?? run.samples[0]?.id);
  const method = settings.method || (Object.values(curves).some(c => c) ? 'pfaffl' : 'livak');
  const expression = computeExpression(run, curves, refTargets, controlSample, method);
  const qc = computeQc(run, curves, settings.thresholds);
  return { standardCurves: curves, quantified, expression, qc, settings: { referenceTargets: refTargets, controlSample, method } };
}

/* ───────────────────────────────────────────────────────────────
   10. Exports
   ─────────────────────────────────────────────────────────────── */

/* ───────────────────────────────────────────────────────────────
   11. View-State (serializable UI preferences)
   ─────────────────────────────────────────────────────────────── */

export function makeViewState() {
  return {
    table: { columns: ['well','sample','target','channel','cq','cqSD','tm'], filters: {}, groupBy: '', sort: { col: 'well', dir: 'asc' }, search: '' },
    charts: { amplification: { channels: [], yMode: 'linear', hiddenWells: [] }, melt: { channel: 0 } },
    plate: { layout: '96', colorBy: 'cq' },
    analysis: { referenceTargets: [], controlSample: null, method: 'pfaffl', thresholds: {} },
  };
}

export function serializeViewState(vs) {
  return btoa(JSON.stringify(vs));
}

export function deserializeViewState(b64) {
  try {
    return JSON.parse(atob(b64));
  } catch (e) {
    return null;
  }
}

export function saveView(name, vs) {
  const views = JSON.parse(localStorage.getItem('qpcr_views') || '{}');
  views[name] = vs;
  localStorage.setItem('qpcr_views', JSON.stringify(views));
}

export function loadView(name) {
  const views = JSON.parse(localStorage.getItem('qpcr_views') || '{}');
  return views[name] || null;
}

export function listViews() {
  const views = JSON.parse(localStorage.getItem('qpcr_views') || '{}');
  return Object.keys(views);
}

export function deleteView(name) {
  const views = JSON.parse(localStorage.getItem('qpcr_views') || '{}');
  delete views[name];
  localStorage.setItem('qpcr_views', JSON.stringify(views));
}

/* ───────────────────────────────────────────────────────────────
   12. Methods Generator (MIQE-aligned)
   ─────────────────────────────────────────────────────────────── */

export function generateMethods(run, analysis, settings) {
  settings = settings || analysis?.settings || {};
  const parts = [];
  parts.push('Cq values were determined by ' + (run.meta.instrument || 'the instrument') + ' software.');
  // Efficiency
  const curves = analysis?.standardCurves || {};
  const effs = Object.entries(curves).filter(([, c]) => c).map(([tid, c]) => {
    const t = run.targets.find(x => x.id == tid);
    return (t?.name || 'target ' + tid) + ': E=' + c.efficiencyPct.toFixed(1) + '%, R²=' + c.r2.toFixed(3);
  });
  if (effs.length > 0) {
    parts.push('Efficiency (' + effs.join('; ') + ') was calculated from standard curve slope.');
  }
  // Method
  const method = settings.method || analysis?.settings?.method || 'livak';
  const methodName = method === 'pfaffl' ? 'Pfaffl method (efficiency-corrected)' : 'Livak method (2^-ddCq)';
  const refTargets = (settings.referenceTargets || analysis?.settings?.referenceTargets || []).map(tid => {
    const t = run.targets.find(x => x.id == tid);
    return t?.name || tid;
  });
  const ctrlSample = settings.controlSample != null ? settings.controlSample : analysis?.settings?.controlSample;
  const ctrlName = run.samples.find(s => s.id == ctrlSample)?.name || 'control';
  if (refTargets.length > 0) {
    parts.push('Relative expression was quantified by the ' + methodName + ' using ' + refTargets.join(', ') + ' as reference gene(s) and ' + ctrlName + ' as calibrator.');
  }
  parts.push('Research use only. Not for clinical diagnostic decisions.');
  return parts.join(' ');
}

export const QPCR_ENGINE_VERSION = '1.0.0';

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    canonicalChannel, makeRun, makeChannel, makeTarget, makeSample, makeWell, makeAnalysis,
    parsePosition, guessSampleType, guessReference, detectFormat, parseRdml, parseCfxCsv, parseTemplate, parseRun,
    linearRegression, efficiencyFromSlope, computeStandardCurves, quantifyUnknowns,
    computeExpression, computeQc, savitzkyGolayDerivative, detectTmPeaks, analyzeRun,
    QPCR_ENGINE_VERSION,
  };
}
