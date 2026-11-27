'use strict';

const byId = id => document.getElementById(id);
const partByRef = new Map(parts.map(part => [part.ref, part]));
const modelCount = new Set(parts.map(part => part.mpn)).size;
const byZone = new Map(lessons.map((lesson, i) => [lesson.id, {...lesson, number:String(i + 1).padStart(2, '0')}]));
const dialog = byId('part-dialog');
const boardImage = 'assets/3d-top.png';
let selected = byZone.get('input');
let showAll = false;

function el(tag, cls, value) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (value !== undefined) node.textContent = value;
  return node;
}

function btn(label, cls, handler) {
  const node = el('button', cls, label);
  node.type = 'button';
  node.addEventListener('click', handler);
  return node;
}

function link(label, href, cls) {
  const a = el('a', cls, label);
  a.href = href;
  a.target = '_blank';
  a.rel = 'noopener';
  return a;
}

function locate(node, ref, useBody) {
  // The orthographic top render is 18.2 px/mm. Board space starts at (147, 133) px.
  // Ganged connectors have off-centre footprint origins, so overview pins mark their bodies.
  const bodies = {J1:[64.5,34.5], J5:[5.55,27], J3:[19.75,45.6], J4:[43.55,45.6]};
  const [x, y] = (useBody && bodies[ref]) || partByRef.get(ref).xy;
  node.style.left = (x / 72 * 100) + '%';
  node.style.top = (y / 50 * 100) + '%';
}

function locator(ref) {
  const figure = el('figure', 'locator');
  const pcb = el('div', 'pcb');
  const img = el('img', 'boardphoto');
  img.src = boardImage;
  img.alt = '控制板元件面，亮圈标出 ' + ref;
  const dot = el('span', 'spot');
  locate(dot, ref, false);
  pcb.append(img, dot);
  figure.append(pcb, el('p', '', ref + ' 封装定位点 · 元件面'));
  return figure;
}

function routingFigure(lesson, inZone) {
  const base = 'assets/zones/' + lesson.id + '.svg';
  const data = routing[lesson.id];
  const section = el('section', 'route-study');
  const toolbar = el('div', 'route-toolbar');
  const pick = el('select');
  pick.setAttribute('aria-label', '按位号放大走线与原理图');
  const reset = btn('返回全区', 'plainbtn', () => focusPart(''));
  const selectLabel = el('label', 'route-picker', '按位号对照');
  pick.add(new Option('整个功能区', ''));
  inZone.forEach(p => pick.add(new Option(p.ref + ' · ' + p.mpn, p.ref)));
  pick.addEventListener('change', () => focusPart(pick.value));
  selectLabel.append(pick);
  toolbar.append(selectLabel, reset, link('打开整张 SVG ↗', base, 'quietlink'));

  const columns = el('div', 'routing-pair');
  function pane(title, target) {
    const figure = el('figure', 'route-pane');
    const head = el('figcaption', 'pane-head');
    const full = link('单独放大 ↗', base + '#' + target, 'quietlink');
    head.append(el('strong', '', title), full);
    const frame = el('div', 'drawing-frame');
    const img = el('img');
    frame.append(img);
    figure.append(head, frame);
    columns.append(figure);
    return {frame, img, full, title, head};
  }
  const board = pane('实板走线', 'board');
  const schematic = pane('电路原理图', 'schematic');
  const keyRef = ({input:'Q1', usb:'U4', sol:'Q6'})[lesson.id] || lesson.pin;
  let schematicRef = keyRef;
  let schematicWide = false;
  const changeScale = btn('', 'schematic-scale', () => {
    schematicWide = !schematicWide;
    showSchematic();
  });
  schematic.head.insertBefore(changeScale, schematic.full);
  function showSchematic() {
    const target = schematicWide ? 'schematic' : 'sch-' + schematicRef;
    schematic.img.src = base + '#' + target;
    schematic.full.href = schematic.img.src;
    schematic.img.alt = lesson.name + '电路原理图 · ' + (schematicWide ? '全区' : schematicRef);
    schematic.head.firstChild.textContent = '电路原理图 · ' + (schematicWide ? '全区' : schematicRef);
    changeScale.textContent = schematicWide ? '放大 ' + schematicRef : '看全区';
    for (const mark of markers.children) {
      mark.classList.toggle('highlight', !schematicWide && mark.dataset.ref === schematicRef);
    }
  }
  const markers = el('div', 'component-targets');
  for (const [ref, [x, y]] of Object.entries(data.anchors)) {
    const mark = btn('', 'component-target', () => focusPart(ref, true));
    mark.dataset.ref = ref;
    mark.style.left = x + '%';
    mark.style.top = y + '%';
    mark.setAttribute('aria-label', '对照 ' + ref);
    mark.title = '放大 ' + ref;
    markers.append(mark);
  }
  board.frame.append(markers);
  const info = el('div', 'route-info');
  info.setAttribute('aria-live', 'polite');
  function focusPart(ref, fromBoard = false, initial = false) {
    pick.value = ref;
    reset.hidden = !ref;
    markers.hidden = Boolean(ref);
    board.img.src = base + '#' + (ref ? 'pcb-' + ref : 'board');
    board.img.alt = lesson.name + '实板走线 · ' + (ref || '全区');
    board.full.href = board.img.src;
    schematicRef = ref || keyRef;
    schematicWide = !ref && !initial;
    showSchematic();
    const p = partByRef.get(ref);
    if (p) {
      info.replaceChildren(el('strong', '', ref), el('span', '', p.spec),
        btn('型号与引脚', 'refbtn', () => openPart(ref)), el('p', '', p.role));
    } else {
      info.textContent = '点走线图上的位号，两张图会一起放大到同一元件。红色为顶层，绿色为底层。';
    }
    if (fromBoard) reset.focus({preventScroll: true});
  }
  focusPart('', false, true);
  const flows = el('ol', 'route-flows');
  data.flows.forEach(([name, path, note], i) => {
    const li = el('li');
    li.append(el('span', 'flow-key', String.fromCharCode(65+i)), el('strong', '', name),
      el('div', 'flow-path', path), el('p', '', note));
    flows.append(li);
  });
  section.append(toolbar, columns, info, el('h3', '', '工作原理与流向'), flows);
  return section;
}

