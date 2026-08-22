(() => {
  const c=window.CHANNEL||{};
  const v=document.getElementById('videoPlayer');
  const loading=document.getElementById('playerLoading');
  const error=document.getElementById('playerError');
  const text=document.getElementById('errorText');
  const retry=document.getElementById('retryBtn');
  let hls=null, attempts=0;
  const showLoading=x=>{if(loading) loading.hidden=!x;if(x&&error) error.hidden=true};
  const fail=msg=>{showLoading(false);if(text)text.textContent=msg;if(error)error.hidden=false};
  function play(){
    if(!c.stream){fail('This channel has no valid .m3u8 stream URL in its JSON data.');return;}
    showLoading(true); attempts=0;
    if(hls){hls.destroy();hls=null}
    v.pause();v.removeAttribute('src');v.load();
    if(window.Hls&&Hls.isSupported()){
      hls=new Hls({enableWorker:true,lowLatencyMode:true,backBufferLength:30,maxBufferLength:30,manifestLoadingMaxRetry:2,levelLoadingMaxRetry:2});
      hls.loadSource(c.stream);hls.attachMedia(v);
      hls.on(Hls.Events.MANIFEST_PARSED,()=>{showLoading(false);v.play().catch(()=>{})});
      hls.on(Hls.Events.ERROR,(_,d)=>{
        if(!d.fatal)return;
        if(attempts<3){attempts++;setTimeout(()=>{if(hls){showLoading(true);hls.startLoad()}},1000*attempts)}
        else fail('Stream is unavailable, blocked by the broadcaster, or not browser-playable.');
      });
    } else if(v.canPlayType('application/vnd.apple.mpegurl')){
      v.src=c.stream;
      v.addEventListener('loadedmetadata',()=>{showLoading(false);v.play().catch(()=>{})},{once:true});
      v.addEventListener('error',()=>fail('The HLS stream is unavailable or blocked.'),{once:true});
    } else fail('This browser does not support HLS playback.');
  }
  retry?.addEventListener('click',play);play();
})();
