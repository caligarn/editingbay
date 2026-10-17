'use strict';
const $ = s => document.querySelector(s);
const state = {data:null, category:'', selected:null, version:null};
const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const driveId = url => /^https:\/\/drive\.google\.com\/file\/d\/([A-Za-z0-9_-]+)\/view$/.exec(url||'')?.[1];
const time = seconds => {const s=Math.max(0,Math.floor(Number(seconds)||0));return `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`;};
function badge(c){return `<span class="badge ${c.reviewStatus==='Caption QA pending'?'warn':c.reviewStatus==='Media missing'?'missing':''}">${esc(c.reviewStatus)}</span>`;}
function filtered(){
  const query=$('#search').value.trim().toLowerCase();const person=$('#person').value;const status=$('#status').value;
  return state.data.clips.filter(c => (!state.category||c.category===state.category)&&(!person||c.person===person)&&(!status||c.reviewStatus===status)&&[c.label,c.topic,c.sourceIds.join(' '),c.id,c.category].join(' ').toLowerCase().includes(query)).sort((a,b)=>$('#sort').value==='name'?a.label.localeCompare(b.label,undefined,{numeric:true}):b.date.localeCompare(a.date)||a.id.localeCompare(b.id));
}
function renderGrid(){
  const clips=filtered();$('#result-count').textContent=`${clips.length} of ${state.data.clips.length} clips · latest versions shown`;
  $('#empty').hidden=clips.length!==0;
  $('#grid').innerHTML=clips.map(c=>{const v=c.versions[0];return `<article class="clip" data-id="${esc(c.id)}"><button class="poster-button ${state.selected===c.id?'selected':''}" data-open="${esc(c.id)}" aria-label="Review ${esc(c.label)} ${v.id}: ${esc(c.topic)}">${v.thumbnail?`<img src="${esc(v.thumbnail)}" alt="${esc(c.label)} — ${esc(c.topic)}" loading="lazy">`:`<span class="poster-missing"><b>Media missing</b><span>Verified video & thumbnail needed</span></span>`}${v.video?'<span class="play-disc" aria-hidden="true">▶</span>':''}${v.duration?`<span class="duration">${time(v.duration)}</span>`:''}</button><div class="card-meta"><h2>${esc(c.label)}</h2><span class="version-tag">${v.id}${c.hubEditions?' · hub':''}</span></div><p class="topic">${esc(c.topic)}</p><div class="card-bottom">${badge(c)}<span class="card-id">${c.id}${c.versions.length>1?` · ${c.versions.length} versions`:''}</span></div></article>`;}).join('');
  $('#grid').querySelectorAll('[data-open]').forEach(b=>b.addEventListener('click',()=>openClip(b.dataset.open)));
  $('#grid').querySelectorAll('img').forEach(img=>img.addEventListener('error',()=>{const fallback=document.createElement('span');fallback.className='poster-missing';fallback.textContent='Thumbnail unavailable';img.replaceWith(fallback);},{once:true}));
}
function current(){const c=state.data.clips.find(c=>c.id===state.selected);return [c,c?.versions.find(v=>v.id===state.version)];}
function reference(){const [c,v]=current();return `${c.label} ${v.id}${c.hubEditions?' (hub edition)':''} at ${$('#timestamp').value || '00:00'}: ${$('#feedback').value.trim() || '...'}`;}
function updateReference(){$('#reference').textContent=reference();}
function toast(message){const el=$('#toast');el.textContent=message;el.hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.hidden=true,3200);}
async function copyReference(){
  const stamp=$('#timestamp');
  if(!/^\d{2,}:\d{2}$/.test(stamp.value)||Number(stamp.value.split(':')[1])>59){stamp.setCustomValidity('Use minutes:seconds, such as 00:23.');stamp.reportValidity();return;}
  stamp.setCustomValidity('');
  try{await navigator.clipboard.writeText(reference());toast('Reference copied. Paste it into your feedback.');}
  catch{const range=document.createRange();range.selectNodeContents($('#reference'));const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);toast('Clipboard unavailable. Select and copy the reference below.');}
}
function openClip(id,versionId=null,scroll=true){
  document.querySelector('video')?.pause();
  const c=state.data.clips.find(c=>c.id===id);if(!c)return;
  state.selected=id;state.version=versionId||c.latestVersion;const v=c.versions.find(v=>v.id===state.version)||c.versions[0];state.version=v.id;
  const latest=v.id===c.latestVersion;
  const drive=driveId(v.video);
  const playerMarkup=drive?`<div class="drive-player"><iframe src="https://drive.google.com/file/d/${esc(drive)}/preview" title="${esc(c.label)} ${v.id} restricted Drive player" allow="autoplay; fullscreen" allowfullscreen></iframe><a class="drive-fallback" href="${esc(v.video)}" target="_blank" rel="noopener noreferrer">Open in Drive ↗</a><p>Sign in with an account that can view this video. If the player does not load here, open it in Drive.</p></div>`:v.video?`<video id="player" controls playsinline preload="metadata" poster="${esc(v.thumbnail||'')}" src="${esc(v.video)}" aria-label="${esc(c.label)} ${v.id}"></video>`:'<div class="missing-player"><h2>Media missing</h2><p>This edition is unavailable. No alternate asset has been substituted.</p></div>';
  const sourceRanges=v.ranges?.length?v.ranges.map(r=>`${time(r[0])}–${time(r[1])} (${Number(r[0]).toFixed(3)}–${Number(r[1]).toFixed(3)} s)`).join('; '):'Exact source ranges are not available in this gallery.';
  $('#review').innerHTML=`<div class="review-top"><p>NOW REVIEWING · ${esc(c.id)}</p><button id="close-review" aria-label="Close clip review">Close ×</button></div><div class="review-body"><div class="player-wrap">${playerMarkup}</div><div class="review-info">${latest?badge(c):'<span class="badge">Older version</span>'}<h2>${esc(c.label)}</h2><p class="review-topic">${esc(c.topic)}</p><div class="version-row"><label for="version">Version</label><select id="version">${c.versions.map(x=>`<option value="${x.id}" ${x.id===v.id?'selected':''}>${x.id}${c.hubEditions?' · hub edition':''}${x.id===c.latestVersion?' · latest':''}${!x.video?' · unavailable':''}</option>`).join('')}</select></div><p class="version-note">${c.hubEditions?'Hub editions: v1 pre-grade; v2 natural grade.':'Stable clip label; each revision keeps its own version.'}</p>${v.captionQA?'<div class="qa-panel"><strong>Caption QA pending</strong><p>This draft requires a listening pass. Captions may contain errors.</p></div>':''}<div class="feedback-box"><div class="feedback-heading"><label for="feedback">Your feedback reference</label><input id="timestamp" class="time-field" aria-label="Feedback timestamp" value="00:00" inputmode="numeric"></div><textarea id="feedback" aria-label="Feedback note" placeholder="What would you change at this moment?"></textarea><div class="feedback-actions"><button class="primary" id="copy">Copy feedback reference</button>${v.video&&!drive?'<button id="seek">Jump to time</button>':''}</div><p class="feedback-hint">${drive?'Enter the timestamp shown in Drive. ':''}Copying sends nothing. Your note clears when you close or change the clip.</p><div class="reference-preview" id="reference"></div></div><details class="provenance"><summary>Clip & source reference</summary><dl><dt>Clip</dt><dd>${esc(c.id)} · ${esc(c.label)} ${v.id}</dd><dt>Source IDs</dt><dd>${esc(c.sourceIds.join('; ')||'Unverified')}</dd><dt>Original source ranges</dt><dd>${esc(sourceRanges)}</dd></dl><p>Feedback timecodes refer to this review video. These are review drafts; no final approval is implied.</p></details></div></div>`;
  $('#review').hidden=false;updateReference();renderGrid();
  $('#version').addEventListener('change',e=>openClip(c.id,e.target.value,false));
  $('#copy').addEventListener('click',copyReference);
  $('#seek')?.addEventListener('click',()=>{
    const stamp=$('#timestamp').value;
    if(!/^\d{2,}:\d{2}$/.test(stamp)||Number(stamp.split(':')[1])>59){toast('Use minutes:seconds, such as 00:23.');return;}
    const [m,s]=stamp.split(':').map(Number);const player=$('#player');
    if(player&&Number.isFinite(player.duration)){player.currentTime=Math.min(m*60+s,Math.max(0,player.duration-.1));}
  });
  $('#feedback').addEventListener('input',updateReference);
  $('#timestamp').addEventListener('input',()=>{$('#timestamp').setCustomValidity('');updateReference();});
  $('#close-review').addEventListener('click',closeReview);
  const player=$('#player');if(player){
    player.addEventListener('timeupdate',()=>{if(document.activeElement!==$('#timestamp')){$('#timestamp').value=time(player.currentTime);updateReference();}});
    player.addEventListener('error',()=>{const wrap=$('.player-wrap');const message=document.createElement('p');message.className='missing-player';message.textContent='Video unavailable or unsupported. No alternate asset was substituted.';wrap.replaceChildren(message);});
  }
  history.replaceState(null,'',`#${encodeURIComponent(c.id)}/${v.id}`);
  if(scroll){$('#review').scrollIntoView({behavior:'auto',block:'start'});$('#close-review').focus({preventScroll:true});}
}
function closeReview(){const id=state.selected;$('#player')?.pause();$('#review').hidden=true;$('#review').replaceChildren();state.selected=null;state.version=null;history.replaceState(null,'',location.pathname);renderGrid();$(`[data-open="${id}"]`)?.focus({preventScroll:true});}
function reset(){state.category='';$('#search').value='';$('#person').value='';$('#status').value='';$('#sort').value='new';updateTabs();renderGrid();}
function updateTabs(){document.querySelectorAll('[data-category]').forEach(b=>{const active=b.dataset.category===state.category;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});}
async function init(){
 try{const res=await fetch('/inventory.json');if(!res.ok)throw Error('Inventory unavailable');state.data=await res.json();
  const n=state.data.counts;$('#stats').innerHTML=`<div class="stat"><strong>${n.clips}</strong><span>distinct clips</span></div><div class="stat"><strong>${n.latestPlayable}</strong><span>review files</span></div><div class="stat"><strong>${n.clips-n.latestPlayable}</strong><span>media missing</span></div>`;$('#all-total').textContent=n.clips;
  $('#snapshot-date').textContent=`Snapshot · ${state.data.snapshotDate}`;
  $('#qa-summary').textContent=`${n.captionQAPending} latest drafts need caption listening confirmation. Drafts may contain errors; appearance here does not imply final approval.`;
  $('#qa-shortcut').textContent=`Show ${n.captionQAPending} flagged drafts ↗`;
  [...new Set(state.data.clips.map(c=>c.person))].sort().forEach(p=>{const o=document.createElement('option');o.value=p;o.textContent=p;$('#person').append(o);});
  ['search','person','status','sort'].forEach(id=>$('#'+id).addEventListener(id==='search'?'input':'change',renderGrid));
  document.querySelectorAll('[data-category]').forEach(b=>b.addEventListener('click',()=>{state.category=b.dataset.category;updateTabs();renderGrid();}));
  $('#toggle-filters').addEventListener('click',()=>{const open=$('.filters').classList.toggle('expanded');$('#toggle-filters').setAttribute('aria-expanded',String(open));});
  $('#reset').addEventListener('click',reset);$('#empty-reset').addEventListener('click',reset);
  $('#qa-shortcut').addEventListener('click',()=>{reset();$('#status').value='Caption QA pending';renderGrid();$('#grid').scrollIntoView({block:'start'});});
  renderGrid();const [id,v]=decodeURIComponent(location.hash.slice(1)).split('/');if(id)openClip(id,v,false);
 }catch(e){$('#result-count').textContent='Could not load the gallery. Please refresh or try again later.';$('#empty').hidden=false;}
}
init();