const menu = byId('zone-list');
for (const lesson of byZone.values()) {
  const pin = btn(lesson.number, 'pin', () => goZone(lesson.id));
  pin.dataset.zone = lesson.id;
  pin.setAttribute('aria-label', lesson.number + ' ' + lesson.name);
  pin.title = lesson.name + ' · ' + lesson.pin;
  locate(pin, lesson.pin, true);
  byId('main-board').append(pin);

  const choice = btn('', 'zonebtn', () => goZone(lesson.id));
  choice.dataset.zone = lesson.id;
  choice.append(el('span','num',lesson.number), el('strong','',lesson.name), el('small','',lesson.pin));
  choice.addEventListener('pointerenter', () => pin.classList.add('peek'));
  choice.addEventListener('pointerleave', () => pin.classList.remove('peek'));
  menu.append(choice);
  for (const id of ['zone-switch','zone-filter']) {
    const opt = el('option','',lesson.number + '  ' + lesson.name);
    opt.value = lesson.id;
    byId(id).append(opt);
  }
}

function circuit(lesson) {
  const card = el('div','circuit');
  const states = el('div','modes');
  states.setAttribute('role','group');
  states.setAttribute('aria-label','选择工作状态');
  const live = el('div');
  live.setAttribute('aria-live','polite');
  function setState(index) {
    [...states.children].forEach((b,i) => b.setAttribute('aria-pressed', i === index));
    const [, path, explanation] = lesson.states[index];
    const independent = lesson.id === 'led' && index === 0;
    const flow = el('div', 'flow' + (independent ? ' independent' : ''));
    for (const [signal, action] of path) {
      const step = el('div','node');
      step.append(el('strong','',signal), el('span','',action));
      flow.append(step);
    }
    live.replaceChildren(flow, el('p','state-text',explanation));
  }
  lesson.states.forEach(([label],i) => states.append(btn(label,'mode',() => setState(i))));
  setState(0);
  card.append(el('h3','','工作过程'), states, live);
  return card;
}

function motorDemo() {
  const box = el('div','study');
  box.append(el('h3','','换一个方向，两台电机各走多少？'),
    el('p','','CoreXY 的右侧皮带 B 走 X + Y，左侧皮带 A 走 X − Y。选择工具头的移动量，比较两条带的位移。'));
  const choices = el('div','jogs'), values = el('div','jogvalues');
  values.setAttribute('aria-live','polite');
  const moves = [['沿 X 移动 5 mm',5,0],['沿 Y 移动 5 mm',0,5],['X +5、Y +5',5,5],['X +5、Y −5',5,-5]];
  function display(i) {
    const [,x,y] = moves[i];
    [...choices.children].forEach((b,n) => b.setAttribute('aria-pressed',n === i));
    const format = n => (n > 0 ? '+' : '') + n + ' mm' + (n === 0 ? '（不转）' : '');
    values.replaceChildren(el('b','','J3 · 右 B　' + format(x+y)),el('b','','J4 · 左 A　' + format(x-y)));
  }
  moves.forEach(([label],i) => choices.append(btn(label,'jog',() => display(i))));
  display(0);
  box.append(choices,values,el('p','wavesub','电机每转 200 整步，每整步分为 16 个微步。20 齿同步带轮配 2 mm 齿距皮带时，每转走 40 mm，因此每毫米带位移需要 200 × 16 ÷ 40 = 80 个 STEP 脉冲。'));
  return box;
}

