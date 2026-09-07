"""Build static pages and their search index from the archived IISER content."""
from pathlib import Path
from bs4 import BeautifulSoup, Comment
from urllib.parse import urljoin, urlparse, unquote
import html, json, re, hashlib

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'content/source'
BASE = 'https://sites.iiserpune.ac.in/~santh/'
INDEX = []
PAGES = {}
TOPICS = json.loads((ROOT/'content/research-topics.json').read_text())
NAV = [('index.html','Home'),('research.html','Research'),('pubs.html','Publications'),('courses.html','Teaching'),('group.html','Group'),('forpdf.html','Opportunities'),('contact.html','Contact')]
COURSES = {p.relative_to(SOURCE).as_posix(): 'course-'+ '-'.join(p.relative_to(SOURCE).with_suffix('').parts[1:]).lower()+'.html' for p in SOURCE.glob('course/**/*.html')}
MAPPING = {**{n:n for n,_ in NAV},'qml_tutorial.html':'qml_tutorial.html', **COURSES}

def soup(name, parser='html.parser'):
    return BeautifulSoup((SOURCE/name).read_text(),parser)
def txt(t):
    return re.sub(r'\s+',' ',t.get_text(' ',strip=True)).strip()
def esc(s): return html.escape(str(s),quote=True)
def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')[:110]
def link(url, source):
    url=url.replace('http://http://','https://')
    absolute=urljoin(BASE+source,url)
    parsed=urlparse(absolute)
    if parsed.hostname in ('sites.iiserpune.ac.in','www.iiserpune.ac.in') and '/~santh/' in parsed.path:
        path=unquote(parsed.path.split('/~santh/')[1]) or 'index.html'
        if path in MAPPING: return MAPPING[path]+('#'+parsed.fragment if parsed.fragment else '')
        return BASE+path+('?' + parsed.query if parsed.query else '')+('#'+parsed.fragment if parsed.fragment else '')
    return absolute

def clean(fragment,source):
    s=BeautifulSoup(str(fragment),'html5lib')
    for el in s.find_all(string=lambda t:isinstance(t,Comment)): el.extract()
    for el in s.select('script,style,noscript,iframe,img,button,link,meta,title,form,input'):
        if el.name=='iframe' and 'youtube.com/embed/' in el.get('src',''):
            a=s.new_tag('a',href='https://www.youtube.com/watch?v='+el['src'].split('/embed/')[1].split('?')[0]);a.string='Watch lecture';el.replace_with(a)
        else: el.decompose()
    for el in s.body.find_all(True):
        old=dict(el.attrs);el.attrs={}
        if el.name=='a':
            href=old.get('href','')
            if href and not href.startswith(('javascript:','#')): el['href']=link(href,source)
            elif href.startswith('#'):el['href']=href
        if el.name in ('td','th'):
            for attr in ('colspan','rowspan'):
                if attr in old:el[attr]=old[attr]
        if el.name in ('font','big','small','center'): el.name='span'
    for a in s.body.select('a'):
        for text in a.find_all(string=True):
            text.replace_with(str(text).replace('↗', '').replace('↖', '').replace('→', '').replace('←', ''))
    return s.body.decode_contents().strip()

def record(title,text,url,category):
    INDEX.append(dict(title=title,text=text,url=url,category=category))

def entry(title,body,page,category,identifier=None,year=''):
    identifier=identifier or slug(title)
    record(title,txt(BeautifulSoup(body,'html.parser')),page+'#'+identifier,category)
    return f'<article class="entry" id="{identifier}"><div class="entry-marker">{esc(year or category)}</div><div><h3>{esc(title)}</h3><div class="prose">{body}</div></div></article>'

def jumps(items):
    return '<nav class="jump-links" aria-label="On this page">'+''.join(f'<a href="#{i}">{esc(t)}</a>' for i,t in items)+'</nav>'

