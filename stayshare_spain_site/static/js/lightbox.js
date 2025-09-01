document.addEventListener('click', function(e){
  const a = e.target.closest('a.lightbox'); if(!a) return;
  e.preventDefault();
  const src = a.getAttribute('href');
  const overlay = document.createElement('div'); overlay.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.85);display:flex;align-items:center;justify-content:center;z-index:9999';
  const img = document.createElement('img'); img.src=src; img.style.cssText='max-width:90vw;max-height:90vh;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,.5)';
  overlay.appendChild(img); document.body.appendChild(overlay);
  overlay.addEventListener('click', ()=>overlay.remove());
});