function pwmDemo() {
  const box = el('div','study');
  box.append(el('h3','','一个 PWM 周期，看得见的通电时间'));
  const choices = el('div','jogs'), output = el('div');
  output.setAttribute('aria-live','polite');
  function display(i) {
    const duty = [0,0.5,1][i], width = 100 * duty;
    [...choices.children].forEach((b,n) => b.setAttribute('aria-pressed',n === i));
    const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('viewBox','0 0 310 50');
    svg.setAttribute('class','wave');
    svg.setAttribute('aria-hidden','true');
    const path = document.createElementNS(svg.namespaceURI,'path');
    let d = 'M5 ' + (duty ? '8' : '38');
    for (let k = 0; k < 3; k++) {
      const x = 5 + 100*k;
      if (duty === 0 || duty === 1) d += ' H' + (x+100);
      else d += ' H' + (x+width) + ' V38 H' + (x+100) + (k<2 ? ' V8' : '');
    }
    path.setAttribute('d',d);path.setAttribute('fill','none');path.setAttribute('stroke','#276348');path.setAttribute('stroke-width','3');
    svg.append(path);
    output.replaceChildren(svg,el('p','','理想命令波形，每周期 1 ms。其中加电 ' + duty + ' ms，占 ' + duty*100 + '%。高电平表示请求接通。'));
  }
  ['S0','S500','S1000'].forEach((t,i) => choices.append(btn(t,'jog',() => display(i))));
  display(1);
  box.append(choices,output,el('p','wavesub','假设互锁已放行、M3 模式、主轴倍率 100%。图示为控制命令，线圈电流会随电感逐渐升降。'));
  return box;
}

function renderLesson(id) {
  selected = byZone.get(id);
  const lesson = selected;
  byId('zone-switch').value = id;
  document.querySelectorAll('[data-zone]').forEach(n => {
    if (n.dataset.zone === id) n.setAttribute('aria-current','true');
    else n.removeAttribute('aria-current');
  });
  const meta = el('div','lessonmeta');
  meta.append(el('span','lesnum',lesson.number),el('span','',lesson.group + ' / ' + lesson.name));
  const title = el('h2','',lesson.headline);
  title.id = 'lesson-title';
  const inZone = parts.filter(p => p.zone === id);
  const learning = routingFigure(lesson, inZone);
  const notes = el('section','notes'), grid = el('div','notegrid');
  for (const [question,answer] of lesson.notes) {
    const article = el('article');
    article.append(el('h4','',question),el('p','',answer));
    grid.append(article);
  }
  notes.append(el('h3','','设计考虑'),grid);
  const zoneParts = el('section','zoneparts'), specs = el('dl','zone-specs');
  inZone.forEach(p => {
    const row = el('div'), ref = el('dt');
    ref.append(btn(p.ref,'chip',() => openPart(p.ref)));
    row.append(ref, el('dd','',p.spec));
    specs.append(row);
  });
  zoneParts.append(el('h3','','本区元件规格 · ' + inZone.length + ' 个位号'),specs);
  const sources = el('div','sources');
  for (const page of new Set([lesson.sheet, ...inZone.map(p => p.page)])) {
    const refs = page === lesson.sheet ? '原理图' : inZone.filter(p => p.page === page).map(p => p.ref).join('、');
    sources.append(link(refs + ' · 第 ' + page + ' 页','assets/schematic.pdf#page=' + page));
  }
  lesson.sources.forEach(([label,href]) => sources.append(link(label,href)));
  const footer = el('div','readerfoot');
  footer.append(el('a','quietlink','回到整板地图'));
  footer.firstChild.href = '#overview';
  const next = lessons[Number(lesson.number)];
  if (next) footer.append(btn('下一分区 · '+next.name,'plainbtn',() => goZone(next.id)));
  else {const a = el('a','quietlink','查阅全部元件'); a.href='#library'; footer.append(a);}
  const content = [meta,title,el('p','lead introtext',lesson.intro),learning,zoneParts,circuit(lesson)];
  if (id === 'x' || id === 'y') content.push(motorDemo());
  if (id === 'sol') content.push(pwmDemo());
  byId('reader').replaceChildren(...content,notes,sources,footer);
}

