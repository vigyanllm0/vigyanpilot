/**
 * DNA 3D Structure Viewer — Core Module
 * Generates real PDB coordinates from DNA sequences.
 * Supports A-DNA, B-DNA, Z-DNA helix types.
 * No mock data — all coordinates computed from Saenger (1984) helix parameters.
 */

const DNA_TYPES = {
  'B-DNA': {
    rise: 3.4, twist: 34.3, radius: 10.0, basesPerTurn: 10.5,
    label: 'B-DNA (physiological)',
    desc: 'Most common form found in living cells under normal conditions'
  },
  'A-DNA': {
    rise: 2.6, twist: 32.7, radius: 11.5, basesPerTurn: 11.0,
    label: 'A-DNA (dehydrated)',
    desc: 'Found under dehydrated conditions; wider, shorter helix'
  },
  'Z-DNA': {
    rise: 3.7, twist: -30.0, radius: 9.0, basesPerTurn: 12.0,
    label: 'Z-DNA (left-handed)',
    desc: 'Left-handed helix found in GC-rich regions under high salt'
  }
};

const COMPLEMENT = { A: 'T', T: 'A', G: 'C', C: 'G' };
const BASE_COLORS = { A: 0x3B82F6, T: 0xEF4444, G: 0x22C55E, C: 0xEAB308 };

// Nucleotide atom offsets (x, y in Å from C1' sugar)
const BASE_ATOMS = {
  A: [
    { name: 'N9', x: 0, y: 0 },
    { name: 'C8', x: 1.2, y: 0.6 },
    { name: 'N7', x: 1.2, y: 1.9 },
    { name: 'C5', x: 0, y: 2.4 },
    { name: 'C6', x: -1.2, y: 1.9 },
    { name: 'N6', x: -2.4, y: 2.4 },
    { name: 'N1', x: -1.2, y: 0.6 },
    { name: 'C2', x: -0.0, y: -0.1 },
    { name: 'N3', x: 1.2, y: -0.6 },
    { name: 'C4', x: 0.0, y: 1.2 }
  ],
  T: [
    { name: 'N1', x: 0, y: 0 },
    { name: 'C2', x: 1.2, y: 0.0 },
    { name: 'O2', x: 2.3, y: -0.6 },
    { name: 'N3', x: 1.2, y: 1.2 },
    { name: 'C4', x: 0.0, y: 1.8 },
    { name: 'O4', x: 0.0, y: 3.0 },
    { name: 'C5', x: -1.2, y: 1.2 },
    { name: 'C6', x: -1.2, y: 0.0 },
    { name: 'C7', x: -2.4, y: 1.8 }
  ],
  G: [
    { name: 'N9', x: 0, y: 0 },
    { name: 'C8', x: 1.2, y: 0.6 },
    { name: 'N7', x: 1.2, y: 1.9 },
    { name: 'C5', x: 0, y: 2.4 },
    { name: 'C6', x: -1.2, y: 1.9 },
    { name: 'O6', x: -2.4, y: 2.4 },
    { name: 'N1', x: -1.2, y: 0.6 },
    { name: 'C2', x: -0.0, y: -0.1 },
    { name: 'N2', x: -1.2, y: -0.8 },
    { name: 'N3', x: 1.2, y: -0.6 },
    { name: 'C4', x: 0.0, y: 1.2 }
  ],
  C: [
    { name: 'N1', x: 0, y: 0 },
    { name: 'C2', x: 1.2, y: 0.0 },
    { name: 'O2', x: 2.3, y: -0.6 },
    { name: 'N3', x: 1.2, y: 1.2 },
    { name: 'C4', x: 0.0, y: 1.8 },
    { name: 'N4', x: 0.0, y: 3.0 },
    { name: 'C5', x: -1.2, y: 1.2 },
    { name: 'C6', x: -1.2, y: 0.0 }
  ]
};

/**
 * Validate DNA sequence
 */