def page(name,title,subtitle,body,category=None):
    category=category or {'research.html':'Research','group.html':'People','courses.html':'Teaching','contact.html':'Contact'}.get(name,title)
    record(title,subtitle,name,category)
    INDEX[-1]['kind']='page'
    PAGES[name]=(title,subtitle,body,category)

def section(title,body,id=None):
    return f'<section class="content-section" id="{id or slug(title)}"><h2>{esc(title)}</h2>{body}</section>'

# Full publication archive, including the metadata outside legacy list items.
ps=soup('pubs.html'); pubgroups={'General articles':[], 'Journal articles':[]}; cat='General articles'
for el in ps.find_all(['div','ul']):
    if el.get('id')=='secjournals':cat='Journal articles'
    if el.name!='ul' or not el.find('li'):continue
    first=el.find('li'); title_node=first.find(['i','a'])
    title=txt(title_node) if title_node else txt(first).split('\n')[0]
    # Some titles are plain text followed by a line break.
    if not title_node:
        title=txt(BeautifulSoup(str(first).split('<br')[0]+'</li>','html.parser'))
    body=clean(el,'pubs.html')
    b=BeautifulSoup(body,'html.parser')
    if title_node:
        first_node=b.find(['i','a']); first_node.decompose()
    else:
        li=b.find('li')
        for n in list(li.contents):
            if getattr(n,'name',None)=='br':n.extract();break
            n.extract()
    for li in b.find_all(['ul','li']):li.unwrap()
    title_link=title_node.find('a') if title_node and title_node.name!='a' else title_node
    href=link(title_link.get('href'),'pubs.html') if title_link and title_link.get('href') else None
    years=re.findall(r'\b(?:19|20)\d{2}\b',txt(el));year=years[-1] if years else ''
    details=b.decode_contents().strip()
    if href:details+=f'<p><a class="resource-link" href="{esc(href)}">Read article</a></p>'
    pubgroups[cat].append((title,details,year))
# A new preprint appears on the source homepage before the archive.
home=soup('index.html')
for ul in home.find_all('li'):
    if 'Localization with Hopping Disorder' in txt(ul):
        a=ul.find('a');t=txt(a)
        if not any(t==p[0] for p in pubgroups['Journal articles']):
            details=BeautifulSoup(clean(ul,'index.html'),'html.parser')
            details.find('a').decompose()
            for tag in details.find_all(['ul','li']):tag.unwrap()
            details=str(details)+f'<p><a class="resource-link" href="{esc(a["href"])}">Read article</a></p>'
            pubgroups['Journal articles'].insert(0,(t,details,'2026'))
papers_by_id = {slug(t):(t,b,y) for t,b,y in pubgroups['Journal articles']}
for topic in TOPICS.values():
    assert all(id in papers_by_id for id in topic['papers']), topic['label']
    assert set(topic['selected']) <= set(topic['papers'])
years=sorted({y for items in pubgroups.values() for _,_,y in items if y},reverse=True)
publication_body = '<div class="publication-filters" hidden><div class="publication-filter-row"><label>Article type<select id="publication-type"><option value="all">All articles</option><option value="journal">Research publications</option><option value="general">General articles</option></select></label><label>Year<select id="publication-year"><option value="all">All years</option>'+''.join(f'<option>{y}</option>' for y in years)+'</select></label><label class="publication-query-label">Search articles<input id="publication-query" type="search" placeholder="Title, author, or keyword" autocomplete="off"></label><button type="button" id="publication-reset">Clear filters</button></div><div class="topic-filters" role="group" aria-label="Research topic"><button type="button" data-topic="all" aria-pressed="true">All topics</button>'+''.join(f'<button type="button" data-topic="{id}" aria-pressed="false">{esc(topic["label"])}</button>' for id,topic in TOPICS.items())+'</div><p id="publication-status" class="sr-only" role="status" aria-live="polite"></p><p id="publication-empty" hidden>No articles match these filters. Try another topic, year, or search term.</p></div>'
publication_body+=jumps([('secjournals','Journal articles'),('secgeneral','General articles')])
for cat,id,kind in [('Journal articles','secjournals','journal'),('General articles','secgeneral','general')]:
    articles=[]
    for t,b,y in pubgroups[cat]:
        tags=[key for key,topic in TOPICS.items() if slug(t) in topic['papers']] if kind=='journal' else []
        tag_html='<div class="publication-topics">'+''.join(f'<a href="pubs.html?topic={key}">{esc(TOPICS[key]["label"])}</a>' for key in tags)+'</div>' if tags else ''
        article=entry(t,b+tag_html,'pubs.html',cat,year=y)
        article=article.replace('<article ',f'<article data-publication data-kind="{kind}" data-year="{y}" data-topics="{" ".join(tags)}" ')
        articles.append(article)
    publication_body+=section(cat,''.join(articles),id)