function goZone(id) {
  if (location.hash === '#zone-' + id) navigateHash();
  else location.hash = 'zone-' + id;
}

function navigateHash() {
  const id = location.hash.slice(6);
  if (location.hash.startsWith('#zone-') && byZone.has(id)) {
    renderLesson(id);
    byId('lesson').focus({preventScroll:true});
    byId('lesson').scrollIntoView({block:'start'});
  }
}
byId('zone-switch').addEventListener('change', e => goZone(e.target.value));
window.addEventListener('hashchange',navigateHash);

function openPart(ref) {
  const part = partByRef.get(ref), zone = byZone.get(part.zone);
  const head = el('div','parthead'), title = el('h2','',ref);
  title.id = 'part-title';
  head.append(title,el('p','',part.mpn));
  const description = el('div','partdesc'), specs = el('dl');
  for (const [field,value] of [['本板参数 / 器件规格',part.spec],['封装 / 安装',part.pkg+' · '+(part.process==='THT'?'通孔安装':'表面贴装')],['采购编号',part.code],['所在功能区',zone.name]]) {
    specs.append(el('dt','',field),el('dd','',value));
  }
  description.append(specs,locator(ref));
  const pins = el('details');
  pins.append(el('summary','','已连接的引脚与网络'));
  const pinlist = el('div','pinlist');
  part.pins.forEach(([pin,net]) => pinlist.append(el('span','',pin+' · '+net)));
  pins.append(pinlist);
  const sources=el('div','sources partlinks');
  if (ref.startsWith('U')) sources.append(link('逐脚走线放大图','assets/ic/'+ref+'.svg'));
  if (ref === 'Q6' || ref === 'Q7') sources.append(link('逐脚走线放大图','assets/transistors/'+ref+'.svg'));
  sources.append(link('器件资料',part.datasheet),link('原理图 · 第 '+part.page+' 页','assets/schematic.pdf#page='+part.page),
    btn('阅读本区讲解','plainbtn',() => {dialog.close();goZone(part.zone);}));
  byId('part-body').replaceChildren(head,description,el('p','partrole',part.role),pins,sources);
  dialog.showModal();
  dialog.scrollTop=0;
}
byId('close-part').addEventListener('click',() => dialog.close());
dialog.addEventListener('click',e => {
  if(e.target !== dialog) return;
  const r = dialog.getBoundingClientRect();
  if(e.clientX<r.left || e.clientX>r.right || e.clientY<r.top || e.clientY>r.bottom) dialog.close();
});

const search = byId('search'), filter = byId('zone-filter');
function renderIndex() {
  const query = search.value.trim().toLowerCase();
  const result = parts.filter(p => (!filter.value || p.zone === filter.value) &&
    [p.ref,p.mpn,p.code,p.pkg,p.role,p.spec,byZone.get(p.zone).name,...p.pins.map(([,net]) => net)]
      .some(v => v.toLowerCase().includes(query)));
  if (query) result.sort((a,b) => Number(b.ref.toLowerCase()===query)-Number(a.ref.toLowerCase()===query));
  const rows = showAll || query || filter.value ? result : result.slice(0,10);
  const table = el('table'), thead = table.createTHead().insertRow(), tbody = table.createTBody();
  for (const h of ['位号','功能区','型号 / MPN','本板参数与额定规格']) {
    const th = el('th','',h);th.scope='col';thead.append(th);
  }
  for (const p of rows) {
    const row = tbody.insertRow();
    row.insertCell().append(btn(p.ref,'refbtn',() => openPart(p.ref)));
    row.insertCell().textContent=byZone.get(p.zone).name;
    row.insertCell().append(el('span','mpn',p.mpn));
    row.insertCell().textContent=p.spec;
  }
  byId('library-table').replaceChildren(result.length ? table : el('p','empty','没有匹配的元件。试试 U1、0.100 Ω 或取消分区筛选。'));
  byId('count').textContent='显示 '+rows.length+' / '+result.length+' 个位号 · 整板 '+modelCount+' 种型号';
  byId('more').hidden = Boolean(query || filter.value || !result.length || result.length<=10);
  byId('more').textContent = showAll ? '收起元件列表' : '显示全部 '+parts.length+' 个位号';
}
byId('more').addEventListener('click',() => {showAll=!showAll;renderIndex();if (!showAll) byId('library').scrollIntoView();});
for (const control of [search,filter]) control.addEventListener(control===search?'input':'change',() => {showAll=false;renderIndex();});
const fittedCount = byId('fitted-count');
fittedCount.textContent = parts.length;
fittedCount.parentElement.hidden = false;
renderLesson('input');
renderIndex();
navigateHash();
