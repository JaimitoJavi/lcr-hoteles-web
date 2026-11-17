(function(){
  var b=document.querySelector('.burger'),n=document.getElementById('nav');
  if(b&&n)b.addEventListener('click',function(){var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o)});
  document.querySelectorAll('form.form').forEach(function(f){
    f.addEventListener('submit',function(e){
      e.preventDefault();var s=f.querySelector('.status');s.className='status';s.textContent='…';
      fetch(f.action,{method:'POST',headers:{'Accept':'application/json'},body:new URLSearchParams(new FormData(f))})
        .then(function(r){return r.json().then(function(j){return{ok:r.ok,j:j}})})
        .then(function(x){if(x.ok){s.textContent=f.dataset.ok;f.reset()}else throw 0})
        .catch(function(){s.className='status err';s.textContent=f.dataset.err});
    });
  });
  var q=new URLSearchParams(location.search),a=document.getElementById('alojamiento');
  if(a&&q.get('alojamiento'))a.value=q.get('alojamiento');
  var as=document.getElementById('asunto');if(as&&q.get('asunto')&&!as.value)as.value=q.get('asunto').replace(/-/g,' ');
})();
