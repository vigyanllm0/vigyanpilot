/* reveal.js — scroll-reveal animations (progressive enhancement)
   Content is visible by default. JS adds .visible when elements enter viewport. */
(function(){
  var els=document.querySelectorAll('.reveal');
  if(!els.length)return;
  function check(){
    for(var i=0;i<els.length;i++){
      var r=els[i].getBoundingClientRect();
      if(r.top<window.innerHeight-60)els[i].classList.add('visible');
    }
  }
  check();
  window.addEventListener('scroll',check,{passive:true});
})();