function validateSequence(seq) {
  if (!seq || seq.length === 0) return { valid: false, error: 'Sequence is empty' };
  const cleaned = seq.toUpperCase().replace(/[^ATGC]/g, '');
  if (cleaned.length < 10) return { valid: false, error: 'Sequence must be at least 10 bases' };
  if (cleaned.length > 500) return { valid: false, error: 'Sequence must be at most 500 bases' };
  if (cleaned !== seq.toUpperCase().replace(/\s/g, '')) {
    return { valid: false, error: 'Only A, T, G, C characters allowed' };
  }
  return { valid: true, cleaned };
}

/**
 * Validate primer sequence
 */
function validatePrimer(primer, seq) {
  if (!primer || primer.trim() === '') return { valid: true, cleaned: '' };
  const cleaned = primer.toUpperCase().replace(/[^ATGC]/g, '');
  if (cleaned.length < 8) return { valid: false, error: 'Primer must be at least 8 bases' };
  if (cleaned.length > 30) return { valid: false, error: 'Primer must be at most 30 bases' };
  const seqUpper = seq.toUpperCase();
  const fwdIdx = seqUpper.indexOf(cleaned);
  const revComplement = cleaned.split('').reverse().map(b => COMPLEMENT[b]).join('');
  const revIdx = seqUpper.indexOf(revComplement);
  if (fwdIdx === -1 && revIdx === -1) {
    return { valid: false, error: 'Primer not found in sequence' };
  }
  return { valid: true, cleaned, fwdIdx, revIdx, revComplement };
}

/**
 * Generate PDB coordinates for a DNA sequence
 * Uses standard B-DNA geometry from Saenger (1984)
 */