page('pubs.html','Publications','Research publications, preprints, and general articles.',publication_body)

# Research text and all original reference links.
rs=soup('research.html'); areas=[]
ids=['quantum-chaos','localisation','random-matrices','quantum-ml','networks','extreme-events','complex-systems']
for h,id in zip(rs.find_all('h4'),ids):
    title=txt(h).rstrip(' :');parent=h.parent;h.extract()
    body=clean(parent,'research.html')
    topic=TOPICS[id]
    related='<aside class="related-papers" aria-label="Selected publications"><h4>Selected publications</h4><ul>'
    for paper_id in topic['selected']:
        paper,_,year=papers_by_id[paper_id]
        related+=f'<li><a href="pubs.html#{paper_id}">{esc(paper)}</a> <span class="paper-year">({year})</span></li>'
    related+=f'</ul><a class="resource-link" href="pubs.html?topic={id}">All publications in this area</a></aside>'
    areas.append((id,title,body+related))
page('research.html','Research','Quantum physics, nonlinear dynamics, and complex systems.',jumps([(i,t) for i,t,_ in areas])+''.join(entry(t,b,'research.html','Research',i, f'{n:02}') for n,(i,t,b) in enumerate(areas,1)))

# Group roster: preserve source categories and dates without guessing current appointments.
gs=soup('group.html'); groups={};category=None
for el in gs.find_all(['div','ul']):
    if el.name=='div' and 'w3-panel' in el.get('class',[]):category=txt(el);groups[category]=[]
    elif el.name=='ul' and category and el.find('li'):
        if len(el.find_all('li',recursive=False))>1:
            for li in el.find_all('li',recursive=False):groups[category].append((txt(li),''))
        else:
            li=el.find('li'); title=txt(li).rstrip(':');li.extract()
            groups[category].append((title,clean(el,'group.html').replace('<ul>','').replace('</ul>','')))
page('group.html','Research group','Ph.D. students, postdoctoral fellows, thesis students, and research interns. Dates and affiliations follow the IISER group directory.',jumps([(slug(g),g) for g in groups])+''.join(section(g,''.join(entry(t,b,'group.html','People') for t,b in members)) for g,members in groups.items()))

# Course pages retain full syllabi, timetables, assignments, and resource links.
for source,dest in COURSES.items():
    cs=soup(source,'html5lib');title=txt(cs.title) if cs.title else source
    title = {
        'course/QML/qml.html':'Quantum Machine Learning · 2023',
        'course/ph3214-qm2/ph3214.html':'Quantum Mechanics II · 2026',
        'course/ph3124/ph3124.html':'Quantum Mechanics I · 2024',
        'course/phy411/phy411_qm.html':'Quantum Mechanics II · 2010',
        'course/phy310/phy310.html':'Mathematical Methods · 2009',
        'course/qmr/qmr.html':'Quantum Mechanics and Relativity · 2009',
    }.get(source,title)
    if title.lower() in ('','untitled'):title=source.split('/')[-2]
    body=clean(cs.body,source)
    # Give each resource a stable search destination, including assignment text and tables.
    bs=BeautifulSoup(body,'html.parser')
    for n,a in enumerate(bs.select('a[href]')):
        a['id']=f'resource-{n+1}'
        label=txt(a)
        if label:record(label,title+' '+txt(a.parent),dest+'#'+a['id'],'Teaching')
    for n,block in enumerate(bs.find_all(['p','tr','li'])):
        text=txt(block)
        if len(text)>35:
            block['id']=f'content-{n+1}';record(title,text,dest+'#'+block['id'],'Teaching')
    # Plain text between <br>s also belongs in the full-text index.
    text=txt(bs)
    for n,start in enumerate(range(0,len(text),650)):
        record(title,text[start:start+800],dest,'Teaching')
    page(dest,title,'Course archive · Syllabus, reading, assignments, and lecture resources.',f'<a class="back-home" href="courses.html">All teaching</a><div class="prose course-document">{bs}</div>','Teaching')

