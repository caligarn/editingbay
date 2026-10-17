#!/usr/bin/env python3
"""Deterministic catalog import/build. No model calls, uploads or network access."""
import argparse, copy, datetime, hashlib, json, re
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
CLIP_KEYS={'id','label','person','topic','category','date','sourceIds','hubEditions','versions','latestVersion','reviewStatus'}
VERSION_KEYS={'id','number','video','thumbnail','duration','ranges','captionQA'}
PRIVATE_PATTERN=re.compile(r'/(?:Users|Volumes|private)/|file://|libfile_|team_[A-Za-z0-9]|prj_[A-Za-z0-9]|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|(?:token|password|secret)\s*[=:]',re.I)

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def require(ok, message):
    if not ok:raise ValueError(message)

def write(path, text):
    path=Path(path)
    if not path.exists() or path.read_text()!=text:
        tmp=path.with_name(path.name+'.tmp');tmp.write_text(text);tmp.replace(path)

def save(path,value):write(path,json.dumps(value,indent=2)+'\n')

def source_ids(value):
    ids=[Path(s.strip()).stem for s in value.split(';')]
    return list(dict.fromkeys(x for x in ids if re.fullmatch(r'(?:[A-Z]{1,8}\d{3,}|A\d+_\d+_C\d+|(?:May-)?IMG_\d+[a-z]?)',x,re.I)))

def recount(catalog):
    for c in catalog['clips']:
        c['versions'].sort(key=lambda v:v['number'],reverse=True)
        v=c['versions'][0];c['latestVersion']=v['id']
        c['reviewStatus']='Media missing' if not v['video'] else 'Caption QA pending' if v['captionQA'] else 'Review draft'
    catalog['snapshotDate']=max(c['date'] for c in catalog['clips'])
    catalog['counts']={'clips':len(catalog['clips']),'latestPlayable':sum(bool(c['versions'][0]['video']) for c in catalog['clips']),
                       'captionQAPending':sum(c['versions'][0]['captionQA'] for c in catalog['clips'])}

def validate(catalog,lock):
    require(set(catalog)=={'schemaVersion','snapshotDate','clips','counts'},'Unexpected catalog fields')
    ids=set();labels=set()
    for c in catalog['clips']:
        require(set(c)==CLIP_KEYS,'Unexpected public clip fields')
        require(c['id'] not in ids and c['label'] not in labels,'Duplicate feedback identity')
        ids.add(c['id']);labels.add(c['label'])
        require(re.fullmatch(r'MC-\d{3,}',c['id']) and re.fullmatch(r'.+ \d{2,}',c['label']),'Invalid feedback identity')
        require(c['versions'],'Clip requires an edition')
        versions=[]
        for v in c['versions']:
            require(set(v)==VERSION_KEYS,'Unexpected public version fields')
            require(type(v['number']) is int and v['number']>0 and v['id']==f"v{v['number']}",'Invalid version')
            require(v['id'] not in versions,'Duplicate version');versions.append(v['id'])
            for field in ('video','thumbnail'):
                value=v[field]
                if value is not None:require(re.fullmatch(r'/media/MC-\d{3,}-v\d+\.(?:mp4|png|jpg|jpeg|webp)',value),'Invalid media identity')
        if c['id'] in lock:
            old=lock[c['id']]
            require(c['label']==old['label'] and set(old['versions']).issubset(versions),'Locked identity renamed or removed')
    require(set(lock).issubset(ids),'Locked clip removed')
    require(not PRIVATE_PATTERN.search(json.dumps(catalog)),'Private-data pattern in public catalog')

