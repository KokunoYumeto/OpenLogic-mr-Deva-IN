import subprocess,json,base64,hashlib
from pathlib import Path
P=Path(__file__).resolve().parents[1]
dest=P/'fonts';dest.mkdir(exist_ok=True)
records=[]
for name,blob in [('NotoSerifDevanagari.ttf','3d90da279fe70b5017d9b51f58772f0c9ea4146e'),('OFL.txt','cd2cc5c94b4151933eba6ee508e3975274d6fa07')]:
    p=dest/name
    if not p.exists():
        raw=subprocess.run(['gh','api','repos/google/fonts/git/blobs/'+blob],capture_output=True,check=True).stdout
        obj=json.loads(raw);assert obj['sha']==blob
        data=base64.b64decode(obj['content']);p.write_bytes(data)
    data=p.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==blob
    records.append({'file':str(p.relative_to(P)),'source_repo':'https://github.com/google/fonts','source_git_blob':blob,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(dest/'MANIFEST.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
print(json.dumps(records,indent=2))