cs=soup('courses.html','html5lib');content=cs.select_one('.w3-content')
# Missing source pages are documented, without sending visitors to known 404s.
missing=['lec_notes.html','course/phy342/phy342_nld.html','course/phy361/phy361.html','course/phy313/phy313.html']
for a in content.select('a[href]'):
    if any(a['href'].endswith(m) for m in missing):
        a.name='span';a.attrs={};a.append(' — original page unavailable')
# Turn legacy heading labels into consistent editorial headings.
for p in content.select('p.w3-text-red'):p.name='h2'
body=BeautifulSoup(clean(content,'courses.html'),'html.parser')
for n,li in enumerate(body.find_all('li')):
    li['id']=f'teaching-{n+1}'
    record(txt(li)[:150],txt(li),'courses.html#'+li['id'],'Teaching')
page('courses.html','Teaching','Courses, lecture recordings, and teaching resources at IISER Pune.',f'<div class="prose teaching-document">{body}</div>')

qs=soup('qml_tutorial.html','html5lib');h=qs.find('h2');container=h.parent
body=BeautifulSoup(clean(container,'qml_tutorial.html'),'html.parser')
for n,a in enumerate(body.select('a[href]')):
    a['id']=f'tutorial-{n+1}';record(txt(a),txt(a.parent),'qml_tutorial.html#'+a['id'],'Teaching')
page('qml_tutorial.html','Quantum machine learning','CODS-2025 · Talks, notebooks, and further reading with M. S. Santhanam and Nisarg Vyas.',f'<a class="back-home" href="courses.html">All teaching</a><div class="prose">{body}</div>','Teaching')

page('forpdf.html','Postdoctoral opportunities','Postdoctoral research in quantum physics, nonlinear dynamics, and complex systems.',section('Research enquiries','<div class="prose"><p>Prospective postdoctoral applicants may contact M. S. Santhanam by email. Please refer to the <a href="research.html">research areas</a> and describe your research interests in your enquiry.</p><p><a class="resource-link" href="mailto:santh@iiserpune.ac.in">santh@iiserpune.ac.in</a></p><p>The source lists the National Post-Doctoral Fellowship (NPDF) scheme of ANRF as one possible funding route. Other funding sources may also be considered.</p></div>')+section('Previous calls','<p class="archive-note">These are archived announcements; their deadlines have passed.</p>'+entry('NPDF / ANRF · 2025','<p>Application deadline listed on the source: 15 June 2025.</p>','forpdf.html','Opportunities',year='Closed')+entry('Quantum computing, machine learning & chaos · 2022','<p>January 2022: one to two postdoctoral positions. Previous experience in these or closely related areas was preferred. The source marks this call closed.</p>','forpdf.html','Opportunities',year='Closed')+entry('IISER-funded postdoctoral positions · 2021','<p>Advertisement 30/2021. Application deadline: 15 June 2021.</p>','forpdf.html','Opportunities',year='Closed')),'Opportunities')