def import_batch(catalog,hashes,lock,batch):
    catalog=copy.deepcopy(catalog);hashes=copy.deepcopy(hashes);lock=copy.deepcopy(lock)
    require(batch['schemaVersion']==1,'Unsupported manifest schema')
    datetime.date.fromisoformat(batch['date'])
    by_id={c['id']:c for c in catalog['clips']}
    for item in batch['clips']:
        cid=item['id'];label=item['label']
        if cid in by_id:
            c=by_id[cid];require(c['label']==label,'Stable label cannot change')
            require(batch['date']>=c['date'],'Revision date precedes latest batch')
        else:
            require(item['category'] in ('Interview','Event promo'),'Unsupported category')
            c={'id':cid,'label':label,'person':re.sub(r' \d+$','',label),'topic':item['topic'],'category':item['category'],
               'date':batch['date'],'sourceIds':source_ids(item['source']),'hubEditions':False,'versions':[],
               'latestVersion':'','reviewStatus':'Review draft'}
            by_id[cid]=c;catalog['clips'].append(c)
        for v in sorted(item['versions'],key=lambda x:x['number']):
            number=v['number'];vid=f'v{number}'
            path=Path(v['video_path']);expected=v.get('sha256')
            require(expected is None or re.fullmatch(r'[a-f0-9]{64}',expected),'Invalid SHA-256')
            require(expected or v.get('missingReason'),'Hash or missingReason required')
            evidence=Path(v['evidence_path']);require(evidence.is_file(),'JSON evidence required');json.loads(evidence.read_text())
            require(path.is_absolute() and path.suffix.lower()=='.mp4','Exact MP4 path required')
            present=bool(expected and path.is_file() and path.stat().st_size)
            if present:require(digest(path)==expected,'Wrong export bytes')
            # A missing exact file keeps its known asset identity, but no new upload is possible until it returns.
            video=f'/media/{cid}-{vid}.mp4' if expected else None
            thumb_path=Path(v['thumbnail_path']) if v.get('thumbnail_path') else None
            thumbnail=None;new_hashes={}
            if video:new_hashes[video[7:]]=expected
            if thumb_path and expected and thumb_path.is_file():
                require(thumb_path.is_absolute() and thumb_path.suffix.lower() in ('.png','.jpg','.jpeg','.webp'),'Exact image path required')
                thumbnail=f'/media/{cid}-{vid}{thumb_path.suffix.lower()}'
                new_hashes[thumbnail[7:]]=digest(thumb_path)
            edition={'id':vid,'number':number,'video':video,'thumbnail':thumbnail,'duration':v.get('duration'),
                     'ranges':v.get('ranges',[]),'captionQA':bool(item.get('warnings'))}
            old=next((x for x in c['versions'] if x['id']==vid),None)
            if old:
                require(old==edition,'Edition changed; add a new version')
            else:
                require(number>max((x['number'] for x in c['versions']),default=0),'Version must append')
                c['versions'].append(edition)
            for key,sha in new_hashes.items():
                require(key not in hashes or hashes[key]==sha,'Locked asset hash changed')
                hashes[key]=sha
        c['date']=batch['date']
    recount(catalog);validate(catalog,lock)
    for c in catalog['clips']:lock[c['id']]={'label':c['label'],'versions':[v['id'] for v in c['versions']]}
    return catalog,hashes,lock

def materialize(catalog,hashes,mapping):
    out=copy.deepcopy(catalog)
    for c in out['clips']:
        for v in c['versions']:
            for field in ('video','thumbnail'):
                key=v[field]
                if not key:continue
                key=key[7:];entry=mapping.get(key)
                require(entry is not None,'Upload mapping missing for '+key)
                require(entry['sha256']==hashes.get(key),'Uploaded bytes do not match '+key)
                url=urlsplit(entry['url'])
                require(url.scheme=='https' and url.hostname and url.hostname.endswith('.public.blob.vercel-storage.com')
                        and not url.username and not url.password and not url.query and not url.fragment,'Public Blob URL required')
                v[field]=entry['url']
    require(not PRIVATE_PATTERN.search(json.dumps(out)),'Private-data pattern in release')
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    commands=p.add_subparsers(dest='command',required=True)
    imp=commands.add_parser('import');imp.add_argument('manifest',type=Path)
    build=commands.add_parser('build');build.add_argument('--media-map',required=True,type=Path)
    commands.add_parser('check')
    args=p.parse_args()
    catalog=json.loads((ROOT/'catalog.json').read_text());hashes=json.loads((ROOT/'asset-hashes.json').read_text())
    lock=json.loads((ROOT/'reference-lock.json').read_text());validate(catalog,lock)
    if args.command=='import':
        catalog,hashes,lock=import_batch(catalog,hashes,lock,json.loads(args.manifest.read_text()))
        save(ROOT/'catalog.json',catalog);save(ROOT/'asset-hashes.json',hashes);save(ROOT/'reference-lock.json',lock)
    elif args.command=='build':
        output=materialize(catalog,hashes,json.loads(args.media_map.read_text()))
        dest=ROOT/'dist';dest.mkdir(exist_ok=True)
        for name in ('index.html','app.js','styles.css','robots.txt','vercel.json'):write(dest/name,(ROOT/'site'/name).read_text())
        save(dest/'inventory.json',output)
        require({x.name for x in dest.iterdir()}=={'index.html','app.js','styles.css','robots.txt','vercel.json','inventory.json'},'Unexpected deploy files')
    print(json.dumps({'command':args.command,'clips':len(catalog['clips']),'deployed':False}))

if __name__=='__main__':main()
