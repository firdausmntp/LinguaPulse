// Evidence for the design review; this is not a WCAG certification.
() => {
  const visible = el => { const b = el.getBoundingClientRect(); return b.width > 0 && b.height > 0 && getComputedStyle(el).visibility !== 'hidden'; };
  const name = el => (el.getAttribute('aria-label') || el.innerText || el.getAttribute('title') || '').trim().replace(/\s+/g, ' ').slice(0, 90);
  const targets = [...document.querySelectorAll('button,a,input:not([type="hidden"]),select,textarea,summary')].filter(visible);
  const text = [...document.querySelectorAll('p,small,dt,dd,label,td,th,button,a')].filter(visible);
  const overflow = [...document.querySelectorAll('section,main,aside,form,dialog,.admin-card,.practice-question,.pane,.table-scroll')].filter(visible).filter(el => el.scrollWidth > el.clientWidth + 2);
  const contrast = [];
  const canvas = document.createElement('canvas'), ctx = canvas.getContext('2d');
  const rgb = value => { ctx.clearRect(0,0,1,1); ctx.fillStyle=value; ctx.fillRect(0,0,1,1); return [...ctx.getImageData(0,0,1,1).data]; };
  const luminance = channels => channels.slice(0,3).map(v => v/255).map(v => v <= .04045 ? v/12.92 : ((v+.055)/1.055)**2.4).reduce((sum,v,i) => sum+v*[.2126,.7152,.0722][i],0);
  for (const el of text) {
    const s=getComputedStyle(el), fg=rgb(s.color);
    let node=el, bg=[255,255,255,255];
    while(node) { const color=rgb(getComputedStyle(node).backgroundColor); if(color[3] === 255) { bg=color; break; } node=node.parentElement; }
    if(fg[3] !== 255 || Number(s.opacity) < 1 || !name(el)) continue;
    const a=luminance(fg), b=luminance(bg), ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
    const size=parseFloat(s.fontSize), large=size>=24 || (size>=18.66 && Number(s.fontWeight)>=700);
    if(ratio < (large ? 3 : 4.5)-.05) contrast.push({text:name(el), ratio:Math.round(ratio*100)/100, size, selector:el.id || el.className});
  }
  const at = selector => { const el=document.querySelector(selector); return el && visible(el) ? Math.round(el.getBoundingClientRect().top + scrollY) : null; };
  return {
    route:location.pathname+location.search, width:innerWidth, height:document.documentElement.scrollHeight,
    pageOverflow:document.documentElement.scrollWidth > innerWidth,
    internalOverflow:overflow.map(el => ({selector:el.id||el.className, scroll:el.scrollWidth, width:el.clientWidth, overflow:getComputedStyle(el).overflowX})),
    smallText:text.filter(el => parseFloat(getComputedStyle(el).fontSize)<12).map(el => ({text:name(el), size:getComputedStyle(el).fontSize})).slice(0,25),
    smallTargets:targets.filter(el => { const b=el.getBoundingClientRect(); return b.width<24 || b.height<24; }).map(el => ({tag:el.tagName, text:name(el), w:Math.round(el.getBoundingClientRect().width), h:Math.round(el.getBoundingClientRect().height)})).slice(0,25),
    unnamedButtons:targets.filter(el => el.tagName==='BUTTON' && !name(el)).length,
    contrast:contrast.slice(0,30),
    primaryActions:[...document.querySelectorAll('.btn-primary')].filter(visible).map(el => ({text:name(el), y:Math.round(el.getBoundingClientRect().top+scrollY)})),
    questionY:at('#practicePrompt'), answerY:at('.practice-options'), submitY:at('#submitExamButton'), telemetry:typeof telemetryActive==='undefined' ? null : telemetryActive,
    headings:[...document.querySelectorAll('h1,h2,h3')].filter(visible).map(el => ({tag:el.tagName,text:name(el)}))
  };
}
