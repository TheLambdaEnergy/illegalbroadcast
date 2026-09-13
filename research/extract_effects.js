// 提取站点 JS 里的游戏效果枚举，把 planetActiveEffects 的数字 ID 变成可读名称。
//
//   node research/extract_effects.js
//
// 目标是这两张表（都在 BImFknRy.js 里，ES 枚举被压缩后的形式）：
//   Yt —— presence 类效果，ID 是 32 位哈希（如 pres_FactoryHub=...）
//   m1 —— 行星/战略效果，ID 是小整数（如 ammo_Pickup1=1317）
//
// 反编译出来的原始形态大致是：
//   m1=(e=>(e[e.ammo_Pickup1=1317]="ammo_Pickup1", ... ,e))(m1||{})

const fs = require('fs');
const path = require('path');

const JSDIR = path.join(__dirname, 'raw', 'js');
const OUT = path.join(__dirname, '..', 'data', 'effects.json');

if (!fs.existsSync(JSDIR)) {
  console.error(`缺少 ${JSDIR}；请先运行: python research/fetch_evidence.py --with-js`);
  process.exit(1);
}

const chunks = {};
for (const f of fs.readdirSync(JSDIR)) {
  if (f.endsWith('.js')) chunks[f] = fs.readFileSync(path.join(JSDIR, f), 'utf8');
}

/** 找到 `ident=(e=>(...))(ident||{})` 这类枚举字面量的范围 */
function findEnum(src, ident) {
  const re = new RegExp(`(?<![\\w$.])${ident}\\s*=\\s*\\(`);
  const m = re.exec(src);
  if (!m) return null;
  // 枚举体结束于 `))(ident||{})` 或 `))(ident||{})`
  const tail = new RegExp(`\\)\\)?\\(${ident}\\s*\\|\\|\\s*\\{\\}\\)`);
  const rest = src.slice(m.index);
  const t = tail.exec(rest);
  if (!t) return null;
  return rest.slice(0, t.index + t[0].length);
}

const ENTRY = /e\[e\.([A-Za-z0-9_$]+)=(-?\d+)\]\s*=\s*"\1"/g;

function parseEnum(body) {
  const out = {};
  let m;
  ENTRY.lastIndex = 0;
  while ((m = ENTRY.exec(body))) {
    out[m[2]] = m[1];
  }
  return out;
}

const result = { source: 'helldiverscompanion online bundle', enums: {}, counts: {} };

for (const [file, src] of Object.entries(chunks)) {
  for (const ident of ['Yt', 'm1']) {
    const body = findEnum(src, ident);
    if (!body) continue;
    const parsed = parseEnum(body);
    const n = Object.keys(parsed).length;
    if (n < 20) continue;                       // 太小的多半是误匹配
    console.log(`${file} :: ${ident} -> ${n} 条  (字面量 ${body.length} 字符)`);
    result.enums[ident] = parsed;
    result.counts[ident] = n;
  }
}

// 合并成一张 id -> slug 的总表；整数 ID 与哈希 ID 分开放，避免键冲突
const pres = result.enums.Yt || {};
const effects = result.enums.m1 || {};

const doc = {
  generated_at: new Date().toISOString(),
  source: result.source,
  note: '从站点线上包里提取的 ES 枚举。presence_id 对应 planetActiveEffects[].galacticEffectId（哈希），' +
        'effect_id 对应同一字段的小整数形式；两者都是「星球正在生效的效果」。',
  presence_ids: pres,
  effect_ids: effects,
  counts: { presence_ids: Object.keys(pres).length, effect_ids: Object.keys(effects).length },
};

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(doc, null, 1));
console.log(`\n已写入 ${OUT}`);
console.log(`  presence_ids: ${doc.counts.presence_ids}`);
console.log(`  effect_ids  : ${doc.counts.effect_ids}`);

// 展示几个已知会用到的
const samples = ['1190', '1188', '1239', '1363', '1209', '1212', '1238', '1261', '1262', '1384', '1385'];
console.log('\n抽样（当前战局里出现过的 effectId）:');
for (const s of samples) {
  if (pres[s] || effects[s]) console.log(`  ${s} -> presence=${pres[s] || '-'}  effect=${effects[s] || '-'}`);
}
