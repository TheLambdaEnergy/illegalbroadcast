// 查明站点显示的「占总在线 X%」到底用的是什么分母。
//   node research/hunt_divers_total.js
const fs = require('fs');
const path = require('path');

const JSDIR = path.join(__dirname, 'raw', 'js');
const out = [];
const log = (...a) => { out.push(a.join(' ')); console.log(...a); };

const chunks = {};
for (const f of fs.readdirSync(JSDIR)) {
  if (f.endsWith('.js')) chunks[f] = fs.readFileSync(path.join(JSDIR, f), 'utf8');
}

function show(pattern, label, before = 400, after = 600, max = 6) {
  log('');
  log('='.repeat(100));
  log(`### ${label}   /${pattern}/`);
  log('='.repeat(100));
  let n = 0;
  for (const [file, src] of Object.entries(chunks)) {
    const re = new RegExp(pattern, 'g');
    let m;
    while ((m = re.exec(src)) && n < max) {
      n++;
      log(`-- ${file} @${m.index} --`);
      log(src.slice(Math.max(0, m.index - before), m.index + after).replace(/\n/g, ' '));
      log('');
    }
  }
  if (!n) log('  (无匹配)');
}

show('setDiversTotal\\(', 'setDiversTotal 的调用点（谁喂给它的）');
show('diversTotal', 'diversTotal 的定义与使用');
show('get diversPct\\b', 'diversPct 的定义');
show('playerTotal\\s*=', 'playerTotal 的来源');
show('diversPctPlanet', 'diversPctPlanet（星球卡片上的百分比）');
show('setDiversMaximum\\(', 'setDiversMaximum 的调用点');
show('filterCount', 'filterCount / popPctFilter（站点的过滤口径）');

// 专门找 Galaxy 类里怎么汇总总数
log('');
log('='.repeat(100));
log('### Galaxy 汇总：playerTotal / playerTourists / diversMaximum');
log('='.repeat(100));
for (const [file, src] of Object.entries(chunks)) {
  for (const needle of ['get playerTotal()', 'get playerTourists()', 'diversMaximum', 'DIVERS_TOTAL']) {
    let i = src.indexOf(needle);
    if (i >= 0) {
      log(`-- ${file} [${needle}] @${i} --`);
      log(src.slice(Math.max(0, i - 350), i + 750).replace(/\n/g, ' '));
      log('');
    }
  }
}

fs.mkdirSync(path.join(__dirname, 'analysis'), { recursive: true });
fs.writeFileSync(path.join(__dirname, 'analysis', 'divers_total_hunt.txt'), out.join('\n'));
console.log('written research/analysis/divers_total_hunt.txt', out.join('\n').length, 'chars');
