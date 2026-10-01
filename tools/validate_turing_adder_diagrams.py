"""Execute transitions extracted from the actual frozen and corrected diagrams."""
import hashlib
import json
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/full'
OUT.mkdir(parents=True,exist_ok=True)
SYMBOL={'TMblank':'0','TMstroke':'1','TMendtape':'#'}
MOVE={'TMright':1,'TMleft':-1,'TMstay':0}
edge_token=re.compile(r'\((?P<root>[A-Za-z0-9_]+)\)\s*(?=edge)|edge(?:\s*\[[^\]]*\])?\s+node(?:\s*\[[^\]]*\])?\s*\{\\TMtrans\{\\(?P<read>TM\w+)\}\{\\(?P<write>TM\w+)\}\{\\(?P<move>TM\w+)\}\}\s*\((?P<dest>[A-Za-z0-9_]+)\)')
def extract(path,index=0):
    raw=path.read_bytes()
    text=raw.decode('utf-8')
    diagram=re.findall(r'\\path(.*?)\\end\{tikzpicture\}',text,re.S)[index]
    diagram=re.sub(r'(?m)%.*$','',diagram)
    transitions={};origin=None;edges=0
    for m in edge_token.finditer(diagram):
        if m['root']:
            origin=m['root'];continue
        assert origin is not None
        key=(origin,SYMBOL[m['read']])
        assert key not in transitions
        transitions[key]=(m['dest'],SYMBOL[m['write']],MOVE[m['move']]);edges+=1
    assert edges==len(re.findall(r'\bedge\b',diagram))
    return transitions,hashlib.sha256(raw).hexdigest()
def run(transitions,n,m,step_bound=None):
    tape=['#']+['1']*n+['0']+['1']*m
    head=1;state='A';steps=0;left_boundary_attempt=False
    while (state,tape[head]) in transitions:
        next_state,written,direction=transitions[(state,tape[head])]
        tape[head]=written
        if head==0 and direction<0:left_boundary_attempt=True
        head=max(0,head+direction)
        if head==len(tape):tape.append('0')
        state=next_state;steps+=1
        assert steps<=(step_bound or 20*(n+m+2)),'bounded specified program did not halt'
    output=''.join(tape[1:]).rstrip('0')
    return {'output':output,'state':state,'head':head,'steps':steps,
            'marker_preserved':tape[0]=='#','left_boundary_attempt':left_boundary_attempt}
rows=[]
for unit,name in [('OLP-0258','unary-numbers.tex'),('OLP-0260','disciplined-machines.tex')]:
    relative=Path('content/turing-machines/machines-computations')/name
    source,source_sha=extract(ROOT/'upstream'/relative)
    target,target_sha=extract(ROOT/'mr'/relative)
    assert set(source)==set(target)
    assert [(k,source[k],target[k]) for k in source if source[k]!=target[k]]==[(('A','1'),('B','1',1),('A','1',1))]
    source_failures=0;checks=0
    for n in range(41):
        for m in range(41):
            expected='1'*(n+m)
            old=run(source,n,m);new=run(target,n,m)
            source_failures+=old['output']!=expected
            assert new['output']==expected,(unit,n,m,new)
            assert new['marker_preserved'] and not new['left_boundary_attempt']
            if unit=='OLP-0260':assert new['state']=='H' and new['head']==1
            checks+=1
    rows.append({'unit_id':unit,'source_sha256':source_sha,'target_sha256':target_sha,
                 'tested_input_pairs':checks,'frozen_source_wrong_sum_cases':source_failures,
                 'corrected_example_3_2':run(target,3,2),'frozen_example_3_2':run(source,3,2),
                 'corrected_zero_zero':run(target,0,0)})
combined=[]
for index in range(3):
    relative=Path('content/turing-machines/machines-computations/combining-machines.tex')
    source,source_sha=extract(ROOT/'upstream'/relative,index)
    target,target_sha=extract(ROOT/'mr'/relative,index)
    assert set(source)==set(target)
    assert [(k,source[k],target[k]) for k in source if source[k]!=target[k]]==[(('A','1'),('B','1',1),('A','1',1))]
    failures=0;checks=0
    for n in range(13):
        for m in range(13):
            old=run(source,n,m,100*(n+m+2)**2)
            new=run(target,n,m,100*(n+m+2)**2)
            if index<2:
                assert new['output']=='1'*(n+m)
                failures+=old['output']!='1'*(n+m)
                if index==1:assert new['state']=='E' and new['head']==1
            else:
                assert re.fullmatch(r'0*1*',new['output'])
                assert new['output'].count('1')==2*(n+m)
                failures+=not re.fullmatch(r'0*1*',old['output']) or old['output'].count('1')!=2*(n+m)
            assert new['marker_preserved'] and not new['left_boundary_attempt']
            checks+=1
    combined.append({'unit_id':'OLP-0261','diagram_index':index,'source_sha256':source_sha,'target_sha256':target_sha,
                     'tested_input_pairs':checks,'frozen_source_specification_failures':failures,
                     'corrected_example_3_2':run(target,3,2,10000)})
report={'status':'passed','actual_tikz_transitions_extracted':True,'input_bound_each':40,
        'general_argument':'q0 scans n strokes, fills the unique separator, q1 scans m strokes and the filled separator, and q2 erases exactly the final stroke. The disciplined tail preserves the tape while returning to square 1 and state h.',
        'limitations':'Finite executions supplement the transition invariant; this is not a proof of arbitrary Turing programs or a full diagram/rendering audit.',
        'results':rows,'combined_graph_results':combined,
        'combined_input_bound_each':12,'combined_limitations':'Final graph leaves leading blanks; verified the claimed doubled contiguous stroke block, not canonical numeric output.'}
(OUT/'TURING_ADDER_DIAGRAM_CHECK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