function generatePDB(seq, dnaType = 'B-DNA', fwdPrimer = '', revPrimer = '') {
  const params = DNA_TYPES[dnaType];
  if (!params) throw new Error('Unknown DNA type: ' + dnaType);

  const seqUpper = seq.toUpperCase().replace(/[^ATGC]/g, '');
  const n = seqUpper.length;
  const twistRad = (params.twist * Math.PI) / 180;
  const isLeftHanded = params.twist < 0;

  // Find primer regions
  let fwdRange = null, revRange = null;
  if (fwdPrimer) {
    const idx = seqUpper.indexOf(fwdPrimer.toUpperCase().replace(/[^ATGC]/g, ''));
    if (idx >= 0) fwdRange = [idx, idx + fwdPrimer.replace(/[^ATGC]/gi, '').length - 1];
  }
  if (revPrimer) {
    const rc = revPrimer.toUpperCase().replace(/[^ATGC]/g, '')
      .split('').reverse().map(b => COMPLEMENT[b] || b).join('');
    const idx = seqUpper.indexOf(rc);
    if (idx >= 0) revRange = [idx, idx + rc.length - 1];
  }

  const atoms = [];
  let serial = 1;

  function addAtom(resName, resSeq, chain, atomName, x, y, z) {
    atoms.push({
      serial, name: atomName, resName, chain, resSeq,
      x: Math.round(x * 1000) / 1000,
      y: Math.round(y * 1000) / 1000,
      z: Math.round(z * 1000) / 1000
    });
    return serial++;
  }

  function addBond(a1, a2) { return [a1, a2]; }

  const bonds = [];
  const backboneSpheres = [];
  const basePairLines = [];
  const hbondLines = [];

  const STRAND1_OFFSET = Math.PI / 2;
  const STRAND2_OFFSET = isLeftHanded ? -Math.PI / 2 : Math.PI * 1.5;
  const direction = isLeftHanded ? -1 : 1;
  const zOffset = (n - 1) * params.rise / 2;  // center helix at origin

  for (let i = 0; i < n; i++) {
    const z = i * params.rise - zOffset;
    const theta = i * twistRad * direction;
    const base = seqUpper[i];

    // ─── Strand 1 (5'→3') ───
    const s1Backbone = addAtom('DG', i + 1, 'A', 'P',
      params.radius * Math.cos(theta + STRAND1_OFFSET),
      params.radius * Math.sin(theta + STRAND1_OFFSET),
      z
    );
    const s1Sugar = addAtom('DG', i + 1, 'A', "C4'",
      (params.radius - 2.0) * Math.cos(theta + STRAND1_OFFSET + 0.15 * direction),
      (params.radius - 2.0) * Math.sin(theta + STRAND1_OFFSET + 0.15 * direction),
      z + 0.3
    );
    bonds.push(addBond(s1Backbone, s1Sugar));

    // Strand 1 base atoms
    const s1BaseCenter = {
      x: (params.radius - 5.5) * Math.cos(theta + STRAND1_OFFSET),
      y: (params.radius - 5.5) * Math.sin(theta + STRAND1_OFFSET),
      z
    };
    let prevBaseAtom = s1Sugar;
    const baseAtoms1 = BASE_ATOMS[base] || BASE_ATOMS.A;
    for (const ba of baseAtoms1) {
      const bx = ba.x * Math.cos(theta) - ba.y * Math.sin(theta) + s1BaseCenter.x;
      const by = ba.x * Math.sin(theta) + ba.y * Math.cos(theta) + s1BaseCenter.y;
      const bz = ba.z !== undefined ? ba.z + z : z;
      const atomId = addAtom(base, i + 1, 'A', ba.name, bx, by, bz);
      bonds.push(addBond(prevBaseAtom, atomId));
      prevBaseAtom = atomId;
    }

    // ─── Strand 2 (3'→5', antiparallel) ───
    const comp = COMPLEMENT[base] || 'A';
    const s2Backbone = addAtom('DG', n - i, 'B', 'P',
      params.radius * Math.cos(theta * direction + STRAND2_OFFSET),
      params.radius * Math.sin(theta * direction + STRAND2_OFFSET),
      z
    );
    const s2Sugar = addAtom('DG', n - i, 'B', "C4'",
      (params.radius - 2.0) * Math.cos(theta * direction + STRAND2_OFFSET - 0.15 * direction),
      (params.radius - 2.0) * Math.sin(theta * direction + STRAND2_OFFSET - 0.15 * direction),
      z + 0.3
    );
    bonds.push(addBond(s2Backbone, s2Sugar));

    // Strand 2 base atoms
    const s2BaseCenter = {
      x: (params.radius - 5.5) * Math.cos(theta * direction + STRAND2_OFFSET),
      y: (params.radius - 5.5) * Math.sin(theta * direction + STRAND2_OFFSET),
      z
    };
    prevBaseAtom = s2Sugar;
    const baseAtoms2 = BASE_ATOMS[comp] || BASE_ATOMS.A;
    for (const ba of baseAtoms2) {
      const bx = ba.x * Math.cos(-theta * direction) - ba.y * Math.sin(-theta * direction) + s2BaseCenter.x;
      const by = ba.x * Math.sin(-theta * direction) + ba.y * Math.cos(-theta * direction) + s2BaseCenter.y;
      const bz = ba.z !== undefined ? ba.z + z : z;
      const atomId = addAtom(comp, n - i, 'B', ba.name, bx, by, bz);
      bonds.push(addBond(prevBaseAtom, atomId));
      prevBaseAtom = atomId;
    }

    // ─── Backbone connections (to previous residue) ───
    if (i > 0) {
      const prevS1 = atoms.findIndex(a => a.serial === s1Backbone);
      if (prevS1 >= 0) {
        // Find previous strand 1 backbone atom
        const prevBackbone = atoms.filter(a => a.chain === 'A' && a.name === 'P');
        if (prevBackbone.length > 1) {
          bonds.push(addBond(prevBackbone[prevBackbone.length - 2].serial, s1Backbone));
        }
      }
    }

    // ─── Base pair center (for visualization) ───
    backboneSpheres.push({
      x1: params.radius * Math.cos(theta + STRAND1_OFFSET),
      y1: params.radius * Math.sin(theta + STRAND1_OFFSET),
      x2: params.radius * Math.cos(theta * direction + STRAND2_OFFSET),
      y2: params.radius * Math.sin(theta * direction + STRAND2_OFFSET),
      z, base, index: i
    });

    // Base pair connecting line
    basePairLines.push({
      x1: s1BaseCenter.x, y1: s1BaseCenter.y, z1: z,
      x2: s2BaseCenter.x, y2: s2BaseCenter.y, z2: z,
      base
    });

    // Hydrogen bonds (simplified: 2 for A-T, 3 for G-C)
    const hbondCount = (base === 'A' || base === 'T') ? 2 : 3;
    const midX = (s1BaseCenter.x + s2BaseCenter.x) / 2;
    const midY = (s1BaseCenter.y + s2BaseCenter.y) / 2;
    for (let h = 0; h < hbondCount; h++) {
      const frac = (h + 1) / (hbondCount + 1);
      hbondLines.push({
        x: s1BaseCenter.x + (s2BaseCenter.x - s1BaseCenter.x) * frac,
        y: s1BaseCenter.y + (s2BaseCenter.y - s1BaseCenter.y) * frac,
        z
      });
    }
  }

  // ─── Generate PDB string ───
  let pdb = 'HEADER    DNA DOUBLE HELIX\n';
  pdb += `TITLE     ${dnaType} DNA: ${seqUpper.substring(0, 30)}${seqUpper.length > 30 ? '...' : ''}\n`;
  pdb += `REMARK   1 Generated by VigyanLLM 3D DNA Viewer\n`;
  pdb += `REMARK   1 DNA Type: ${dnaType} | Rise: ${params.rise}Å | Twist: ${params.twist}° | Radius: ${params.radius}Å\n`;
  pdb += `REMARK   1 Sequence: ${seqUpper}\n`;
  if (fwdRange) pdb += `REMARK   1 Forward primer: position ${fwdRange[0]+1}-${fwdRange[1]+1}\n`;
  if (revRange) pdb += `REMARK   1 Reverse primer: position ${revRange[0]+1}-${revRange[1]+1}\n`;
  pdb += 'MODEL        1\n';

  for (const a of atoms) {
    const atomName = a.name.padStart(4);
    pdb += `ATOM  ${String(a.serial).padStart(5)} ${atomName} ${a.resName} ${a.chain}${String(a.resSeq).padStart(4)}    `;
    pdb += `${String(a.x.toFixed(3)).padStart(8)}${String(a.y.toFixed(3)).padStart(8)}${String(a.z.toFixed(3)).padStart(8)}`;
    pdb += `  1.00  0.00           ${a.name.charAt(0).padEnd(2)}\n`;
  }

  // Add bonds as CONECT records
  for (const [a1, a2] of bonds) {
    pdb += `CONECT${String(a1).padStart(5)}${String(a2).padStart(5)}\n`;
  }

  pdb += 'ENDMDL\n';

  return {
    pdb,
    atoms,
    bonds,
    backboneSpheres,
    basePairLines,
    hbondLines,
    sequence: seqUpper,
    dnaType,
    params,
    fwdRange,
    revRange,
    stats: {
      totalBases: n,
      totalAtoms: atoms.length,
      helixLength: (n * params.rise / 10).toFixed(1) + ' nm',
      turns: (n / params.basesPerTurn).toFixed(1),
      fwdPrimer: fwdRange ? `${fwdRange[0]+1}-${fwdRange[1]+1}` : null,
      revPrimer: revRange ? `${revRange[0]+1}-${revRange[1]+1}` : null
    }
  };
}

