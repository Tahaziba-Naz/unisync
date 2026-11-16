(() => {
 const results=document.querySelector('#results'); if(!results) return;
 let page=1,totalPages=1,timer;
 const params=new URLSearchParams(); (window.UNISYNC_CATEGORIES||[]).forEach(c=>params.append('category',c));
 async function load(){
  results.innerHTML='<div class="loading">Loading approved information…</div>';
  const q=new URLSearchParams(params); const term=document.querySelector('#search').value.trim(); if(term) q.set('q',term);
  q.set('page',page); q.set('sort',document.querySelector('#sort').value); if(document.querySelector('#upcoming').checked) q.set('deadline','upcoming');
  try { const res=await fetch('/api/records?'+q); if(!res.ok) throw new Error('Could not load information.'); const data=await res.json(); totalPages=data.pages||1;
   results.innerHTML=data.items.length?data.items.map(r=>`<article class="card"><span class="tag">${escapeHtml(r.category.replaceAll('_',' '))}</span><h3><a href="/record/${r.id}">${escapeHtml(r.title)}</a></h3><p>${escapeHtml((r.description||'Open the details to learn more.').slice(0,160))}</p><div class="card-foot">${r.deadline?'Deadline '+new Date(r.deadline+'T00:00:00').toLocaleDateString():'No deadline listed'}</div></article>`).join(''):'<div class="empty"><h3>No approved information found</h3><p>Try another search, or check back after administrators review new source information.</p></div>';
   document.querySelector('#page-label').textContent=data.total?`Page ${page} of ${data.pages} · ${data.total} results`:'0 results';
  } catch(e){results.innerHTML=`<div class="empty"><h3>Could not load information</h3><p>${escapeHtml(e.message)}</p><button class="button" onclick="location.reload()">Retry</button></div>`;}
  document.querySelector('#prev').disabled=page<=1; document.querySelector('#next').disabled=page>=totalPages;
 }
 function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
 document.querySelector('#search').addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(()=>{page=1;load()},250)});
 document.querySelector('#sort').addEventListener('change',()=>{page=1;load()}); document.querySelector('#upcoming').addEventListener('change',()=>{page=1;load()});
 document.querySelector('#prev').addEventListener('click',()=>{if(page>1){page--;load()}}); document.querySelector('#next').addEventListener('click',()=>{if(page<totalPages){page++;load()}}); load();
})();
