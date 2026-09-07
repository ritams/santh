/* Shared navigation and local, typo-tolerant site search. */
(() => {
  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.nav');
  const header = document.querySelector('.header');
  function closeMenu() {
    menu.classList.remove('active'); nav.classList.remove('active');
    menu.setAttribute('aria-expanded', 'false'); menu.setAttribute('aria-label', 'Open navigation');
    document.body.style.overflow = '';
  }
  menu.addEventListener('click', () => {
    const open = menu.getAttribute('aria-expanded') !== 'true';
    menu.classList.toggle('active', open); nav.classList.toggle('active', open);
    menu.setAttribute('aria-expanded', String(open)); menu.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    document.body.style.overflow = open ? 'hidden' : '';
  });
  nav.addEventListener('click', e => { if (e.target.closest('a')) closeMenu(); });
  window.addEventListener('resize', () => { if (innerWidth > 768) closeMenu(); });
  const scrollTopButton = document.querySelector('.scroll-top');
  let idleTimer;
  function updateScrollControls() {
    header.classList.toggle('scrolled', scrollY > 30);
    scrollTopButton.hidden = scrollY < 120;
    scrollTopButton.classList.remove('is-idle');
    scrollTopButton.inert = false;
    clearTimeout(idleTimer);
    if (!scrollTopButton.hidden) idleTimer = setTimeout(() => {
      // Preserve a keyboard user's focused control until they leave it.
      if (document.activeElement === scrollTopButton) return;
      scrollTopButton.classList.add('is-idle');
      scrollTopButton.inert = true;
    }, 2500);
  }
  for (const event of ['scroll', 'pointermove', 'pointerdown', 'keydown', 'touchstart']) {
    window.addEventListener(event, updateScrollControls, {passive:true});
  }
  scrollTopButton.addEventListener('blur', updateScrollControls);
  window.addEventListener('pageshow', updateScrollControls);
  updateScrollControls();
  scrollTopButton.addEventListener('click', () => {
    document.querySelector('#main').focus({preventScroll:true});
    window.scrollTo({top:0, behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && nav.classList.contains('active')) { closeMenu(); menu.focus(); }
    if (e.key === 'Tab' && nav.classList.contains('active')) {
      const links = [...nav.querySelectorAll('a'), menu];
      const i = links.indexOf(document.activeElement);
      if (e.shiftKey && (i <= 0)) {e.preventDefault(); menu.focus();}
      else if (!e.shiftKey && (i === links.length - 1)) {e.preventDefault(); links[0].focus();}
    }
  });
  if (!window.Fuse || !window.SEARCH_INDEX) return;
  const data = window.SEARCH_INDEX;
  const search = createSiteSearch(data);
  const publicationFilters = document.querySelector('.publication-filters');
  if (publicationFilters) {
    const type = document.querySelector('#publication-type');
    const year = document.querySelector('#publication-year');
    const query = document.querySelector('#publication-query');
    const topicButtons = [...publicationFilters.querySelectorAll('[data-topic]')];
    const articles = [...document.querySelectorAll('[data-publication]')];
    let topic = 'all', timer;
    function readPublicationURL() {
      const params = new URLSearchParams(location.search);
      const requestedTopic = params.get('topic');
      topic = topicButtons.some(button => button.dataset.topic === requestedTopic) ? requestedTopic : 'all';
      type.value = params.get('type') || 'all'; if (!type.value) type.value = 'all';
      year.value = params.get('year') || 'all'; if (!year.value) year.value = 'all';
      query.value = params.get('q') || '';
    }
    function filterPublications() {
      const q = query.value.trim();
      const matches = q ? new Set(search(q).filter(item => item.url.startsWith('pubs.html#')).map(item => item.url.split('#')[1])) : null;
      let visible = 0;
      for (const article of articles) {
        article.hidden = !((type.value === 'all' || article.dataset.kind === type.value)
          && (year.value === 'all' || article.dataset.year === year.value)
          && (topic === 'all' || article.dataset.topics.split(' ').includes(topic))
          && (!matches || matches.has(article.id)));
        if (!article.hidden) visible++;
      }
      for (const section of document.querySelectorAll('.content-section')) {
        section.hidden = !section.querySelector('[data-publication]:not([hidden])');
        document.querySelector(`.jump-links a[href="#${section.id}"]`).hidden = section.hidden;
      }
      for (const button of topicButtons) button.setAttribute('aria-pressed', String(button.dataset.topic === topic));
      document.querySelector('#publication-empty').hidden = visible !== 0;
      document.querySelector('#publication-status').textContent = `${visible} matching articles`;
      const url = new URL(location.href);
      for (const [key, value] of [['topic', topic], ['type', type.value], ['year', year.value], ['q', q]]) {
        if (value && value !== 'all') url.searchParams.set(key, value); else url.searchParams.delete(key);
      }
      history.replaceState(null, '', url);
    }
    for (const button of topicButtons) button.addEventListener('click', () => {topic = button.dataset.topic; filterPublications();});
    type.addEventListener('change', filterPublications);
    year.addEventListener('change', filterPublications);
    query.addEventListener('input', () => {clearTimeout(timer);timer = setTimeout(filterPublications, 100);});
    document.querySelector('#publication-reset').addEventListener('click', () => {
      clearTimeout(timer);topic = 'all';type.value = 'all';year.value = 'all';query.value = '';filterPublications();
    });
    window.addEventListener('popstate', () => {readPublicationURL();filterPublications();});
    readPublicationURL(); filterPublications(); publicationFilters.hidden = false;
  }

  const dialog = document.querySelector('.search-dialog');
  let returnFocus;
  function openSearch() {returnFocus = document.activeElement; closeMenu(); dialog.showModal(); document.body.style.overflow='hidden'; dialog.querySelector('input').focus();}
  document.querySelector('.search-trigger').addEventListener('click', e => {e.preventDefault(); openSearch();});
  dialog.querySelector('.search-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', e => {if(e.target === dialog) { const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close(); }});
  dialog.addEventListener('close', () => {document.body.style.overflow='';returnFocus?.focus();});
  document.addEventListener('keydown', e => {if((e.metaKey || e.ctrlKey) && e.key.toLowerCase()==='k'){e.preventDefault();if(dialog.open)dialog.close();else openSearch();}});
  if (!/Mac|iPhone|iPad/.test(navigator.platform)) document.querySelector('kbd').textContent='Ctrl K';
  const escape = s => s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function highlight(text,query) {
    const terms=query.toLowerCase().split(/\s+/).filter(t=>t.length>1);
    let out='',i=0;
    while(i<text.length){const term=terms.find(t=>text.toLowerCase().startsWith(t,i));if(term){out+='<mark>'+escape(text.slice(i,i+term.length))+'</mark>';i+=term.length;}else{out+=escape(text[i]);i++;}}
    return out;
  }
  function excerpt(text,query) {
    const terms=query.toLowerCase().split(/\s+/);let pos=terms.map(t=>text.toLowerCase().indexOf(t)).find(p=>p>=0) ?? 0;
    const start=Math.max(0,pos-50);return (start?'…':'')+text.slice(start,start+180)+(text.length>start+180?'…':'');
  }
  for(const root of document.querySelectorAll('.search-dialog,.search-page')) {
    const input=root.querySelector('input'),results=root.querySelector('.search-results'),status=root.querySelector('.search-status'),filters=root.querySelector('.search-filters');
    let category='All',limit=20,timer;
    const categories=['All','Research','Publications','Teaching','People','Opportunities','Contact','Projects'];
    for(const c of categories){const button=document.createElement('button');button.type='button';button.textContent=c;button.setAttribute('aria-pressed',String(c==='All'));button.addEventListener('click',()=>{category=c;limit=20;for(const b of filters.children)b.setAttribute('aria-pressed',String(b===button));render();});filters.append(button);}
    const belongs = item => category==='All' || (category==='Publications' ? ['Publications','Journal articles','General articles'].includes(item.category) : item.category===category || (category==='Teaching' && item.category==='Teaching & learning'));
    function render() {
      const query=input.value.trim();
      if(root.classList.contains('search-page')) {const url=new URL(location.href);query?url.searchParams.set('q',query):url.searchParams.delete('q');history.replaceState(null,'',url);}
      let found;
      if(query){
        found=search(query);
      } else found=data.filter(item=>item.kind==='page' && item.category!=='Search');
      const seen=new Set();found=found.filter(item=>{if(!belongs(item)||seen.has(item.url))return false;seen.add(item.url);return true;});
      results.replaceChildren();
      status.textContent=query ? `${found.length} result${found.length===1?'':'s'} for “${query}”${category!=='All'?' in '+category:''}` : 'Enter a title, author, topic, or year.';
      for(const item of found.slice(0,limit)){
        const a=document.createElement('a');a.href=item.url;a.className='search-result';
        a.innerHTML=`<span class="result-category">${escape(item.category)}</span><h3>${highlight(item.title,query)}</h3><p>${highlight(excerpt(item.text,query),query)}</p>`;
        a.addEventListener('click',()=>{if(dialog.open)dialog.close();});results.append(a);
      }
      if(!found.length){const p=document.createElement('p');p.textContent='No results found. Try a different query or category.';p.className='archive-note';results.append(p);}
      if(found.length>limit){const button=document.createElement('button');button.className='search-more';button.textContent=`Show more (${found.length-limit} remaining)`;button.addEventListener('click',()=>{const previous=limit;limit+=20;render();results.querySelectorAll('a')[previous]?.focus();});results.append(button);}
    }
    input.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(()=>{limit=20;render();},100);});
    root.addEventListener('keydown', e=>{
      if(e.key==='Enter' && document.activeElement===input){clearTimeout(timer);render();}
      const links=[...results.querySelectorAll('a')];const index=links.indexOf(document.activeElement);
      if(e.key==='ArrowDown' && (document.activeElement===input||index>=0)){e.preventDefault();links[Math.min(index+1,links.length-1)]?.focus();}
      if(e.key==='ArrowUp' && index>=0){e.preventDefault();if(index===0)input.focus();else links[index-1].focus();}
      if(e.key==='Enter' && document.activeElement===input){e.preventDefault();links[0]?.click();}
    });
    if(root.classList.contains('search-page'))input.value=new URLSearchParams(location.search).get('q')||'';
    render();
  }
})();