page('contact.html','Contact','For research enquiries, collaboration, and prospective postdoctoral work.', '<div class="contact-inner"><div class="prose"><h2>M. S. Santhanam</h2><p>Physics Department<br>Indian Institute of Science Education and Research Pune</p><p>Dr. Homi Bhabha Road<br>Pune 411 008, India</p></div><div class="contact-info"><div class="contact-row"><span class="contact-label">Email</span><a href="mailto:santh@iiserpune.ac.in">santh@iiserpune.ac.in</a></div><div class="contact-row"><span class="contact-label">Phone</span><a href="tel:+912025908088">+91 20 25908088</a></div><div class="contact-row"><span class="contact-label">Institution</span><a href="https://www.iiserpune.ac.in/">IISER Pune</a></div></div></div>')
record('Contact M. S. Santhanam','santh@iiserpune.ac.in +91 20 25908088 Physics Department Dr. Homi Bhabha Road Pune 411008 India','contact.html','Contact')
projects=[('Election Insights','Statistical patterns of competition and participation in democratic elections.','https://electioninsights.in/'),('Infectious Diseases Hazard Map','Infectious disease risk assessment using mobility and transportation networks in India.','https://sites.iiserpune.ac.in/~hazardmap/'),('Quantum ML tutorial','Lecture slides and computational notebooks on quantum machine learning.','qml_tutorial.html')]
project_html=''.join(f'<a class="project-card" href="{u}"><h3>{t}</h3><p>{d}</p><span class="project-link">View project</span></a>' for t,d,u in projects)
for t,d,u in projects:record(t,d,u,'Projects')
recent=pubgroups['Journal articles'][:4]
recent_html=''.join(f'<a class="recent-item" href="pubs.html#{slug(t)}"><span class="recent-meta">{y} · Research</span><span class="recent-title">{esc(t)}</span></a>' for t,_,y in recent)
body=f'''<section class="hero"><div class="container"><div class="hero-grid"><div class="hero-main"><span class="hero-label">Theoretical Physics · IISER Pune</span><h1>M. S. Santhanam</h1><p class="hero-text">Professor of Physics<br>Indian Institute of Science Education and Research, Pune</p><p class="hero-description">Research interests: quantum chaos, nonlinear dynamics, quantum computation, statistical physics, complex networks, and data science.</p><div class="hero-links"><a href="research.html" class="text-link">Research</a><a href="contact.html" class="text-link">Contact</a></div></div><aside class="hero-aside"><h4>Recent publications</h4><div class="recent-list">{recent_html}</div><a class="learn-more" href="pubs.html">All publications</a></aside></div></div></section>
<section class="home-explore"><div class="container"><div class="project-cards"><a class="project-card" href="research.html"><h3>Research</h3><p>Theoretical and computational studies of quantum and complex systems.</p><span class="project-link">Research areas</span></a><a class="project-card" href="courses.html"><h3>Teaching</h3><p>Courses, lecture recordings, assignments, and quantum computing notebooks.</p><span class="project-link">Courses & resources</span></a><a class="project-card" href="group.html"><h3>Research group</h3><p>Doctoral students, postdoctoral fellows, thesis students, and research interns.</p><span class="project-link">Research group</span></a></div></div></section>
<section class="projects"><div class="container"><div class="section-intro"><h2>Projects & resources</h2></div><div class="project-cards">{project_html}</div></div></section>'''
page('index.html','M. S. Santhanam','Theoretical physicist at IISER Pune. Quantum chaos, complex networks, quantum computing, and statistical physics.',body,'Home')
page('search.html','Search','Search publications, research topics, group members, and teaching resources.', '<div class="search-page"><label class="sr-only" for="page-query">Search the whole site</label><input id="page-query" type="search" placeholder="Title, author, topic, or course" autocomplete="off"><div class="search-filters" aria-label="Filter search results"></div><p class="search-status" role="status" aria-live="polite"></p><div class="search-results"></div></div>','Search')

