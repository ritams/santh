"""Check generated pages, local links, anchors, and search coverage."""
from pathlib import Path
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup
import json
root=Path(__file__).resolve().parent.parent
pages={p.name:BeautifulSoup(p.read_text(),'html.parser') for p in root.glob('*.html')}
errors=[]
def check_link(origin,href):
    u=urlparse(href)
    if u.scheme or u.netloc:return
    target=unquote(u.path) or origin
    if not (root/target).exists():errors.append(f'{origin}: missing {href}')
    elif u.fragment and target in pages and not pages[target].find(id=unquote(u.fragment)):errors.append(f'{origin}: missing anchor {href}')
for name,s in pages.items():
    ids=[x['id'] for x in s.select('[id]')]
    if len(ids)!=len(set(ids)):errors.append(f'{name}: duplicate IDs')
    assert len(s.select('main'))==1 and len(s.select('h1'))==1,name
    for a in s.select('a[href],script[src],link[href],img[src]'):check_link(name,a.get('href',a.get('src')))
index=json.loads((root/'search-index.js').read_text().split(' = ',1)[1].rstrip(';\n'))
for item in index:check_link('search.html',item['url'])
for name in pages:assert any(i['url']==name for i in index),name
assert sum(i['category']=='People' and '#' in i['url'] for i in index)==39
assert len(pages['pubs.html'].select('article'))==114
assert 'Saranya Ray' in pages['group.html'].get_text()
assert len(index)>800
if errors:raise SystemExit('\n'.join(errors))
print(f'PASS: {len(pages)} pages, {len(index)} search entries, all local links/anchors, 114 publications, 39 people.')
# Topic assignments and research references share the same maintained catalog.
topics=json.loads((root/'content/research-topics.json').read_text())
research_papers={a['id'] for a in pages['pubs.html'].select('#secjournals [data-publication]')}
assert set().union(*(set(t['papers']) for t in topics.values())) == research_papers
for topic in topics.values():
    assert len(topic['selected']) == 3
    assert set(topic['selected']) <= set(topic['papers']) <= research_papers
assert len(pages['research.html'].select('.related-papers li')) == 21
assert pages['pubs.html'].select_one('#publication-year')
assert all(s.select_one('.scroll-top') for s in pages.values())
print('PASS: topic coverage for all research publications and 21 selected-paper references.')
