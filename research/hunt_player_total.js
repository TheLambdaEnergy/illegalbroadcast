// 定位 Galaxy.playerTotal / playerTourists 的实际计算方式。
//   node research/hunt_player_total.js
const fs = require('fs');
const path = require('path');

const JSDIR = path.join(__dirname, 'raw', 'js');
const out = [];
const log = (...a) => { out.push(a.join(' ')); console.log(...a); };

const chunks = {};
for (const f of fs.readdirSync(JSDIR)) {
  if (f.endsWith('.js')) chunks[f] = fs.readFileSync(path.join(JSDIR, f), 'utf8');
}

function hunt(pattern, label, before = 600, after = 900, max = 8) {
  log('');
  log('='.repeat(100));
  log(`### ${label}`);
  log(`### /${pattern}/`);
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

hunt('playerTotal\\s*[:=]\\s*(?![0-9-])', 'playerTotal 被赋成表达式（不是默认值）');
hunt('playerTourists\\s*[:=]\\s*(?![0-9-])', 'playerTourists 被赋成表达式');
hunt('totalPlayerCount', 'totalPlayerCount（站点统计页用的字段名）');
hunt('diversAmt\\s*[,)]', 'diversAmt 的来源');
hunt('reduce\\([^)]*diversAmt', '求和 diversAmt 的 reduce');
hunt('unfiltered', 'filterCount.unfiltered 的口径');
hunt('diversMaximum\\s*[:=]', 'diversMaximum 的赋值');

fs.writeFileSync(path.join(__dirname, 'analysis', 'player_total_hunt.txt'), out.join('\n'));
console.log('written research/analysis/player_total_hunt.txt', out.join('\n').length, 'chars');
