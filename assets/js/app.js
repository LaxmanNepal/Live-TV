const state={channels:[],filtered:[],current:null,hls:null,favorites:new Set(JSON.parse(localStorage.getItem('livetv-favorites')||'[]')),recent:JSON.parse(localStorage.getItem('livetv-recent')||'[]'),category:'all',search:'',favoritesMode:false,retries:0,retryTimer:null};
const $=s=>document.querySelector(s);
const els={search:$('#channelSearch'),results:$('#searchResults'),player:$('#videoPlayer'),empty:$('#playerEmpty'),loading:$('#playerLoading'),error:$('#playerError'),nowName:$('#nowName'),nowProgram:$('#nowProgram'),nowLogo:$('#nowLogo'),popular:$('#popularChannels'),grid:$('#channelGrid'),chips:$('#categoryChips'),count:$('#channelCount'),browseTitle:$('#browseTitle'),playerCard:$('#playerCard')};

async function init(){
  try{
    const [channelResponse,statusResponse]=await Promise.all([fetch('data/channels.json',{cache:'no-store'}),fetch('data/stream-status.json',{cache:'no-store'}).catch(()=>null)]);
    if(!channelResponse.ok)throw new Error(`HTTP ${channelResponse.status}`);
    const data=await channelResponse.json();
    const status=statusResponse?.ok?await statusResponse.json():null;
    state.channels=(data.channels||[]).filter(c=>c&&c.enabled!==false).map(c=>({...c,health:status?.channels?.[c.id]||null}));
    renderAll();loadTheme();handleHash();
  }catch(e){console.error(e);els.grid.innerHTML='<div class="empty-state"><strong>Channel data unavailable</strong><br>Please refresh after the TV data sync completes.</div>';}
}
function renderAll(){renderCategories();renderPopular();renderGrid();}
function logoHTML(ch,cls='card-logo'){if(!ch.logo)return `<div class="${cls} logo-fallback"><i class="fa-solid fa-tv"></i></div>`;return `<img class="${cls}" src="${escapeHtml(ch.logo)}" alt="${escapeHtml(ch.name)} logo" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.hidden=false"><div class="${cls} logo-fallback" hidden><i class="fa-solid fa-tv"></i></div>`;}
function statusHTML(ch){const s=ch.health?.status;return s==='online'?'<span class="stream-status online">● Online</span>':s==='offline'||s==='invalid'?'<span class="stream-status offline">● Offline</span>':'';}
function renderPopular(){const list=state.channels.filter(c=>c.stream).slice(0,12);els.popular.innerHTML=list.length?list.map(cardHTML).join(''):'<div class="empty-state compact">No live streams are currently configured. The GitHub sync will populate them automatically.</div>';bindCards(els.popular);}
function cardHTML(ch){return `<article class="channel-card" data-id="${escapeHtml(ch.id)}">${logoHTML(ch)}<div class="card-body"><div class="card-name">${escapeHtml(ch.name)}</div><div class="card-sub">${escapeHtml(ch.language||'')} • ${escapeHtml(ch.category||'')}</div>${statusHTML(ch)}</div></article>`;}
function renderCategories(){const cats=['all',...new Set(state.channels.map(c=>c.category).filter(Boolean))];els.chips.innerHTML=cats.map(c=>`<button class="chip ${state.category===c&&!state.favoritesMode?'active':''}" data-category="${escapeHtml(c)}" type="button">${c==='all'?'All':title(c)}</button>`).join('');els.chips.querySelectorAll('.chip').forEach(b=>b.onclick=()=>{state.category=b.dataset.category;state.favoritesMode=false;renderCategories();renderGrid();scrollBrowse();});}
function searchable(c){return `${c.name} ${c.language} ${c.country} ${c.category} ${c.slug||''}`.toLowerCase();}
function getFiltered(){const q=state.search;return state.channels.filter(c=>(!state.favoritesMode||state.favorites.has(c.id))&&(state.category==='all'||c.category===state.category)&&(!q||searchable(c).includes(q)));}
function renderGrid(){state.filtered=getFiltered();els.count.textContent=`${state.filtered.length} channel${state.filtered.length!==1?'s':''}`;els.browseTitle.textContent=state.favoritesMode?'Favorites':state.category==='all'?'All channels':`${title(state.category)} channels`;els.grid.innerHTML=state.filtered.length?state.filtered.map(gridCard).join(''):'<div class="empty-state">No channels found.</div>';bindCards(els.grid);}
function gridCard(ch){const fav=state.favorites.has(ch.id);return `<article class="grid-card" data-id="${escapeHtml(ch.id)}">${logoHTML(ch,'grid-logo')}<div class="grid-body"><button class="fav-btn ${fav?'active':''}" data-fav="${escapeHtml(ch.id)}" type="button" aria-label="${fav?'Remove':'Add'} ${escapeHtml(ch.name)} favorite"><i class="fa-${fav?'solid':'regular'} fa-heart"></i></button><div class="grid-name">${escapeHtml(ch.name)}</div><span class="tag">${escapeHtml(ch.category||'TV')}</span>${statusHTML(ch)}</div></article>`;}
function bindCards(root){root.querySelectorAll('[data-id]').forEach(card=>card.onclick=e=>{if(e.target.closest('[data-fav]'))return;selectChannel(card.dataset.id);});root.querySelectorAll('[data-fav]').forEach(btn=>btn.onclick=e=>{e.stopPropagation();toggleFavorite(btn.dataset.fav);});}
function selectChannel(id){const ch=state.channels.find(c=>c.id===id);if(!ch)return;state.current=ch;state.retries=0;rememberRecent(id);history.replaceState(null,'',`#${encodeURIComponent(ch.slug||ch.id)}`);els.nowName.textContent=ch.name;els.nowProgram.textContent=ch.program||`${ch.language||''} • ${title(ch.category||'TV')}`;els.nowLogo.innerHTML=ch.logo?`<img class="channel-logo large-logo" src="${escapeHtml(ch.logo)}" alt="${escapeHtml(ch.name)} logo" onerror="this.style.display='none';this.nextElementSibling.hidden=false"><i class="fa-solid fa-tv" hidden></i>`:'<i class="fa-solid fa-tv"></i>';els.empty.hidden=true;els.error.hidden=true;playStream(ch);scrollPlayer();}
function playStream(ch){
  destroyPlayer(false);els.loading.hidden=false;els.error.hidden=true;state.retries=state.retries||0;
  if(!ch.stream){showError('This channel has no stream URL in the source data.');return;}
  if(location.protocol==='https:'&&/^http:/i.test(ch.stream)){showError('This stream uses HTTP and is blocked by the browser on an HTTPS site. The source must provide HTTPS.');return;}
  const isHls=/\.m3u8(?:$|\?)/i.test(ch.stream);
  els.player.crossOrigin='anonymous';
  if(isHls&&window.Hls&&Hls.isSupported()){
    state.hls=new Hls({enableWorker:true,lowLatencyMode:true,maxBufferLength:30,backBufferLength:30,manifestLoadingMaxRetry:2,levelLoadingMaxRetry:2,fragLoadingMaxRetry:2});
    state.hls.attachMedia(els.player);
    state.hls.on(Hls.Events.MEDIA_ATTACHED,()=>state.hls?.loadSource(ch.stream));
    state.hls.on(Hls.Events.MANIFEST_PARSED,()=>{els.loading.hidden=true;state.retries=0;els.player.play().catch(()=>{});});
    state.hls.on(Hls.Events.ERROR,(_,data)=>handleHlsError(data));
  }else if(isHls&&els.player.canPlayType('application/vnd.apple.mpegurl')){
    els.player.src=ch.stream;els.player.addEventListener('loadedmetadata',onNativeLoaded,{once:true});els.player.addEventListener('error',onNativeError,{once:true});
  }else{
    els.player.src=ch.stream;els.player.addEventListener('loadedmetadata',onNativeLoaded,{once:true});els.player.addEventListener('error',onNativeError,{once:true});
  }
}
function onNativeLoaded(){els.loading.hidden=true;state.retries=0;els.player.play().catch(()=>{});}
function onNativeError(){if(state.current) scheduleRetry('The stream could not be loaded. Retrying automatically…');}
function handleHlsError(data){
  if(!data?.fatal)return;
  if(data.type===Hls.ErrorTypes.NETWORK_ERROR&&state.hls){scheduleRetry('Network problem. Reconnecting…');return;}
  if(data.type===Hls.ErrorTypes.MEDIA_ERROR&&state.hls){try{state.hls.recoverMediaError();els.loading.hidden=false;return;}catch{}}
  scheduleRetry('The HLS stream failed. Retrying automatically…');
}
function scheduleRetry(message){
  if(state.retryTimer||!state.current)return;
  state.retries+=1;
  if(state.retries>3){destroyPlayer(false);showError('Stream unavailable after several attempts. Check the stream source or try again later.');return;}
  els.loading.hidden=false;els.error.hidden=true;els.loading.querySelector('span:last-child').textContent=`${message} (${state.retries}/3)`;
  state.retryTimer=setTimeout(()=>{state.retryTimer=null;playStream(state.current);},Math.min(2500*state.retries,8000));
}
function destroyPlayer(clearRetry=true){if(clearRetry&&state.retryTimer){clearTimeout(state.retryTimer);state.retryTimer=null}if(state.hls){state.hls.destroy();state.hls=null}els.player.pause();els.player.removeAttribute('src');els.player.load();}
function showError(message){els.loading.hidden=true;els.error.hidden=false;els.error.querySelector('span').textContent=message;}
function toggleFavorite(id){if(state.favorites.has(id))state.favorites.delete(id);else state.favorites.add(id);localStorage.setItem('livetv-favorites',JSON.stringify([...state.favorites]));renderGrid();}
function rememberRecent(id){state.recent=[id,...state.recent.filter(x=>x!==id)].slice(0,12);localStorage.setItem('livetv-recent',JSON.stringify(state.recent));}
function showFavorites(){state.favoritesMode=true;state.category='all';state.search='';els.search.value='';els.results.hidden=true;renderCategories();renderGrid();scrollBrowse();}
function doSearch(){state.search=els.search.value.trim().toLowerCase();state.favoritesMode=false;state.category='all';const q=state.search;if(!q){els.results.hidden=true;renderCategories();renderGrid();return}const found=state.channels.filter(c=>searchable(c).includes(q)).sort((a,b)=>scoreSearch(b,q)-scoreSearch(a,q)).slice(0,10);els.results.innerHTML=found.length?found.map(c=>`<div class="result-item" data-search-id="${escapeHtml(c.id)}">${logoHTML(c,'channel-logo')}<div><strong>${escapeHtml(c.name)}</strong><div class="card-sub">${escapeHtml(c.country||'')} • ${escapeHtml(c.category||'')} ${statusHTML(c)}</div></div></div>`).join(''):'<div class="result-item">No matching channels</div>';els.results.hidden=false;renderCategories();renderGrid();els.results.querySelectorAll('[data-search-id]').forEach(x=>x.onclick=()=>{selectChannel(x.dataset.searchId);els.results.hidden=true;});}
function scoreSearch(c,q){const n=c.name.toLowerCase();return n===q?100:n.startsWith(q)?80:n.includes(q)?60:20;}
function scrollBrowse(){document.querySelector('#browse')?.scrollIntoView({behavior:'smooth',block:'start'});}
function scrollPlayer(){els.playerCard?.scrollIntoView({behavior:'smooth',block:'start'});}
function title(s=''){return s.charAt(0).toUpperCase()+s.slice(1)}
function escapeHtml(s=''){return String(s).replace(/[&<>\'\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]||c));}
function toggleTheme(){document.body.classList.toggle('dark');localStorage.setItem('livetv-theme',document.body.classList.contains('dark')?'dark':'light');updateThemeIcon();}
function loadTheme(){if(localStorage.getItem('livetv-theme')==='dark')document.body.classList.add('dark');updateThemeIcon();}
function updateThemeIcon(){const dark=document.body.classList.contains('dark');$('#themeToggle').innerHTML=`<i class="fa-solid fa-${dark?'sun':'moon'}"></i>`;}
function handleHash(){const hash=decodeURIComponent(location.hash.slice(1));if(!hash||hash==='home')return;const ch=state.channels.find(c=>c.id===hash||c.slug===hash);if(ch)selectChannel(ch.id);}

$('#themeToggle').onclick=toggleTheme;$('#themeNav').onclick=toggleTheme;$('#viewAllBtn').onclick=()=>{state.favoritesMode=false;state.category='all';renderCategories();renderGrid();scrollBrowse();};$('#allNav').onclick=()=>{state.favoritesMode=false;state.category='all';renderCategories();renderGrid();scrollBrowse();};$('#favoritesNav').onclick=showFavorites;$('#retryBtn').onclick=()=>{if(state.current){state.retries=0;playStream(state.current);}};$('#fullscreenBtn').onclick=()=>{const el=els.playerCard;if(document.fullscreenElement)document.exitFullscreen();else (el.requestFullscreen||el.webkitRequestFullscreen)?.call(el);};
els.search.addEventListener('input',doSearch);window.addEventListener('hashchange',handleHash);document.addEventListener('click',e=>{if(!e.target.closest('.search-wrap'))els.results.hidden=true});document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();els.search.focus();}});window.addEventListener('beforeunload',()=>destroyPlayer());
init();
