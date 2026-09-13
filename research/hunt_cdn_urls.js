// 找出 CDN 历史上所有 get*History* 方法的 URL 模板。
//   node research/hunt_cdn_urls.js
const fs = require('fs');
const path = require('path');

const JSDIR = path.join(__dirname, 'raw', 'js');
const out = [];
const log = (...a) => { out.push(a.join(' ')); console.log(...a); };

const chunks = {};
for (const f of fs.readdirSync(JSDIR)) {
  if (f.endsWith('.js')) chunks[f] = fs.readFileSync(path.join(JSDIR, f), 'utf8');
}

// 1) 所有 cdn.helldiverscompanion.com 附近的 URL 片段
log('='.repeat(100));
log('### 所有 CDN URL 字面量');
log('='.repeat(100));
const urls = new Set();
for (const src of Object.values(chunks)) {
  for (const m of src.matchAll(/["'`](https:\/\/[a-z.]*helldiverscompanion\.com\/[^"'`]*?)["'`]/g)) {
    urls.add(m[1]);
  }
  // 模板字符串里的相对片段
  for (const m of src.matchAll(/["'`](\/(?:live|data)\/[a-zA-Z0-9${}\/_.-]*)["'`]/g)) {
    urls.add(m[1]);
  }
}
for (const u of [...urls].sort()) log('  ' + u);

// 2) get*History* 方法的实现
log('');
log('='.repeat(100));
log('### get*History* 方法定义');
log('='.repeat(100));
for (const [file, src] of Object.entries(chunks)) {
  const re = /(?:static\s+)?(?:async\s+)?(get[A-Za-z0-9_]*Historic?[A-Za-z0-9_]*)\s*\(([^)]*)\)\s*\{/g;
  let m;
  while ((m = re.exec(src))) {
    const body = src.slice(m.index, m.index + 420).replace(/\n/g, ' ');
    log(`-- ${file} :: ${m[1]}(${m[2]}) --`);
    log('   ' + body);
    log('');
  }
}

// 3) cdnFetch 的调用点（URL 就是在这里拼出来的）
log('='.repeat(100));
log('### cdnFetch 调用点');
log('='.repeat(100));
for (const [file, src] of Object.entries(chunks)) {
  const re = /cdnFetch\(/g;
  let m;
  let n = 0;
  while ((m = re.exec(src)) && n < 30) {
    n++;
    log(`-- ${file} @${m.index} --`);
    log('   ' + src.slice(m.index - 120, m.index + 260).replace(/\n/g, ' '));
  }
}

fs.writeFileSync(path.join(__dirname, 'analysis', 'cdn_urls.txt'), out.join('\n'));
console.log('\nwritten research/analysis/cdn_urls.txt', out.join('\n').length, 'chars');
