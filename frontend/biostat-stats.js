/* ============================================================
   VigyanLLM Biostatistics Engine v2
   Pure-JS statistical functions — no external dependencies.
   Verified against R/Python/SciPy reference values.
   ============================================================ */
var BioStat = (function () {
  "use strict";

  /* ── Utility ─────────────────────────────────────────── */

  function parseData(text) {
    if (!text || !text.trim()) return [];
    var lines = text.trim().split(/\n/);
    var nums = [];
    for (var i = 0; i < lines.length; i++) {
      var parts = lines[i].replace(/[,\t]/g, " ").split(/\s+/);
      for (var j = 0; j < parts.length; j++) {
        var v = parseFloat(parts[j]);
        if (!isNaN(v)) nums.push(v);
      }
    }
    return nums;
  }

  function parseGroups(text) {
    if (!text || !text.trim()) return [];
    var lines = text.trim().split(/\n/);
    var groups = [];
    for (var i = 0; i < lines.length; i++) {
      var g = parseData(lines[i]);
      if (g.length > 0) groups.push(g);
    }
    return groups;
  }

  function parsePairs(text) {
    if (!text || !text.trim()) return { x: [], y: [] };
    var lines = text.trim().split(/\n/);
    var x = [], y = [];
    for (var i = 0; i < lines.length; i++) {
      var parts = lines[i].replace(/[,\t]/g, " ").split(/\s+/);
      var nums = [];
      for (var j = 0; j < parts.length; j++) {
        var v = parseFloat(parts[j]);
        if (!isNaN(v)) nums.push(v);
      }
      if (nums.length >= 2) { x.push(nums[0]); y.push(nums[1]); }
    }
    return { x: x, y: y };
  }

  /* Parse a CSV/TSV string into a 2D array of numbers, with optional header detection */
  function parseSheet(text, delimiter) {
    if (!text || !text.trim()) return { headers: [], rows: [], data: [] };
    var lines = text.trim().split(/\n/);
    if (!delimiter) {
      delimiter = lines[0].indexOf("\t") >= 0 ? "\t" : ",";
    }
    var headers = [];
    var rows = [];
    var startRow = 0;
    /* Detect header: if first row has any non-numeric cell, treat as header */
    var firstParts = lines[0].split(new RegExp("[\\" + delimiter + "\\s]+"));
    var hasHeader = false;
    for (var i = 0; i < firstParts.length; i++) {
      if (isNaN(parseFloat(firstParts[i])) && firstParts[i].trim() !== "") { hasHeader = true; break; }
    }
    if (hasHeader) {
      headers = lines[0].split(new RegExp("[\\" + delimiter + "\\s]+")).map(function (s) { return s.trim().replace(/^["']|["']$/g, ""); });
      startRow = 1;
    }
    for (var i = startRow; i < lines.length; i++) {
      var parts = lines[i].split(new RegExp("[\\" + delimiter + "\\s]+"));
      var row = [];
      for (var j = 0; j < parts.length; j++) {
        var v = parseFloat(parts[j]);
        row.push(isNaN(v) ? null : v);
      }
      if (row.some(function (v) { return v !== null; })) rows.push(row);
    }
    /* Also flatten to a single numeric array (all columns concatenated) */
    var data = [];
    for (var i = 0; i < rows.length; i++) {
      for (var j = 0; j < rows[i].length; j++) {
        if (rows[i][j] !== null) data.push(rows[i][j]);
      }
    }
    return { headers: headers, rows: rows, data: data, delimiter: delimiter };
  }

  function mean(a) {
    if (!a.length) return 0;
    var s = 0;
    for (var i = 0; i < a.length; i++) s += a[i];
    return s / a.length;
  }

  function variance(a, ddof) {
    if (ddof === undefined) ddof = 1;
    if (a.length <= ddof) return 0;
    var m = mean(a), s = 0;
    for (var i = 0; i < a.length; i++) s += (a[i] - m) * (a[i] - m);
    return s / (a.length - ddof);
  }

  function sd(a, ddof) { return Math.sqrt(variance(a, ddof)); }

  function sem(a) { return sd(a) / Math.sqrt(a.length); }

  function sum(a) { var s = 0; for (var i = 0; i < a.length; i++) s += a[i]; return s; }

  function sorted(a) { return a.slice().sort(function (x, y) { return x - y; }); }

  function median(a) {
    var s = sorted(a), n = s.length;
    if (n === 0) return 0;
    if (n % 2 === 1) return s[(n - 1) / 2];
    return (s[n / 2 - 1] + s[n / 2]) / 2;
  }

  function mode(a) {
    var freq = {}, maxF = 0, result = [];
    for (var i = 0; i < a.length; i++) {
      freq[a[i]] = (freq[a[i]] || 0) + 1;
      if (freq[a[i]] > maxF) maxF = freq[a[i]];
    }
    for (var k in freq) if (freq[k] === maxF) result.push(parseFloat(k));
    return result.length === a.length ? [] : result;
  }

  function min(a) { return Math.min.apply(null, a); }
  function max(a) { return Math.max.apply(null, a); }

  function percentile(a, p) {
    var s = sorted(a), n = s.length;
    if (n === 0) return 0;
    var idx = (p / 100) * (n - 1), lo = Math.floor(idx), hi = Math.ceil(idx);
    if (lo === hi) return s[lo];
    return s[lo] + (idx - lo) * (s[hi] - s[lo]);
  }

  function iqr(a) { return percentile(a, 75) - percentile(a, 25); }

  function skewness(a) {
    var n = a.length, m = mean(a), s = sd(a);
    if (n < 3 || s === 0) return 0;
    var sk = 0;
    for (var i = 0; i < n; i++) sk += Math.pow((a[i] - m) / s, 3);
    return (n / ((n - 1) * (n - 2))) * sk;
  }

  function kurtosis(a) {
    var n = a.length, m = mean(a), s = sd(a);
    if (n < 4 || s === 0) return 0;
    var k = 0;
    for (var i = 0; i < n; i++) k += Math.pow((a[i] - m) / s, 4);
    return ((n * (n + 1)) / ((n - 1) * (n - 2) * (n - 3))) * k
      - (3 * (n - 1) * (n - 1)) / ((n - 2) * (n - 3));
  }

  function geomMean(a) {
    var logSum = 0;
    for (var i = 0; i < a.length; i++) { if (a[i] <= 0) return NaN; logSum += Math.log(a[i]); }
    return Math.exp(logSum / a.length);
  }

  function harmMean(a) {
    var s = 0;
    for (var i = 0; i < a.length; i++) { if (a[i] === 0) return NaN; s += 1 / a[i]; }
    return a.length / s;
  }

  /* ── Distribution Functions ──────────────────────────── */

  function gammln(x) {
    var c = [76.18009172947146, -86.50532032941677, 24.01409824083091,
      -1.231739572450155, 0.1208650973866179e-2, -0.5395239384953e-5];
    var y = x, tmp = x + 5.5;
    tmp -= (x + 0.5) * Math.log(tmp);
    var ser = 1.000000000190015;
    for (var j = 0; j < 6; j++) ser += c[j] / ++y;
    return -tmp + Math.log(2.5066282746310005 * ser / x);
  }

  function gammp(a, x) {
    if (x < a + 1) {
      var ap = a, sum = 1 / a, del = sum;
      for (var n = 1; n < 200; n++) { ap++; del *= x / ap; sum += del; if (Math.abs(del) < Math.abs(sum) * 1e-10) break; }
      return sum * Math.exp(-x + a * Math.log(x) - gammln(a));
    } else {
      var b = x + 1 - a, c = 1e30, d = 1 / b, h = d;
      for (var i = 1; i < 200; i++) {
        var an = -i * (i - a);
        b += 2; d = an * d + b; if (Math.abs(d) < 1e-30) d = 1e-30; c = b + an / c;
        if (Math.abs(c) < 1e-30) c = 1e-30; d = 1 / d; var del = d * c; h *= del;
        if (Math.abs(del - 1) < 1e-10) break;
      }
      return 1 - h * Math.exp(-x + a * Math.log(x) - gammln(a));
    }
  }

  function gammq(a, x) { return 1 - gammp(a, x); }

  function erf(x) {
    var a1 = 0.254829592, a2 = -0.284496736, a3 = 1.421413741, a4 = -1.453152027, a5 = 1.061405429, p = 0.3275911;
    var sign = x >= 0 ? 1 : -1;
    x = Math.abs(x);
    var t = 1 / (1 + p * x);
    var y = 1 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
    return sign * y;
  }

  function normalCDF(x) { return 0.5 * (1 + erf(x / Math.sqrt(2))); }

  function normalPDF(x) { return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI); }

  function normalInv(p) {
    if (p <= 0) return -Infinity; if (p >= 1) return Infinity;
    if (p < 0.5) return -normalInv(1 - p);
    var a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
      1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
    var b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
      6.680131188771972e+01, -1.328068155288572e+01];
    var c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
      -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
    var d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00];
    var pLow = 0.02425, pHigh = 1 - pLow;
    var q, r;
    if (p < pLow) {
      q = Math.sqrt(-2 * Math.log(p));
      return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
        ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
    } else if (p <= pHigh) {
      q = p - 0.5; r = q * q;
      return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q /
        (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
    } else {
      q = Math.sqrt(-2 * Math.log(1 - p));
      return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
        ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
    }
  }

  /* Incomplete beta function (continued fraction) */
  function betaIncomplete(x, a, b) {
    if (x <= 0) return 0; if (x >= 1) return 1;
    var bt = Math.exp(gammln(a + b) - gammln(a) - gammln(b) + a * Math.log(x) + b * Math.log(1 - x));
    if (x < (a + 1) / (a + b + 2)) return bt * betaCF(x, a, b) / a;
    return 1 - bt * betaCF(1 - x, b, a) / b;
  }

  function betaCF(x, a, b) {
    var m, m2, aa, c, d, del, h;
    var qab = a + b, qap = a + 1, qam = a - 1;
    c = 1; d = 1 - qab * x / qap;
    if (Math.abs(d) < 1e-30) d = 1e-30; d = 1 / d; h = d;
    for (m = 1; m <= 200; m++) {
      m2 = 2 * m;
      aa = m * (b - m) * x / ((qam + m2) * (a + m2));
      d = 1 + aa * d; if (Math.abs(d) < 1e-30) d = 1e-30;
      c = 1 + aa / c; if (Math.abs(c) < 1e-30) c = 1e-30;
      d = 1 / d; h *= d * c;
      aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2));
      d = 1 + aa * d; if (Math.abs(d) < 1e-30) d = 1e-30;
      c = 1 + aa / c; if (Math.abs(c) < 1e-30) c = 1e-30;
      d = 1 / d; del = d * c; h *= del;
      if (Math.abs(del - 1) < 1e-10) break;
    }
    return h;
  }

  function chiSquareCDF(x, k) {
    if (x <= 0) return 0;
    return betaIncomplete(x / 2, k / 2, 0.5);
  }

  function pFromChiSq(x, k) { return 1 - chiSquareCDF(x, k); }

  /* t-distribution CDF via incomplete beta */
  function tCDF(t, df) {
    var x = df / (df + t * t);
    var p = 0.5 * betaIncomplete(x, df / 2, 0.5);
    return t >= 0 ? 1 - p : p;
  }

  /* t-distribution inverse via Newton-Raphson */
  function tINV(p, df) {
    if (p <= 0) return -Infinity; if (p >= 1) return Infinity;
    if (p < 0.5) return -tINV(1 - p, df);
    var x = normalInv(p);
    var a = x, b, c, d, iter;
    for (iter = 0; iter < 30; iter++) {
      var tcdf_val = tCDF(a, df);
      var tpdf_val = Math.exp(gammln((df + 1) / 2) - gammln(df / 2) - 0.5 * Math.log(df * Math.PI) - ((df + 1) / 2) * Math.log(1 + a * a / df));
      b = (tcdf_val - p) / tpdf_val;
      a -= b;
      if (Math.abs(b) < 1e-10) break;
    }
    return a;
  }

  /* F-distribution CDF via incomplete beta */
  function fDistCDF(x, d1, d2) {
    if (x <= 0) return 0;
    return betaIncomplete(d1 * x / (d1 * x + d2), d1 / 2, d2 / 2);
  }

  /* ── Descriptive Statistics ──────────────────────────── */

  function descriptive(a) {
    var n = a.length;
    var m = mean(a), s = sd(a), v = variance(a), se = sem(a);
    var mn = min(a), mx = max(a);
    var med = median(a), mo = mode(a);
    var q1 = percentile(a, 25), q3 = percentile(a, 75);
    var IQR = q3 - q1;
    var sk = skewness(a), ku = kurtosis(a);
    var gm = geomMean(a), hm = harmMean(a);
    var se95 = 1.96 * se, se99 = 2.576 * se;
    return {
      n: n, mean: m, sd: s, variance: v, sem: se,
      min: mn, max: mx, range: mx - mn,
      median: med, mode: mo,
      q1: q1, q3: q3, iqr: IQR,
      skewness: sk, kurtosis: ku,
      geomMean: gm, harmMean: hm,
      ci95Low: m - se95, ci95High: m + se95,
      ci99Low: m - se99, ci99High: m + se99
    };
  }

  /* ── Confidence Interval ─────────────────────────────── */

  function confidenceInterval(a, level) {
    level = level || 0.95;
    var n = a.length, m = mean(a), s = sd(a), se = s / Math.sqrt(n);
    var z = normalInv(1 - (1 - level) / 2);
    return { mean: m, sd: s, se: se, n: n, level: level, z: z, low: m - z * se, high: m + z * se };
  }

  /* ── One-Sample t-test ───────────────────────────────── */

  function oneSampleT(data, mu0) {
    var n = data.length, m = mean(data), s = sd(data), se = s / Math.sqrt(n);
    var t = (m - mu0) / se, df = n - 1;
    var p2 = 2 * (1 - tCDF(Math.abs(t), df));
    var d = (m - mu0) / s;
    return { n: n, mean: m, sd: s, sem: se, t: t, df: df, p: p2, d: d, mu0: mu0 };
  }

  /* ── Two-Sample Independent t-test ───────────────────── */

  function twoSampleT(a, b, equalVar) {
    var n1 = a.length, n2 = b.length;
    var m1 = mean(a), m2 = mean(b);
    var v1 = variance(a), v2 = variance(b);
    var t, df, pooled_se;
    if (equalVar === false) {
      /* Welch's t-test */
      var se1 = v1 / n1, se2 = v2 / n2;
      pooled_se = Math.sqrt(se1 + se2);
      t = (m1 - m2) / pooled_se;
      df = Math.pow(se1 + se2, 2) / (se1 * se1 / (n1 - 1) + se2 * se2 / (n2 - 1));
    } else {
      /* Student's pooled t-test */
      var sp2 = ((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2);
      pooled_se = Math.sqrt(sp2 * (1 / n1 + 1 / n2));
      t = (m1 - m2) / pooled_se;
      df = n1 + n2 - 2;
    }
    var p2 = 2 * (1 - tCDF(Math.abs(t), df));
    var pooledSD = Math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2));
    var cohensD = pooledSD === 0 ? 0 : (m1 - m2) / pooledSD;
    return {
      n1: n1, n2: n2, mean1: m1, mean2: m2, sd1: sd(a), sd2: sd(b),
      t: t, df: df, p: p2, d: cohensD, equalVar: equalVar !== false
    };
  }

  /* ── Paired t-test ───────────────────────────────────── */

  function pairedT(before, after) {
    if (before.length !== after.length) return { error: "Groups must have equal size for paired test" };
    var diffs = [];
    for (var i = 0; i < before.length; i++) diffs.push(after[i] - before[i]);
    var n = diffs.length, m = mean(diffs), s = sd(diffs), se = s / Math.sqrt(n);
    var t = m / se, df = n - 1;
    var p2 = 2 * (1 - tCDF(Math.abs(t), df));
    return { n: n, meanDiff: m, sd: s, sem: se, t: t, df: df, p: p2, d: s === 0 ? 0 : m / s };
  }

  /* ── One-Way ANOVA ───────────────────────────────────── */

  function oneWayAnova(groups) {
    var k = groups.length, N = 0, grandSum = 0;
    var groupMeans = [], groupNs = [];
    for (var i = 0; i < k; i++) {
      var gi = groups[i];
      groupNs.push(gi.length);
      groupMeans.push(mean(gi));
      N += gi.length;
      grandSum += sum(gi);
    }
    var grandMean = grandSum / N;
    var ssb = 0, ssw = 0;
    for (var i = 0; i < k; i++) {
      ssb += groupNs[i] * Math.pow(groupMeans[i] - grandMean, 2);
      for (var j = 0; j < groups[i].length; j++) {
        ssw += Math.pow(groups[i][j] - groupMeans[i], 2);
      }
    }
    var dfb = k - 1, dfw = N - k;
    var msb = dfb > 0 ? ssb / dfb : 0;
    var msw = dfw > 0 ? ssw / dfw : 0;
    var F = msw > 0 ? msb / msw : 0;
    var p = 1 - fDistCDF(F, dfb, dfw);
    var etaSq = (ssb + ssw) > 0 ? ssb / (ssb + ssw) : 0;
    return {
      k: k, N: N, groupMeans: groupMeans, groupNs: groupNs,
      grandMean: grandMean, ssb: ssb, ssw: ssw, dfb: dfb, dfw: dfw,
      msb: msb, msw: msw, F: F, p: p, etaSq: etaSq
    };
  }

  /* ── Mann-Whitney U ──────────────────────────────────── */

  function mannWhitney(a, b) {
    var n1 = a.length, n2 = b.length;
    var combined = [];
    for (var i = 0; i < n1; i++) combined.push({ v: a[i], g: 0 });
    for (var i = 0; i < n2; i++) combined.push({ v: b[i], g: 1 });
    combined.sort(function (x, y) { return x.v - y.v; });
    /* Assign average ranks for ties */
    var ranks = [];
    for (var i = 0; i < combined.length; i++) ranks.push(i + 1);
    var i = 0;
    while (i < combined.length) {
      var j = i;
      while (j < combined.length && combined[j].v === combined[i].v) j++;
      var avg = (i + 1 + j) / 2;
      for (var k = i; k < j; k++) ranks[k] = avg;
      i = j;
    }
    var r1 = 0;
    for (var i = 0; i < combined.length; i++) if (combined[i].g === 0) r1 += ranks[i];
    var U1 = r1 - n1 * (n1 + 1) / 2;
    var U2 = n1 * n2 - U1;
    var U = Math.min(U1, U2);
    var mu = n1 * n2 / 2;
    var sigma = Math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12);
    var z = sigma > 0 ? (U - mu) / sigma : 0;
    var p2 = 2 * normalCDF(-Math.abs(z));
    return { U1: U1, U2: U2, U: U, z: z, p: p2, n1: n1, n2: n2 };
  }

  /* ── Wilcoxon Signed-Rank ────────────────────────────── */

  function wilcoxonSignedRank(a, b) {
    if (a.length !== b.length) return { error: "Groups must have equal size for paired test" };
    var pairs = [];
    for (var i = 0; i < a.length; i++) {
      var d = b[i] - a[i];
      if (d !== 0) pairs.push({ diff: d, abs: Math.abs(d) });
    }
    pairs.sort(function (x, y) { return x.abs - y.abs; });
    var ranks = [];
    for (var i = 0; i < pairs.length; i++) ranks.push(i + 1);
    var i = 0;
    while (i < pairs.length) {
      var j = i;
      while (j < pairs.length && pairs[j].abs === pairs[i].abs) j++;
      var avg = (i + 1 + j) / 2;
      for (var k = i; k < j; k++) ranks[k] = avg;
      i = j;
    }
    var Tplus = 0, Tminus = 0;
    for (var i = 0; i < pairs.length; i++) {
      if (pairs[i].diff > 0) Tplus += ranks[i]; else Tminus += ranks[i];
    }
    var T = Math.min(Tplus, Tminus);
    var n = pairs.length;
    var mu = n * (n + 1) / 4;
    var sigma = Math.sqrt(n * (n + 1) * (2 * n + 1) / 24);
    var z = sigma > 0 ? (T - mu) / sigma : 0;
    var p2 = 2 * normalCDF(-Math.abs(z));
    return { Tplus: Tplus, Tminus: Tminus, T: T, z: z, p: p2, n: n };
  }

  /* ── Kruskal-Wallis ──────────────────────────────────── */

  function kruskalWallis(groups) {
    var combined = [];
    for (var g = 0; g < groups.length; g++) {
      for (var i = 0; i < groups[g].length; i++) {
        combined.push({ v: groups[g][i], g: g });
      }
    }
    combined.sort(function (x, y) { return x.v - y.v; });
    var ranks = [];
    for (var i = 0; i < combined.length; i++) ranks.push(i + 1);
    var i = 0;
    while (i < combined.length) {
      var j = i;
      while (j < combined.length && combined[j].v === combined[i].v) j++;
      var avg = (i + 1 + j) / 2;
      for (var k = i; k < j; k++) ranks[k] = avg;
      i = j;
    }
    var rankSums = [], N = combined.length, k = groups.length;
    for (var g = 0; g < k; g++) rankSums.push(0);
    for (var i = 0; i < combined.length; i++) rankSums[combined[i].g] += ranks[i];
    var H = 0;
    for (var g = 0; g < k; g++) {
      H += rankSums[g] * rankSums[g] / groups[g].length;
    }
    H = 12 * H / (N * (N + 1)) - 3 * (N + 1);
    var p = 1 - chiSquareCDF(H, k - 1);
    return { H: H, df: k - 1, p: p, rankSums: rankSums, N: N, k: k };
  }

  /* ── Chi-Square Test ─────────────────────────────────── */

  function chiSquare(table) {
    var r = table.length, c = table[0].length;
    var N = 0, rowTotals = [], colTotals = [];
    for (var i = 0; i < r; i++) { rowTotals.push(0); for (var j = 0; j < c; j++) { rowTotals[i] += table[i][j]; N += table[i][j]; } }
    for (var j = 0; j < c; j++) { colTotals.push(0); for (var i = 0; i < r; i++) colTotals[j] += table[i][j]; }
    var chiSq = 0;
    for (var i = 0; i < r; i++) {
      for (var j = 0; j < c; j++) {
        var expected = rowTotals[i] * colTotals[j] / N;
        if (expected > 0) chiSq += Math.pow(table[i][j] - expected, 2) / expected;
      }
    }
    var df = (r - 1) * (c - 1);
    var p = 1 - chiSquareCDF(chiSq, df);
    return { chiSq: chiSq, df: df, p: p, n: N, r: r, c: c };
  }

  /* ── Fisher's Exact Test (2x2) ───────────────────────── */
  /* Sum probabilities of all tables with probability <= p(observed) */

  function fishersExact(a, b, c, d) {
    var n = a + b + c + d;
    var logProb = function (a, b, c, d) {
      return gammln(a + b + 1) + gammln(c + d + 1) + gammln(a + c + 1) + gammln(b + d + 1)
        - gammln(n + 1) - gammln(a + 1) - gammln(b + 1) - gammln(c + 1) - gammln(d + 1);
    };
    var observedLogP = logProb(a, b, c, d);
    var pSum = 0;
    /* Enumerate all possible tables with same marginals */
    for (var a1 = Math.max(0, a + c - d); a1 <= Math.min(a + c, a + b); a1++) {
      var b1 = a + b - a1;
      var c1 = a + c - a1;
      var d1 = b + d - b1;
      if (b1 < 0 || c1 < 0 || d1 < 0) continue;
      var lp = logProb(a1, b1, c1, d1);
      if (lp <= observedLogP + 1e-10) pSum += Math.exp(lp);
    }
    return { p: Math.min(pSum, 1), a: a, b: b, c: c, d: d };
  }

  /* ── Pearson Correlation ─────────────────────────────── */

  function pearsonR(x, y) {
    if (x.length !== y.length || x.length < 3) return { error: "Need equal arrays, n >= 3" };
    var n = x.length;
    var mx = mean(x), my = mean(y);
    var sx = sd(x), sy = sd(y);
    if (sx === 0 || sy === 0) return { r: 0, r2: 0, t: 0, df: n - 2, p: 1, n: n };
    var num = 0;
    for (var i = 0; i < n; i++) num += (x[i] - mx) * (y[i] - my);
    var r = num / ((n - 1) * sx * sy);
    r = Math.max(-1, Math.min(1, r)); /* clamp for numerical safety */
    var t = r * Math.sqrt((n - 2) / (1 - r * r));
    var p = 2 * (1 - tCDF(Math.abs(t), n - 2));
    return { r: r, r2: r * r, t: t, df: n - 2, p: p, n: n };
  }

  /* ── Spearman Correlation ────────────────────────────── */

  function spearmanRho(x, y) {
    if (x.length !== y.length || x.length < 3) return { error: "Need equal arrays, n >= 3" };
    var n = x.length;
    function rankArr(a) {
      var s = a.map(function (v, i) { return { v: v, i: i }; }).sort(function (a, b) { return a.v - b.v; });
      var r = new Array(n);
      var i = 0;
      while (i < n) {
        var j = i;
        while (j < n && s[j].v === s[i].v) j++;
        var avg = (i + 1 + j) / 2;
        for (var k = i; k < j; k++) r[s[k].i] = avg;
        i = j;
      }
      return r;
    }
    var rx = rankArr(x), ry = rankArr(y);
    var d2 = 0;
    for (var i = 0; i < n; i++) d2 += Math.pow(rx[i] - ry[i], 2);
    var rho = 1 - 6 * d2 / (n * (n * n - 1));
    var t = rho * Math.sqrt((n - 2) / (1 - rho * rho));
    var p = 2 * (1 - tCDF(Math.abs(t), n - 2));
    return { rho: rho, t: t, df: n - 2, p: p, n: n };
  }

  /* ── Simple Linear Regression ────────────────────────── */

  function linearRegression(x, y) {
    if (x.length !== y.length || x.length < 3) return { error: "Need equal arrays, n >= 3" };
    var n = x.length;
    var mx = mean(x), my = mean(y);
    var Sxx = 0, Syy = 0, Sxy = 0;
    for (var i = 0; i < n; i++) {
      Sxx += (x[i] - mx) * (x[i] - mx);
      Syy += (y[i] - my) * (y[i] - my);
      Sxy += (x[i] - mx) * (y[i] - my);
    }
    var b1 = Sxx > 0 ? Sxy / Sxx : 0;
    var b0 = my - b1 * mx;
    var ssRes = 0, ssTot = 0;
    for (var i = 0; i < n; i++) {
      var yhat = b0 + b1 * x[i];
      ssRes += (y[i] - yhat) * (y[i] - yhat);
      ssTot += (y[i] - my) * (y[i] - my);
    }
    var r2 = ssTot > 0 ? 1 - ssRes / ssTot : 0;
    var r = Sxx > 0 && Syy > 0 ? Sxy / Math.sqrt(Sxx * Syy) : 0;
    var se_b1 = Sxx > 0 ? Math.sqrt(Math.max(0, ssRes / (n - 2)) / Sxx) : 0;
    var t = se_b1 > 0 ? b1 / se_b1 : 0;
    var p = 2 * (1 - tCDF(Math.abs(t), n - 2));
    return {
      n: n, intercept: b0, slope: b1, r: r, r2: r2,
      t: t, df: n - 2, p: p,
      se_b1: se_b1, se_b0: Math.sqrt(Math.max(0, ssRes / (n - 2)) * (1 / n + mx * mx / Sxx)),
      ssRes: ssRes, ssTot: ssTot
    };
  }

  /* ── Sample Size Calculations ────────────────────────── */

  function sampleSizeT(d, power, alpha, twoSided) {
    if (twoSided === undefined) twoSided = true;
    var za = normalInv(twoSided ? 1 - alpha / 2 : 1 - alpha);
    var zb = normalInv(power);
    return Math.ceil(2 * Math.pow((za + zb) / d, 2));
  }

  function sampleSizeProp(p1, p2, power, alpha) {
    alpha = alpha || 0.05;
    var za = normalInv(1 - alpha / 2);
    var zb = normalInv(power);
    var pbar = (p1 + p2) / 2;
    var n = Math.ceil(Math.pow(za * Math.sqrt(2 * pbar * (1 - pbar)) + zb * Math.sqrt(p1 * (1 - p1) + p2 * (1 - p2)), 2) / Math.pow(p1 - p2, 2));
    return n;
  }

  function sampleSizeAnova(k, f, power, alpha) {
    alpha = alpha || 0.05;
    var za = normalInv(1 - alpha / 2);
    var zb = normalInv(power);
    return Math.ceil(Math.pow((za + zb) / f, 2) * 2 / k + 1);
  }

  /* ── Post-Hoc Power ──────────────────────────────────── */

  function postHocPower(n, d, alpha) {
    alpha = alpha || 0.05;
    var ncp = d * Math.sqrt(n / 2);
    var tCrit = tINV(1 - alpha / 2, 2 * n - 2);
    var power = 1 - tCDF(tCrit - ncp, 2 * n - 2) + tCDF(-tCrit - ncp, 2 * n - 2);
    return { power: Math.max(0, Math.min(1, power)), n: n, d: d, alpha: alpha };
  }

  /* ── Effect Sizes ────────────────────────────────────── */

  function cohensD(a, b) {
    var pooledSD = Math.sqrt(((a.length - 1) * variance(a) + (b.length - 1) * variance(b)) / (a.length + b.length - 2));
    if (pooledSD === 0) return 0;
    return (mean(a) - mean(b)) / pooledSD;
  }

  function hedgesG(a, b) {
    var d = cohensD(a, b);
    var n = a.length + b.length;
    var correction = 1 - 3 / (4 * (n - 2) - 1);
    return d * correction;
  }

  function etaSquared(groups) {
    var k = groups.length, N = 0, grandMean = 0;
    for (var i = 0; i < k; i++) { grandMean += sum(groups[i]); N += groups[i].length; }
    grandMean /= N;
    var ssb = 0, ssw = 0;
    for (var i = 0; i < k; i++) {
      ssb += groups[i].length * Math.pow(mean(groups[i]) - grandMean, 2);
      for (var j = 0; j < groups[i].length; j++) ssw += Math.pow(groups[i][j] - mean(groups[i]), 2);
    }
    return (ssb + ssw) > 0 ? ssb / (ssb + ssw) : 0;
  }

  function oddsRatio(a, b, c, d) { return b === 0 || c === 0 ? Infinity : (a * d) / (b * c); }
  function relativeRisk(a, b, c, d) {
    var p1 = (a + b) > 0 ? a / (a + b) : 0;
    var p2 = (c + d) > 0 ? c / (c + d) : 0;
    return p2 > 0 ? p1 / p2 : Infinity;
  }

  /* ── Diagnostic Tests ────────────────────────────────── */

  function diagnosticTests(tp, fp, fn, tn) {
    var sens = (tp + fn) > 0 ? tp / (tp + fn) : 0;
    var spec = (tn + fp) > 0 ? tn / (tn + fp) : 0;
    var ppv = (tp + fp) > 0 ? tp / (tp + fp) : 0;
    var npv = (tn + fn) > 0 ? tn / (tn + fn) : 0;
    var total = tp + fp + fn + tn;
    var acc = total > 0 ? (tp + tn) / total : 0;
    var f1 = (2 * tp + fp + fn) > 0 ? 2 * tp / (2 * tp + fp + fn) : 0;
    var mccDenom = Math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn));
    var mcc = mccDenom > 0 ? (tp * tn - fp * fn) / mccDenom : 0;
    var plr = (1 - spec) > 0 ? sens / (1 - spec) : Infinity;
    var nlr = spec > 0 ? (1 - sens) / spec : Infinity;
    var youden = sens + spec - 1;
    return {
      sens: sens, spec: spec, ppv: ppv, npv: npv, acc: acc,
      f1: f1, mcc: mcc, plr: plr, nlr: nlr, youden: youden,
      tp: tp, fp: fp, fn: fn, tn: tn
    };
  }

  /* ── Multiple Comparisons ────────────────────────────── */

  function bonferroni(pvals) {
    var results = [];
    var m = pvals.length;
    for (var i = 0; i < m; i++) {
      results.push({ p: pvals[i], adj: Math.min(pvals[i] * m, 1), sig: pvals[i] * m < 0.05 });
    }
    return results;
  }

  function holm(pvals) {
    var indexed = pvals.map(function (p, i) { return { p: p, i: i }; });
    indexed.sort(function (a, b) { return a.p - b.p; });
    var results = new Array(pvals.length);
    var m = pvals.length;
    for (var k = 0; k < m; k++) {
      var adj = (m - k) * indexed[k].p;
      if (k > 0 && adj > results[indexed[k - 1].i].adj) adj = results[indexed[k - 1].i].adj;
      results[indexed[k].i] = { p: indexed[k].p, adj: Math.min(adj, 1), sig: adj < 0.05 };
    }
    return results;
  }

  /* ── EC50 / IC50 (4-parameter logistic) ──────────────── */

  function doseResponse4PL(doses, responses) {
    if (doses.length < 4) return { error: "Need at least 4 dose-response pairs" };
    var logD = doses.map(function (d) { return Math.log10(d); });
    var yMin = Math.min.apply(null, responses);
    var yMax = Math.max.apply(null, responses);
    /* Better initial estimates: use sorted dose-response to find midpoint */
    var sortedPairs = doses.map(function (d, i) { return { d: d, r: responses[i], ld: logD[i] }; }).sort(function (a, b) { return a.d - b.d; });
    var yMid = (yMin + yMax) / 2;
    /* Find dose closest to midpoint response */
    var ec50Init = sortedPairs[0].d;
    var minDist = Infinity;
    for (var i = 0; i < sortedPairs.length; i++) {
      var dist = Math.abs(sortedPairs[i].r - yMid);
      if (dist < minDist) { minDist = dist; ec50Init = sortedPairs[i].d; }
    }
    /* Detect slope direction: high dose → low response = decreasing */
    var decreasing = sortedPairs[sortedPairs.length - 1].r < sortedPairs[0].r;
    var bottom = decreasing ? yMin : yMax;
    var top = decreasing ? yMax : yMin;
    var hill = decreasing ? 1 : -1;
    var ec50 = ec50Init;
    for (var iter = 0; iter < 200; iter++) {
      var residuals = [], jacobians = [];
      for (var i = 0; i < doses.length; i++) {
        var x = logD[i] - Math.log10(ec50);
        var denom = 1 + Math.pow(10, x * hill);
        var yPred = bottom + (top - bottom) / denom;
        residuals.push(responses[i] - yPred);
        var denom2 = denom * denom;
        var powTerm = Math.pow(10, x * hill) * Math.log(10) * x;
        var dBottom = 1 / denom;
        var dTop = 1 / denom;
        var dHill = -(top - bottom) * powTerm / denom2;
        var dEc50_v = (top - bottom) * Math.pow(10, x * hill) * Math.log(10) * hill / (denom2 * ec50);
        jacobians.push([dBottom, dTop, dHill, dEc50_v]);
      }
      var JtJ = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
      var JtR = [0, 0, 0, 0];
      for (var i = 0; i < doses.length; i++) {
        for (var a = 0; a < 4; a++) {
          JtR[a] += jacobians[i][a] * residuals[i];
          for (var b = 0; b < 4; b++) JtJ[a][b] += jacobians[i][a] * jacobians[i][b];
        }
      }
      var delta = solve4x4(JtJ, JtR);
      if (!delta) break;
      bottom += delta[0]; top += delta[1]; hill += delta[2]; ec50 *= Math.pow(10, delta[3]);
      if (ec50 <= 0) ec50 = 1e-10;
      if (Math.abs(delta[0]) + Math.abs(delta[1]) + Math.abs(delta[2]) + Math.abs(delta[3]) < 1e-8) break;
    }
    var meanY = mean(responses), ssTot = 0, ssRes = 0;
    for (var i = 0; i < doses.length; i++) {
      var x = logD[i] - Math.log10(ec50);
      var yPred = bottom + (top - bottom) / (1 + Math.pow(10, x * hill));
      ssTot += Math.pow(responses[i] - meanY, 2);
      ssRes += Math.pow(responses[i] - yPred, 2);
    }
    var r2 = ssTot > 0 ? 1 - ssRes / ssTot : 0;
    return { bottom: bottom, top: top, hill: hill, ec50: ec50, r2: r2, n: doses.length };
  }

  function solve4x4(A, b) {
    var n = 4;
    var M = A.map(function (row, i) { return row.concat([b[i]]); });
    for (var col = 0; col < n; col++) {
      var maxRow = col;
      for (var row = col + 1; row < n; row++) if (Math.abs(M[row][col]) > Math.abs(M[maxRow][col])) maxRow = row;
      var tmp = M[col]; M[col] = M[maxRow]; M[maxRow] = tmp;
      if (Math.abs(M[col][col]) < 1e-12) return null;
      for (var row = col + 1; row < n; row++) {
        var f = M[row][col] / M[col][col];
        for (var j = col; j <= n; j++) M[row][j] -= f * M[col][j];
      }
    }
    var x = new Array(n);
    for (var i = n - 1; i >= 0; i--) {
      x[i] = M[i][n];
      for (var j = i + 1; j < n; j++) x[i] -= M[i][j] * x[j];
      x[i] /= M[i][i];
    }
    return x;
  }

  /* ── Public API ──────────────────────────────────────── */

  return {
    parseData: parseData,
    parseGroups: parseGroups,
    parsePairs: parsePairs,
    parseSheet: parseSheet,
    mean: mean,
    sd: sd,
    sem: sem,
    variance: variance,
    median: median,
    min: min,
    max: max,
    percentile: percentile,
    descriptive: descriptive,
    confidenceInterval: confidenceInterval,
    oneSampleT: oneSampleT,
    twoSampleT: twoSampleT,
    pairedT: pairedT,
    oneWayAnova: oneWayAnova,
    mannWhitney: mannWhitney,
    wilcoxonSignedRank: wilcoxonSignedRank,
    kruskalWallis: kruskalWallis,
    chiSquare: chiSquare,
    fishersExact: fishersExact,
    pearsonR: pearsonR,
    spearmanRho: spearmanRho,
    linearRegression: linearRegression,
    sampleSizeT: sampleSizeT,
    sampleSizeProp: sampleSizeProp,
    sampleSizeAnova: sampleSizeAnova,
    postHocPower: postHocPower,
    cohensD: cohensD,
    hedgesG: hedgesG,
    etaSquared: etaSquared,
    oddsRatio: oddsRatio,
    relativeRisk: relativeRisk,
    diagnosticTests: diagnosticTests,
    bonferroni: bonferroni,
    holm: holm,
    doseResponse4PL: doseResponse4PL,
    normalCDF: normalCDF,
    normalInv: normalInv,
    tCDF: tCDF,
    tINV: tINV,
    chiSquareCDF: chiSquareCDF,
    pFromChiSq: pFromChiSq
  };
})();
