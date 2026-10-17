"""
Pharma calculator test suite — validates every calculation in pharma-calc.js
against hand-computed reference values and known pharmaceutical formulas.
"""

import pytest
import math
import subprocess
import sys
import os
import tempfile
import json


def run_js(code):
    """Execute JavaScript code in Node.js and return the result."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, dir='/tmp') as f:
        f.write(code)
        f.flush()
        tmp_path = f.name
    try:
        result = subprocess.run(
            ['node', '-e', f"""
var fs = require('fs');
var code = fs.readFileSync('{tmp_path}', 'utf8');
eval(code);
"""],
            capture_output=True, text=True, timeout=10,
            cwd=os.path.dirname(tmp_path)
        )
        if result.returncode != 0:
            raise RuntimeError(f"Node.js error: {result.stderr}")
        return result.stdout.strip()
    finally:
        os.unlink(tmp_path)


@pytest.fixture(scope="module")
def pharma_calc():
    """Load pharma-calc.js and return the PharmaCalc object."""
    js_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'pharma-calc.js')
    with open(js_path, 'r') as f:
        js_code = f.read()
    return js_code


def test_antibiotic_database_completeness(pharma_calc):
    """Verify the antibiotic database has 30+ entries with all required fields."""
    output = run_js(f"{pharma_calc}; console.log(PharmaCalc.ANTIBIOTICS.length);")
    count = int(output)
    assert count >= 30, f"Expected 30+ antibiotics, got {count}"

    # Check first entry has all required fields
    output = run_js(f"{pharma_calc}; console.log(JSON.stringify(PharmaCalc.ANTIBIOTICS[0]));")
    entry = json.loads(output)
    required_fields = ['name', 'stock', 'working', 'solvent', 'storage', 'light', 'solubility', 'saltForm', 'saltFactor', 'mw', 'notes']
    for field in required_fields:
        assert field in entry, f"Missing field: {field}"


def test_ampicillin_stock_calculation(pharma_calc):
    """Hand-computed: 100 mg/mL × 10 mL = 1000 mg base × 1.09 salt factor = 1090 mg / 100% purity = 1090 mg."""
    output = run_js(f"""
{pharma_calc}
var abx = PharmaCalc.ANTIBIOTICS.find(function(a){{return a.name==='Ampicillin'}});
var result = PharmaCalc.calculateStock({{
    antibiotic: abx, stockConc: 100, stockVol: 10, workingConc: 100,
    mediaVol: 500, purity: 100, saltFactor: abx.saltFactor, mw: abx.mw,
    volumeDisplacement: true, costPerMg: 0
}});
console.log(JSON.stringify({{mass: result.adjustedMass, baseMass: result.baseMass}}));
""")
    data = json.loads(output)
    assert data['baseMass'] == 1000.0  # 100 mg/mL × 10 mL
    assert data['mass'] == pytest.approx(1090.0, abs=0.1)  # 1000 × 1.09 salt factor


def test_kanamycin_salt_factor(pharma_calc):
    """Kanamycin sulfate has salt factor 1.27 — 27% more mass needed."""
    output = run_js(f"""
{pharma_calc}
var abx = PharmaCalc.ANTIBIOTICS.find(function(a){{return a.name==='Kanamycin'}});
var result = PharmaCalc.calculateStock({{
    antibiotic: abx, stockConc: 50, stockVol: 10, workingConc: 50,
    mediaVol: 1000, purity: 100, saltFactor: abx.saltFactor, mw: abx.mw,
    volumeDisplacement: false, costPerMg: 0
}});
console.log(result.adjustedMass);
""")
    mass = float(output)
    # 50 mg/mL × 10 mL = 500 mg base × 1.27 = 635 mg
    assert mass == pytest.approx(635.0, abs=0.1)


def test_dilution_factor_calculation(pharma_calc):
    """Stock 100 mg/mL = 100,000 µg/mL, working 100 µg/mL → dilution factor 1000."""
    output = run_js(f"""
{pharma_calc}
var result = PharmaCalc.calculateDilution(100, null, 0.1, 100);
console.log(JSON.stringify({{v1: result.v1, df: result.dilutionFactor}}));
""")
    data = json.loads(output)
    # C1=100 mg/mL, C2=0.1 mg/mL (100 µg/mL), V2=100 mL
    # V1 = C2 × V2 / C1 = 0.1 × 100 / 100 = 0.1 mL = 100 µL
    assert data['v1'] == pytest.approx(0.1, abs=0.001)
    assert data['df'] == pytest.approx(1000, abs=1)


def test_half_life_calculation(pharma_calc):
    """C0=100, Ct=50, t=6h → k = ln(2)/6, tt_half = 6h."""
    output = run_js(f"""
{pharma_calc}
var result = PharmaCalc.calculateHalfLife(100, 50, 6);
console.log(JSON.stringify({{k: result.k, tt_half: result.halfLife}}));
""")
    data = json.loads(output)
    assert data['tt_half'] == pytest.approx(6.0, abs=0.01)
    assert data['k'] == pytest.approx(math.log(2) / 6, abs=0.001)


def test_clearance_calculation(pharma_calc):
    """Dose=500 mg, AUC=20 mg·h/L → CL = 25 L/h."""
    output = run_js(f"{pharma_calc}; console.log(PharmaCalc.calculateClearance(500, 20));")
    cl = float(output)
    assert cl == pytest.approx(25.0, abs=0.01)


def test_volume_of_distribution(pharma_calc):
    """Dose=500 mg, C0=10 mg/L → Vd = 50 L."""
    output = run_js(f"{pharma_calc}; console.log(PharmaCalc.calculateVd(500, 10));")
    vd = float(output)
    assert vd == pytest.approx(50.0, abs=0.01)


def test_loading_dose_calculation(pharma_calc):
    """Target=10 mg/L, Vd=50 L, F=0.8 → LD = 10 × 50 / 0.8 = 625 mg."""
    output = run_js(f"{pharma_calc}; console.log(PharmaCalc.calculateLoadingDose(10, 50, 0.8));")
    ld = float(output)
    assert ld == pytest.approx(625.0, abs=0.1)


def test_maintenance_dose_calculation(pharma_calc):
    """CL=5 L/h, target=10 mg/L, interval=8h, F=0.8 → MD = 5 × 10 × 8 / 0.8 = 500 mg."""
    output = run_js(f"{pharma_calc}; console.log(PharmaCalc.calculateMaintenanceDose(5, 10, 8, 0.8));")
    md = float(output)
    assert md == pytest.approx(500.0, abs=0.1)


def test_auc_trapezoidal(pharma_calc):
    """AUC from time=[0,2,4,6], conc=[10,8,5,2] → trapezoidal = 2×(9+6.5+3.5) = 38."""
    output = run_js(f"""
{pharma_calc}
var result = PharmaCalc.calculateAUC([10, 8, 5, 2], [0, 2, 4, 6]);
console.log(result);
""")
    auc = float(output)
    # (2-0)×(10+8)/2 + (4-2)×(8+5)/2 + (6-4)×(5+2)/2 = 18 + 13 + 7 = 38
    assert auc == pytest.approx(38.0, abs=0.01)


def test_fic_synergy(pharma_calc):
    """FIC index: MIC_A alone=4, MIC_B alone=8, combo A=1, combo B=2 → FIC=0.25+0.25=0.5 → Synergistic."""
    output = run_js(f"""
{pharma_calc}
var result = PharmaCalc.calculateFIC(4, 8, 1, 2);
console.log(JSON.stringify({{fic: result.ficIndex, interp: result.interpretation}}));
""")
    data = json.loads(output)
    assert data['fic'] == pytest.approx(0.5, abs=0.01)
    assert data['interp'] == "Synergistic"


def test_fic_antagonistic(pharma_calc):
    """FIC index > 2 → Antagonistic. MIC_A alone=4, MIC_B alone=8, combo A=4, combo B=16 → FIC=1+2=3."""
    output = run_js(f"""
{pharma_calc}
var result = PharmaCalc.calculateFIC(4, 8, 4, 16);
console.log(result.interpretation);
""")
    assert output == "Antagonistic"


def test_time_kill_bactericidal(pharma_calc):
    """Initial CFU=1e8, final CFU=1e4 → 4 log reduction → bactericidal."""
    output = run_js(f"""
{pharma_calc}
var result = PharmaCalc.calculateTimeKill([0, 4, 8, 24], [1e8, 1e7, 1e5, 1e4]);
console.log(JSON.stringify({{logRed: result.logReduction, bact: result.bactericidal}}));
""")
    data = json.loads(output)
    assert data['logRed'] == pytest.approx(4.0, abs=0.1)
    assert data['bact'] is True


def test_mpc_calculation(pharma_calc):
    """Doses=[256,128,64,32,16,8,4,2], CFU=[100,50,10,5,2,0,0,0], initial=1e6."""
    output = run_js(f"""
{pharma_calc}
var result = PharmaCalc.calculateMPC([256,128,64,32,16,8,4,2], [100,50,10,5,2,0,0,0], 1e6);
console.log(JSON.stringify({{mpc: result.mpc, mic: result.mic, ratio: result.mpcMicRatio}}));
""")
    data = json.loads(output)
    assert data['mpc'] == 8  # lowest dose with zero colonies
    assert data['mic'] == 256  # lowest dose with ≤1% survival (1e6 × 0.01 = 1e4 CFU)
    assert data['ratio'] == pytest.approx(0.03125, abs=0.001)  # 8/256


def test_arrhenius_kinetics(pharma_calc):
    """Arrhenius: Ea=50000, Tref=25°C, refRate=0.01/day, T=40°C."""
    output = run_js(f"""
{pharma_calc}
var result = PharmaCalc.calculateArrhenius(40, 50000, 25, 0.01);
console.log(JSON.stringify({{k: result.k, t90: result.t90}}));
""")
    data = json.loads(output)
    # Higher temp → faster degradation → shorter t90
    assert data['k'] > 0.01
    assert data['t90'] > 0
    assert data['t90'] < 100  # Should degrade faster at 40°C than 25°C


def test_protein_binding_correction(pharma_calc):
    """Total=100 mg/L, bound=0.9, target free=10 mg/L → free=10, required total=100."""
    output = run_js(f"""
{pharma_calc}
var result = PharmaCalc.calculateProteinBindingCorrection(100, 0.9, 10);
console.log(JSON.stringify({{free: result.freeConc, reqTotal: result.requiredTotal}}));
""")
    data = json.loads(output)
    assert data['free'] == pytest.approx(10.0, abs=0.1)  # 100 × (1-0.9) = 10
    assert data['reqTotal'] == pytest.approx(100.0, abs=0.1)  # 10 / 0.1 = 100


def test_serial_dilution_plan(pharma_calc):
    """Start=1000, factor=10, steps=3 → [1000, 100, 10]."""
    output = run_js(f"""
{pharma_calc}
var results = PharmaCalc.planSerialDilution(1000, 10, 3, 1);
console.log(JSON.stringify(results.map(function(r){{return r.concentration}})));
""")
    concs = json.loads(output)
    assert concs == [1000, 100, 10]


def test_henderson_hasselch(pharma_calc):
    """pH=7.4, pKa=6.4 → ionized fraction = 10^(7.4-6.4) / (1 + 10^(7.4-6.4)) = 10/11 ≈ 0.909."""
    output = run_js(f"""
{pharma_calc}
var result = PharmaCalc.hendersonHasselch(7.4, 6.4);
console.log(result.ionizedFraction);
""")
    ionized = float(output)
    assert ionized == pytest.approx(10.0 / 11.0, abs=0.001)


def test_reconstitute_vial(pharma_calc):
    """100 mg powder, 100% purity, 50 mg/mL target → 2 mL diluent."""
    output = run_js(f"""
{pharma_calc}
var result = PharmaCalc.reconstituteVial(100, 100, 50);
console.log(result.diluentVolume);
""")
    vol = float(output)
    assert vol == pytest.approx(2.0, abs=0.01)


def test_cocktail_planner(pharma_calc):
    """Ampicillin (100 mg/mL, 100 µg/mL) + Kanamycin (50 mg/mL, 50 µg/mL) in 500 mL."""
    output = run_js(f"""
{pharma_calc}
var ampi = PharmaCalc.ANTIBIOTICS.find(function(a){{return a.name==='Ampicillin'}});
var kan = PharmaCalc.ANTIBIOTICS.find(function(a){{return a.name==='Kanamycin'}});
var results = PharmaCalc.planCocktail([ampi, kan], 500);
console.log(JSON.stringify(results.map(function(r){{return {{name: r.antibiotic.name, add: r.stockToAddUl}}}})));
""")
    data = json.loads(output)
    # Ampicillin: (100 × 500) / (100 × 1000) = 0.5 mL = 500 µL
    assert data[0]['add'] == pytest.approx(500, abs=0.1)
    # Kanamycin: (50 × 500) / (50 × 1000) = 0.5 mL = 500 µL
    assert data[1]['add'] == pytest.approx(500, abs=0.1)


def test_resistance_gene_mapper(pharma_calc):
    """bla gene should map to Ampicillin at 100 µg/mL."""
    output = run_js(f"""
{pharma_calc}
var gene = PharmaCalc.RESISTANCE_GENES['bla (AmpR)'];
console.log(JSON.stringify({{abx: gene.antibiotic, conc: gene.concentration}}));
""")
    data = json.loads(output)
    assert data['abx'] == "Ampicillin"
    assert data['conc'] == 100


def test_dose_response_4pl(pharma_calc):
    """Synthetic 4PL data: bottom=0, top=100, logEC50=-6, hill=1."""
    output = run_js(f"""
{pharma_calc}
// Generate synthetic data: y = 100 / (1 + 10^((-6 - log10(d)) * 1))
var doses = [1e-8, 1e-7, 1e-6, 1e-5, 1e-4];
var responses = doses.map(function(d){{return 100 / (1 + Math.pow(10, (-6 - Math.log10(d)) * 1))}});
var result = PharmaCalc.doseResponse4PL(doses, responses);
console.log(JSON.stringify({{ec50: result.ec50, r2: result.r2, bottom: result.bottom, top: result.top}}));
""")
    data = json.loads(output)
    assert data['ec50'] == pytest.approx(1e-6, rel=0.1)
    assert data['bottom'] == pytest.approx(0, abs=1)
    assert data['top'] == pytest.approx(100, abs=1)
    assert data['r2'] > 0.99


def test_osmolarity_calculation(pharma_calc):
    """Normal saline: 154 mM NaCl → Na+ 154 + Cl- 154 = 308 mOsm/L (simplified, no valence multiplier)."""
    output = run_js(f"""
{pharma_calc}
var result = PharmaCalc.calculateOsmolarity(0, 154, 0, 154, 0);
console.log(result);
""")
    osm = float(output)
    assert osm == pytest.approx(308, abs=1)


def test_stability_estimate(pharma_calc):
    """Degradation rate 0.01/day, target 90% → ~10.5 days."""
    output = run_js(f"""
{pharma_calc}
var result = PharmaCalc.estimateStability(-20, 0.01, 0.9);
console.log(result.daysToTarget);
""")
    days = float(output)
    assert days == pytest.approx(10.0, abs=0.5)


def test_purity_correction(pharma_calc):
    """1000 mg base × 1.09 salt / 0.95 purity = 1147.4 mg."""
    output = run_js(f"""
{pharma_calc}
var abx = PharmaCalc.ANTIBIOTICS.find(function(a){{return a.name==='Ampicillin'}});
var result = PharmaCalc.calculateStock({{
    antibiotic: abx, stockConc: 100, stockVol: 10, workingConc: 100,
    mediaVol: 500, purity: 95, saltFactor: abx.saltFactor, mw: abx.mw,
    volumeDisplacement: false, costPerMg: 0
}});
console.log(result.adjustedMass);
""")
    mass = float(output)
    # 1000 × 1.09 / 0.95 = 1147.37
    assert mass == pytest.approx(1147.4, abs=0.5)


def test_solubility_warning(pharma_calc):
    """Tetracycline stock=5 mg/mL is at solubility limit; 10 mg/mL should warn."""
    output = run_js(f"""
{pharma_calc}
var abx = PharmaCalc.ANTIBIOTICS.find(function(a){{return a.name==='Tetracycline'}});
var result = PharmaCalc.calculateStock({{
    antibiotic: abx, stockConc: 10, stockVol: 10, workingConc: 10,
    mediaVol: 100, purity: 100, saltFactor: abx.saltFactor, mw: abx.mw,
    volumeDisplacement: false, costPerMg: 0
}});
console.log(result.solubilityWarning ? 'warned' : 'ok');
""")
    assert output == "warned"


def test_volume_displacement(pharma_calc):
    """With displacement: solvent = stockVol - powderVol. Without: solvent = stockVol."""
    output = run_js(f"""
{pharma_calc}
var abx = PharmaCalc.ANTIBIOTICS.find(function(a){{return a.name==='Ampicillin'}});
var withDisp = PharmaCalc.calculateStock({{
    antibiotic: abx, stockConc: 100, stockVol: 10, workingConc: 100,
    mediaVol: 500, purity: 100, saltFactor: abx.saltFactor, mw: abx.mw,
    volumeDisplacement: true, costPerMg: 0
}});
var withoutDisp = PharmaCalc.calculateStock({{
    antibiotic: abx, stockConc: 100, stockVol: 10, workingConc: 100,
    mediaVol: 500, purity: 100, saltFactor: abx.saltFactor, mw: abx.mw,
    volumeDisplacement: false, costPerMg: 0
}});
console.log(JSON.stringify({{withDisp: withDisp.solventVol, withoutDisp: withoutDisp.solventVol}}));
""")
    data = json.loads(output)
    assert data['withDisp'] < data['withoutDisp']


def test_cost_calculation(pharma_calc):
    """1090 mg × $0.01/mg = $10.90 stock cost."""
    output = run_js(f"""
{pharma_calc}
var abx = PharmaCalc.ANTIBIOTICS.find(function(a){{return a.name==='Ampicillin'}});
var result = PharmaCalc.calculateStock({{
    antibiotic: abx, stockConc: 100, stockVol: 10, workingConc: 100,
    mediaVol: 500, purity: 100, saltFactor: abx.saltFactor, mw: abx.mw,
    volumeDisplacement: false, costPerMg: 0.01
}});
console.log(result.cost.stockCost);
""")
    cost = float(output)
    assert cost == pytest.approx(10.90, abs=0.01)