for name,(title,subtitle,body,category) in PAGES.items():
    nav=''.join(f'<a href="{n}"'+(' aria-current="page"' if n==name or (n=='courses.html' and (name in COURSES.values() or name=='qml_tutorial.html')) else '')+f'>{t}</a>' for n,t in NAV)
    source=next((s for s,d in COURSES.items() if d==name), name)
    source_note=f'<a href="{BASE+source}">IISER source</a>' if (SOURCE/source).exists() else ''
    main=body if name=='index.html' else f'<div class="container page-content"><header class="page-intro"><span class="section-tag">{esc(category)} / M. S. Santhanam</span><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></header>{body}</div>'
    document=f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)}{' | M. S. Santhanam' if name!='index.html' else ''}</title><meta name="description" content="{esc(subtitle)}"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet"><link rel="stylesheet" href="styles.css"><script defer src="vendor/fuse.min.js"></script><script defer src="search-index.js"></script><script defer src="search-engine.js"></script><script defer src="script.js"></script></head>
<body><noscript><style>.header{{position:static}}.header .container{{flex-wrap:wrap}}.nav{{position:static;visibility:visible;opacity:1;pointer-events:auto;height:auto;padding:1rem 0;flex-wrap:wrap}}.menu-toggle{{display:none}}.page-content{{padding-top:3rem}}</style><p class="archive-note">Search needs JavaScript. You can browse all pages using the navigation links.</p></noscript><a class="skip-link" href="#main">Skip to content</a><header class="header"><div class="container"><a href="index.html" class="logo">Santhanam<span class="logo-dot">.</span></a><nav id="site-nav" class="nav" aria-label="Main navigation">{nav}</nav><div class="header-actions"><a class="search-trigger" href="search.html" aria-label="Search the whole site"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/></svg><span>Search</span><kbd>⌘ K</kbd></a><button class="menu-toggle" aria-label="Open navigation" aria-controls="site-nav" aria-expanded="false"><span></span><span></span><span></span></button></div></div></header><main id="main" tabindex="-1">{main}</main><footer class="footer"><div class="container"><div><span>M. S. Santhanam · IISER Pune</span><div class="footer-links">{source_note}<a href="search.html">Search the site</a><a href="forpdf.html">Postdoctoral opportunities</a></div></div><span class="footer-credit">—web // imagined by <strong><a href="https://ritampal.com">ritam</a></strong></span></div></footer><button class="scroll-top" type="button" aria-label="Scroll to top" hidden>Top</button>
<dialog class="search-dialog" aria-labelledby="search-title"><div class="search-dialog-top"><h2 id="search-title">Search the site</h2><button class="search-close" aria-label="Close search">Esc <span aria-hidden="true">×</span></button></div><label class="sr-only" for="dialog-query">Search the whole site</label><input id="dialog-query" type="search" placeholder="Title, author, topic, or course" autocomplete="off"><div class="search-filters" aria-label="Filter search results"></div><p class="search-status" role="status" aria-live="polite"></p><div class="search-results"></div><div class="search-help">↑ ↓ navigate <span>Enter to open · Esc to close</span></div></dialog></body></html>'''
    for asset in ('styles.css', 'script.js', 'search-engine.js', 'search-index.js'):
        asset_bytes=json.dumps(INDEX,ensure_ascii=False).encode() if asset=='search-index.js' else (ROOT/asset).read_bytes()
        version = hashlib.sha256(asset_bytes).hexdigest()[:10]
        document = document.replace(f'"{asset}"', f'"{asset}?v={version}"')
    (ROOT/name).write_text('\n'.join(line.rstrip() for line in document.splitlines())+'\n')
(ROOT/'search-index.js').write_text('window.SEARCH_INDEX = '+json.dumps(INDEX,ensure_ascii=False).replace('</','<\\/')+';\n')
print(f'Built {len(PAGES)} pages with {len(INDEX)} searchable entries.')
print('Publications:',{k:len(v) for k,v in pubgroups.items()}, 'People:',sum(map(len,groups.values())))
