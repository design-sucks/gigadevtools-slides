/* Minimal navigation bridge for the unchanged v25 UI/motion modules. */
var slidesEl=document.getElementById('slides'),slides=slidesEl.querySelectorAll(':scope>.slide'),total=slides.length,cur=0,lockScroll=false;
var breadLabels=JSON.parse(document.getElementById('sk-deck-state').textContent).slides.map(s=>s.label);
window.breadLabelsCopy=breadLabels;
function stopAnims(){}
function setInitialVidFrame(){}
function positionBubble(){
 const items=document.querySelectorAll('#bread .bread-item'),bubble=document.getElementById('breadBubble'),el=items[cur];
 if(el&&bubble){bubble.style.left=el.offsetLeft+'px';bubble.style.top=el.offsetTop+'px';bubble.style.width=el.offsetWidth+'px';bubble.style.height=el.offsetHeight+'px';}
}
function updateUI(){
 document.querySelectorAll('#navbar .nav-dot,#bread .bread-item').forEach(el=>el.classList.remove('on'));
 document.querySelectorAll('#navbar .nav-dot')[cur]?.classList.add('on');
 document.querySelectorAll('#bread .bread-item')[cur]?.classList.add('on');positionBubble();
}
function goTo(n){
 if(!Number.isInteger(n)||n<0||n>=slides.length)return;
 if(window.SalesKitMotion)return SalesKitMotion.navigate(n);
 cur=n;slidesEl.scrollTop=slides[n].offsetTop;updateUI();
}
slidesEl.addEventListener('scroll',()=>{if(lockScroll)return;let best=0,distance=Infinity;slides.forEach((s,i)=>{const d=Math.abs(s.offsetTop-slidesEl.scrollTop);if(d<distance){distance=d;best=i;}});if(cur!==best){cur=best;updateUI();}},{passive:true});