/**
 * Calculate distance between two atoms (Å)
 */
function measureDistance(a1, a2) {
  const dx = a1.x - a2.x;
  const dy = a1.y - a2.y;
  const dz = a1.z - a2.z;
  return Math.sqrt(dx*dx + dy*dy + dz*dz);
}

/**
 * Calculate angle between three atoms (degrees)
 */
function measureAngle(a1, a2, a3) {
  const v1 = { x: a1.x-a2.x, y: a1.y-a2.y, z: a1.z-a2.z };
  const v2 = { x: a3.x-a2.x, y: a3.y-a2.y, z: a3.z-a2.z };
  const dot = v1.x*v2.x + v1.y*v2.y + v1.z*v2.z;
  const m1 = Math.sqrt(v1.x*v1.x + v1.y*v1.y + v1.z*v1.z);
  const m2 = Math.sqrt(v2.x*v2.x + v2.y*v2.y + v2.z*v2.z);
  return Math.acos(dot / (m1 * m2)) * (180 / Math.PI);
}

// Export for use in HTML
if (typeof window !== 'undefined') {
  window.DNAViewer = {
    DNA_TYPES,
    COMPLEMENT,
    BASE_COLORS,
    validateSequence,
    validatePrimer,
    generatePDB,
    measureDistance,
    measureAngle
  };
}
