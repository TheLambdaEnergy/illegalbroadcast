// 从线上 JS 包里定位并提取硬编码的数据表 -> research/analysis/extract_tables.txt
//
//   node research/extract_tables.js
//
// 依赖 research/raw/js（先跑 python research/fetch_evidence.py --with-js）。
//
// 已知目标：
//   KT  —— 按星球索引排列的名称数组（260 项，站点自己也只用它渲染名称）
//   s1  —— slug -> settingsHash 枚举，用于确认 settingsHash 是星球稳定标识

const fs = require('fs');
const path = require('path');

const JSDIR = path.join(__dirname, 'raw', 'js');
const OUTDIR = path.join(__dirname, 'analysis');

if (!fs.existsSync(JSDIR)) {
  console.error(`缺少 ${JSDIR}；请先运行: python research/fetch_evidence.py --with-js`);
  process.exit(1);
}

const chunks = {};
for (const f of fs.readdirSync(JSDIR)) {
  if (f.endsWith('.js')) chunks[f] = fs.readFileSync(path.join(JSDIR, f), 'utf8');
}

const out = [];
const log = (...a) => { out.push(a.join(' ')); console.log(...a); };

/** 从 start 处的 [ 或 { 开始，返回配对闭合符之后的下标。 */
function findEnd(src, start) {
  const open = src[start];
  let depth = 0;
  let i = start;
  const n = src.length;
  while (i < n) {
    const c = src[i];
    if (c === '"' || c === "'") {
      const q = c; i++;
      while (i < n) { if (src[i] === '\\') { i += 2; continue; } if (src[i] === q) break; i++; }
      i++; continue;
    }
    if (c === '`') {
      i++;
      while (i < n) { if (src[i] === '\\') { i += 2; continue; } if (src[i] === '`') break; i++; }
      i++; continue;
    }
    if (c === '/' && src[i + 1] === '/') { while (i < n && src[i] !== '\n') i++; continue; }
    if (c === '/' && src[i + 1] === '*') { const j = src.indexOf('*/', i); i = j < 0 ? n : j + 2; continue; }
    if (c === '[' || c === '{') depth++;
    else if (c === ']' || c === '}') { depth--; if (depth === 0) return i + 1; }
    i++;
  }
  throw new Error('unterminated literal');
}

const evalLiteral = (text) => new Function('"use strict";return (' + text + ');')();

function describe(v, depth = 0) {
  if (Array.isArray(v)) return `array[${v.length}]`;
  if (v && typeof v === 'object') {
    const keys = Object.keys(v);
    return `object{${keys.slice(0, 8).join(',')}${keys.length > 8 ? ',...' : ''}}`;
  }
  return typeof v;
}

// ---------------------------------------------------------------- 定向提取
for (const [file, src] of Object.entries(chunks)) {
  for (const ident of ['KT', 's1']) {
    const re = new RegExp(`(?<![\\w$.])${ident}\\s*=\\s*[[{]`, 'g');
    let m;
    while ((m = re.exec(src))) {
      const start = src.indexOf(m[0].includes('{') ? '{' : '[', m.index);
      let end;
      try { end = findEnd(src, start); } catch { continue; }
      const lit = src.slice(start, end);
      let value;
      try { value = evalLiteral(lit); } catch { continue; }
      log('='.repeat(90));
      log(`### ${ident} @ ${file}:${start}  (${lit.length} 字符)  ${describe(value)}`);
      log('='.repeat(90));
      if (Array.isArray(value)) {
        log(`条目数: ${value.length}`);
        log(`前 5: ${JSON.stringify(value.slice(0, 5))}`);
        log(`后 5: ${JSON.stringify(value.slice(-5))}`);
      } else {
        const keys = Object.keys(value);
        log(`键数: ${keys.length}`);
        for (const k of keys.slice(0, 12)) log(`  ${k} = ${value[k]}`);
      }
      log('');
    }
  }
}

// ---------------------------------------------------------------- 通用扫描
log('='.repeat(90));
log('### 体积较大、以字符串为主的对象/数组字面量（候选数据表）');
log('='.repeat(90));
const found = [];
for (const [file, src] of Object.entries(chunks)) {
  const re = /(?<![\w$.])([A-Za-z_$][\w$]{0,6})\s*=\s*([\[{])/g;
  let m;
  while ((m = re.exec(src))) {
    const start = m.index + m[0].length - 1;
    let end;
    try { end = findEnd(src, start); } catch { continue; }
    const len = end - start;
    if (len < 2000 || len > 900000) continue;
    const lit = src.slice(start, end);
    const strings = (lit.match(/"[^"]{2,40}"/g) || []).length;
    if (strings < 15) continue;
    let value;
    try { value = evalLiteral(lit); } catch { continue; }
    found.push({ file, ident: m[1], len, strings, shape: describe(value) });
  }
}
for (const r of found) {
  log(`${r.file.padEnd(22)} ${r.ident.padEnd(6)} len=${String(r.len).padStart(7)} ` +
      `strings=${String(r.strings).padStart(5)} ${r.shape}`);
}

fs.mkdirSync(OUTDIR, { recursive: true });
const outPath = path.join(OUTDIR, 'extract_tables.txt');
fs.writeFileSync(outPath, out.join('\n'));
console.log(`\n已写入 ${outPath}`);
