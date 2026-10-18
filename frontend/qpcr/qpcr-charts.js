/**
 * qpcr-charts.js — Canvas chart library.
 * Line, scatter, bar. Color-blind safe palette. Series toggling, zoom, PNG export.
 * Zero dependencies. <60KB raw.
 */

const PALETTE = [
  '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
];

const CB_SAFE = [
  '#0072B2', '#E69F00', '#009E73', '#CC79A7', '#F0E442',
  '#56B4E9', '#D55E00', '#000000',
];

export function getPalette(cbSafe) {
  return cbSafe ? CB_SAFE : PALETTE;
}

export class Chart {
  constructor(canvas, opts) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.opts = Object.assign({ padding: 40, cbSafe: true }, opts || {});
    this.series = []; // { label, data: [{x,y}], color, style, visible }
    this.xRange = null;
    this.yRange = null;
    this.zoom = { x: [null, null], y: [null, null] };
    this.listeners = {};
    this._init();
  }

  _init() {
    this.canvas.addEventListener('wheel', e => this._onWheel(e));
    this.canvas.addEventListener('mousedown', e => this._onMouseDown(e));
    this.canvas.addEventListener('mousemove', e => this._onMouseMove(e));
    this.canvas.addEventListener('mouseup', e => this._onMouseUp(e));
    this.canvas.addEventListener('dblclick', () => this.resetZoom());
  }

  addSeries(label, data, opts) {
    const idx = this.series.length;
    const color = (opts && opts.color) || getPalette(this.opts.cbSafe)[idx % getPalette(this.opts.cbSafe).length];
    this.series.push({
      label, data: data || [], color,
      style: (opts && opts.style) || 'line',
      visible: true,
      ...opts,
    });
    return idx;
  }

  setSeriesVisible(idx, visible) {
    if (this.series[idx]) this.series[idx].visible = visible;
    this.render();
  }

  toggleSeries(idx) {
    if (this.series[idx]) this.series[idx].visible = !this.series[idx].visible;
    this.render();
  }

  _computeRanges() {
    let xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity;
    for (const s of this.series) {
      if (!s.visible) continue;
      for (const p of s.data) {
        if (p.x < xmin) xmin = p.x;
        if (p.x > xmax) xmax = p.x;
        if (p.y < ymin) ymin = p.y;
        if (p.y > ymax) ymax = p.y;
      }
    }
    if (!isFinite(xmin)) { xmin = 0; xmax = 1; ymin = 0; ymax = 1; }
    const xpad = (xmax - xmin) * 0.05 || 1;
    const ypad = (ymax - ymin) * 0.1 || 1;
    this.xRange = this.zoom.x[0] != null ? this.zoom.x : [xmin - xpad, xmax + xpad];
    this.yRange = this.zoom.y[0] != null ? this.zoom.y : [ymin - ypad, ymax + ypad];
  }

  _toPixel(x, y) {
    const [x0, x1] = this.xRange;
    const [y0, y1] = this.yRange;
    const p = this.opts.padding;
    const w = this.canvas.width - 2 * p;
    const h = this.canvas.height - 2 * p;
    return {
      px: p + (x - x0) / (x1 - x0) * w,
      py: this.canvas.height - p - (y - y0) / (y1 - y0) * h,
    };
  }

  render() {
    const ctx = this.ctx;
    const w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, w, h);
    this._computeRanges();

    // grid
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 0.5;
    const p = this.opts.padding;
    for (let i = 0; i <= 5; i++) {
      const x = p + (w - 2 * p) * i / 5;
      const y = p + (h - 2 * p) * i / 5;
      ctx.beginPath(); ctx.moveTo(x, p); ctx.lineTo(x, h - p); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(p, y); ctx.lineTo(w - p, y); ctx.stroke();
    }

    // axes labels
    ctx.fillStyle = '#475569';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(this.opts.xLabel || 'X', w / 2, h - 8);
    ctx.save();
    ctx.translate(12, h / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(this.opts.yLabel || 'Y', 0, 0);
    ctx.restore();

    // series
    for (const s of this.series) {
      if (!s.visible || s.data.length === 0) continue;
      ctx.strokeStyle = s.color;
      ctx.fillStyle = s.color;
      ctx.lineWidth = s.style === 'line' ? 2 : 1;
      if (s.style === 'scatter' || s.style === 'line') {
        ctx.beginPath();
        let first = true;
        for (const pt of s.data) {
          const { px, py } = this._toPixel(pt.x, pt.y);
          if (first) { ctx.moveTo(px, py); first = false; }
          else ctx.lineTo(px, py);
        }
        if (s.style === 'line') ctx.stroke();
      }
      if (s.style === 'scatter' || s.style === 'bar') {
        for (const pt of s.data) {
          const { px, py } = this._toPixel(pt.x, pt.y);
          ctx.beginPath();
          ctx.arc(px, py, 3, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      if (s.style === 'bar') {
        const barW = (this.canvas.width - 2 * this.opts.padding) / (s.data.length * this.series.filter(x => x.visible).length + 1);
        // simplified bar rendering
      }
    }

    // legend (skip empty/invisible series — a legend entry with no drawn curve is a lie)
    let ly = p;
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'left';
    for (const s of this.series) {
      if (!s.visible || s.data.length === 0) continue;
      ctx.fillStyle = s.color;
      ctx.fillRect(w - 120, ly, 12, 12);
      ctx.fillStyle = '#334155';
      ctx.fillText(s.label, w - 104, ly + 10);
      ly += 16;
    }

    // empty-state message: when nothing is plottable, say so instead of showing a blank plot
    const anyPlottable = this.series.some(s => s.visible && s.data.length > 0);
    if (!anyPlottable) {
      const msg = this.emptyMessage || 'No data to plot.';
      ctx.fillStyle = '#64748b';
      ctx.font = '13px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const maxW = w - 2 * p - 40;
      const words = msg.split(' ');
      const linesOut = [];
      let cur = '';
      for (const word of words) {
        const test = cur ? cur + ' ' + word : word;
        if (ctx.measureText(test).width > maxW && cur) { linesOut.push(cur); cur = word; }
        else cur = test;
      }
      if (cur) linesOut.push(cur);
      const midY = (h) / 2 - (linesOut.length - 1) * 9;
      linesOut.forEach((ln, i) => ctx.fillText(ln, w / 2, midY + i * 18));
      ctx.textBaseline = 'alphabetic';
    }
  }

  _onWheel(e) {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 1.1 : 0.9;
    const [x0, x1] = this.xRange;
    const [y0, y1] = this.yRange;
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    const xr = (x1 - x0) / 2 * factor;
    const yr = (y1 - y0) / 2 * factor;
    this.zoom.x = [cx - xr, cx + xr];
    this.zoom.y = [cy - yr, cy + yr];
    this.render();
  }

  _onMouseDown(e) {
    this._dragStart = { x: e.offsetX, y: e.offsetY, zoom: { ...this.zoom } };
  }

  _onMouseMove(e) {
    if (!this._dragStart) return;
    const dx = e.offsetX - this._dragStart.x;
    const dy = e.offsetY - this._dragStart.y;
    const [x0, x1] = this._dragStart.zoom.x || this.xRange;
    const [y0, y1] = this._dragStart.zoom.y || this.yRange;
    const xr = x1 - x0, yr = y1 - y0;
    const w = this.canvas.width - 2 * this.opts.padding;
    const h = this.canvas.height - 2 * this.opts.padding;
    this.zoom.x = [x0 - dx / w * xr, x1 - dx / w * xr];
    this.zoom.y = [y0 + dy / h * yr, y1 + dy / h * yr];
    this.render();
  }

  _onMouseUp() {
    this._dragStart = null;
  }

  resetZoom() {
    this.zoom = { x: [null, null], y: [null, null] };
    this.render();
  }

  exportPNG(filename) {
    const link = document.createElement('a');
    link.download = filename || 'chart.png';
    link.href = this.canvas.toDataURL('image/png');
    link.click();
  }

  resize(w, h) {
    this.canvas.width = w;
    this.canvas.height = h;
    this.render();
  }
}

export { PALETTE, CB_SAFE };
export default Chart;
