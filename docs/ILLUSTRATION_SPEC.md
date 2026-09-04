# Custom Tool Illustrations — Commission Spec

## Overview
Six simple line-art illustrations for VigyanLLM's tool pages. Single-weight line art (2px stroke), no fill, using saffron (#e85d4c) and sage (#7c9a6b) accents. Consistent stroke weight is critical — do not mix filled icons and line icons.

## Style Guide
- **Stroke weight:** 2px consistent
- **Colors:** Saffron (#e85d4c) primary, Sage (#7c9a6b) secondary, Dark navy (#1a1a2e) for outlines
- **Fill:** None (transparent)
- **Background:** Transparent
- **Size:** 120×120px viewBox
- **Format:** SVG (vector, scalable)
- **Aesthetic:** Hand-drawn feel — slightly imperfect circles, sketchy arrows. "Crafted by scientists, not marketers."

## Illustrations

### 1. Primer Design
- **Concept:** Double helix with two arrows pointing inward (representing forward/reverse primers binding)
- **Elements:** DNA double helix (simplified, 3 turns), two horizontal arrows pointing inward from left and right
- **Colors:** Helix in dark navy, arrows in saffron
- **Use on:** /primer hero, pillar card

### 2. BLAST Search
- **Concept:** A wave/sequence match visualization (like an alignment dot plot)
- **Elements:** Two parallel horizontal lines (sequences), diagonal match lines between them, a magnifying glass over one match
- **Colors:** Lines in dark navy, match lines in sage, magnifying glass in saffron
- **Use on:** /blast hero, pillar card

### 3. Molecular Docking
- **Concept:** A protein pocket with a small molecule fitting in
- **Elements:** Simplified protein surface (curved shape with a pocket), small molecule (3-4 connected circles) fitting into the pocket
- **Colors:** Protein in dark navy, small molecule in saffron
- **Use on:** /docking hero, pillar card

### 4. Multiple Sequence Alignment
- **Concept:** Three aligned sequences with conservation bars
- **Elements:** Three horizontal bars (sequences) with vertical lines showing matching positions, a conservation bar below with varying heights
- **Colors:** Sequences in dark navy, conservation bars in sage (tall) and saffron (short)
- **Use on:** /msa hero, pillar card

### 5. CRISPR
- **Concept:** Scissors cutting a DNA strand at a specific locus
- **Elements:** DNA strand (horizontal, simplified), scissors icon at a cut point, small guide RNA indicator
- **Colors:** DNA in dark navy, scissors in saffron, guide RNA in sage
- **Use on:** /crispr-analysis hero (when live), pillar card

### 6. Tm Calculator
- **Concept:** A thermometer with a DNA strand wrapped around it
- **Elements:** Thermometer (vertical, with temperature markings), DNA strand wrapping around it, temperature value displayed
- **Colors:** Thermometer in dark navy, DNA in saffron, temperature in sage
- **Use on:** /tm-calculator hero

## Delivery
- SVG files to `frontend/assets/illustrations/`
-命名: `illustration-primer.svg`, `illustration-blast.svg`, etc.
- Each file should be <5KB optimized
- Include viewBox="0 0 120 120" for consistent sizing

## Budget
- ₹5,000–15,000 for all 6 illustrations
- Fiverr/Upwork: search "scientific line art illustration" or "bioinformatics icon design"
- Reference style: "hand-drawn scientific line art, single weight stroke, no fill"
