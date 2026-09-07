/* Shared by the browser and the search regression checks. */
(function(root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('./vendor/fuse.min.js'));
  else root.createSiteSearch = factory(root.Fuse);
})(typeof window !== 'undefined' ? window : this, function(Fuse) {
  const normalize = text => text.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  function distance(a,b) {
    const rows=Array.from({length:a.length+1},()=>Array(b.length+1).fill(0));
    for(let i=0;i<=a.length;i++)rows[i][0]=i;
    for(let j=0;j<=b.length;j++)rows[0][j]=j;
    for(let i=1;i<=a.length;i++)for(let j=1;j<=b.length;j++){
      rows[i][j]=Math.min(rows[i-1][j]+1,rows[i][j-1]+1,rows[i-1][j-1]+(a[i-1]===b[j-1]?0:1));
      if(i>1&&j>1&&a[i-1]===b[j-2]&&a[i-2]===b[j-1])rows[i][j]=Math.min(rows[i][j],rows[i-2][j-2]+1);
    }
    return rows[a.length][b.length];
  }
  return function(data) {
    const vocabulary = new Map();
    for(const item of data)for(const word of normalize(item.title+' '+item.text).match(/[a-z0-9]+/g)||[])vocabulary.set(word,(vocabulary.get(word)||0)+1);
    const fuse=new Fuse(data,{keys:[{name:'title',weight:3},{name:'text',weight:1},{name:'category',weight:.5}],threshold:.18,ignoreLocation:true,includeScore:true,minMatchCharLength:2});
    function correct(term) {
      if(term.length<4||vocabulary.has(term)||/^\d+$/.test(term))return term;
      let best=term,min=term.length>=8?2:1,frequency=0;
      for(const [word,count] of vocabulary){
        if(Math.abs(word.length-term.length)>min)continue;
        const d=distance(term,word);
        if(d<min||(d===min&&count>frequency)){best=word;min=d;frequency=count;}
      }
      return best;
    }
    return function(query){
      const terms=(normalize(query).match(/[a-z0-9]+/g)||[]).slice(0,12).map(correct);
      if(!terms.length)return [];
      const maps=terms.map(term=>new Map(fuse.search(term).map(r=>[r.refIndex,r])));
      return [...maps[0]].filter(([id])=>maps.every(m=>m.has(id)))
        .map(([id,r])=>({...r,score:maps.reduce((sum,m)=>sum+(m.get(id).score||0),0)/maps.length}))
        .sort((a,b)=>a.score-b.score).map(r=>r.item);
    };
  };
});
