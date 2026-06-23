// static/js/main.js
// tiny helper to mark active links on client-side nav changes (when using pushState later)
(function(){
  const links = document.querySelectorAll('.nav-link');
  const path = location.pathname;
  links.forEach(a=>{
    if(a.getAttribute('href') === path){ a.classList.add('active'); }
  });
})();
