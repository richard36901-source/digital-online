async function loadFacebookPixel() {
  const p = new URLSearchParams(location.search);
  const marketer = p.get('marketer') || '';

  try {
    const res = await fetch('/marketers/marketers.json');
    const marketers = await res.json();
    // Default to the "yahav" marketer whenever the link carries no marketer
    // param, or names one that isn't in marketers.json.
    const mk = (marketer && marketers[marketer]) ? marketer : 'yahav';
    const m = marketers[mk];
    if (!m || !m.fb_pixel) return;

    const s = document.createElement('script');
    s.innerHTML = `
      !function(f,b,e,v,n,t,s){
        if(f.fbq)return;
        n=f.fbq=function(){ n.callMethod ?
          n.callMethod.apply(n, arguments) : n.queue.push(arguments) };
        if(!f._fbq) f._fbq=n;
        n.push=n; n.loaded=!0; n.version='2.0'; n.queue=[];
        t=b.createElement(e); t.async=!0; t.src=v;
        s=b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t,s);
      }(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');

      fbq('init', '${m.fb_pixel}');
      fbq('track', 'PageView');
    `;
    document.head.appendChild(s);
  } catch (e) {}
}

loadFacebookPixel();