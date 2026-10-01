"""Integrate actually recorded corrective decisions into the standard review bundle."""
import hashlib
import json
import re

def derive(root, edition, reader_bindings, locator):
    path=root/'provenance/sol6-reaudit/CORRECTIVE_REPAIRS.jsonl'
    if not path.is_file():return [],[],[],[],{'corrective_decisions':0,'corrective_occurrences':0}
    raw=path.read_bytes()
    evidence={'path_or_uri':'provenance/sol6-reaudit/CORRECTIVE_REPAIRS.jsonl',
              'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    canonical,legacy,occurrences,markdown=[],[],[],[]
    derived_rendering_descriptions=[]
    for row in (json.loads(s) for s in raw.decode('utf-8').splitlines() if s.strip()):
        uid=row['unit_id'];rid=row['id'];reason=row['rationale_mr']
        term=row.get('source_term_or_construction',row.get('source_quote',rid))
        chosen=row.get('chosen_marathi')
        if not chosen:
            assert row.get('title_mr') and row.get('affected_segments'), rid
            chosen=(row['title_mr']+' — '+', '.join(row['affected_segments'])+
                    ' मधील दुरुस्त मराठी रूप; प्रत्येक संदर्भातील सद्य अचूक उतारा खाली दिला आहे.')
            derived_rendering_descriptions.append(rid)
        question=row.get('please_double_check_question_mr') or row.get('review_question_mr') or (
            'मूळ गणिती अर्थ, संख्यापकांची व्याप्ती आणि मराठी शब्दरचना या दुरुस्तीत अचूक जुळतात का?')
        paths=[row['source_path'],row['target_path']]
        assert paths[0].startswith('upstream/') and paths[1].startswith('mr/')
        assert hashlib.sha256((root/paths[0]).read_bytes()).hexdigest()==row['source_sha256']
        assert hashlib.sha256((root/paths[1]).read_bytes()).hexdigest()==row['current_target_sha256']
        spans=[]
        for file in paths:
            text=(root/file).read_bytes().decode('utf-8');position=0;blocks=[]
            for block in re.split(r'\n\s*\n',text.strip()):
                start=text.find(block,position);assert start>=0
                end=start+len(block);position=end
                blocks.append((text.count('\n',0,start)+1,text.count('\n',0,end)+1))
            spans.append(blocks)
        recs=[];ids=[]
        for index in row['affected_block_indices']:
            sid=f'{uid}-B{index:03d}';oid=f'{rid}-{sid}';ids.append(oid)
            source=locator(paths[0],uid,*spans[0][index-1],term,reason,'प्रत्यक्ष तपासलेला बदलाचा मूळ संदर्भखंड')
            target=locator(paths[1],uid,*spans[1][index-1],chosen,reason,'प्रत्यक्ष दुरुस्त केलेला संदर्भखंड; पूर्ण एककाचा पुनरावलोकन दावा नाही')
            binding=reader_bindings[uid]
            recs.append({'occurrence_id':oid,'unit_id':uid,'semantic_unit_id':sid,'source':source,'target':target,
                         'reader_locator':binding,'evidence_refs':[evidence]})
            occurrences.append({'schema':'openlogic-expert-review-occurrence/1','occurrence_id':oid,'decision_id':rid,
                'record_kind':'corrective_review','unit_id':uid,'aligned_block':f'B{index:03d}',
                'source_path':paths[0],'source_lines':f'{spans[0][index-1][0]}-{spans[0][index-1][1]}',
                'target_path':paths[1],'target_lines':f'{spans[1][index-1][0]}-{spans[1][index-1][1]}',
                'chosen_rendering':chosen,'rationale':reason,'please_double_check_question':question,
                'choice_locator_precision':'प्रत्यक्ष दुरुस्त केलेला संदर्भखंड','script':'Deva','locale':'mr-IN',
                'reader_pdf_sha256':binding['artifact_sha256'],'reader_pdf_pages':[binding['assembled_pdf_page']],
                'reader_page_label':binding['printed_page'],'page_locator_precision':binding['provenance']})
        canonical.append({'decision_id':rid,'record_kind':row.get('record_kind','syntax'),'recording_mode':'derived' if rid in derived_rendering_descriptions else 'contemporaneous',
            'edition':edition,'source_term_or_construction':term,
            'intended_sense':reason,'chosen_rendering':chosen,'rationale':reason,
            'authorities_checked':[{'authority_id':'OpenLogic-frozen-source','citation':'Open Logic Project, '+paths[0],
                'status':'checked_context_only','passage_id':r['semantic_unit_id'],
                'locator':f"{paths[0]}:{r['source']['line_span']['start']}-{r['source']['line_span']['end']}",
                'source_sha256':row['source_sha256'],
                'passage_sha256':hashlib.sha256(r['source']['excerpt'].encode('utf-8')).hexdigest(),
                'note':'मूळ इंग्रजी गणित व बदलाचा संदर्भखंड प्रत्यक्ष पाहिला. Passage hash हा exact UTF-8 excerpt चा आहे. मराठी canon च्या पुनर्वाचनाच्या भूमिका स्वतंत्र repair नोंदीत आहेत; नेमक्या पूर्ण शब्दरचनेची तज्ज्ञ-साक्ष असल्याचा दावा नाही.'} for r in recs],
            'alternatives':[],'confidence':'high','confidence_reason':'नेमकी source/target तुलना आणि नोंदवलेल्या निवडीचा तर्क उपलब्ध; स्वतंत्र तज्ज्ञ स्वीकृतीचा दावा नाही.'+(' निवडीचे संक्षिप्त वर्णन नोंदवलेल्या शीर्षक आणि खंडनिर्देशांवरून व्युत्पन्न; अचूक मराठी उतारा प्रत्येक सद्य संदर्भात आहे.' if rid in derived_rendering_descriptions else ''),
            'provisional':True,'review_priority':'high','expert_review_useful':True,
            'expert_review_reason':'गणिती अर्थ व मराठी शब्दक्रम तज्ज्ञांना पुन्हा तपासता यावा.',
            'please_double_check_question':question,'occurrences':recs})
        legacy.append({'schema':'openlogic-expert-review-decision/1','record_kind':'corrective_review',
            'issue_id':rid,'english':term,'chosen_marathi':chosen,'rationale':reason,
            'precise_review_question':question,'occurrence_ids':ids,'open_to_correction':True})
        markdown.extend([f'## {rid} — {uid}', '', f'मूळ शब्दरचना: {term}', '',f'निवड: {chosen}', '',reason,'',question,'',
                         'संदर्भखंड: '+', '.join(row['affected_segments'])+'.',''])
    assert len(canonical)==len({d['decision_id'] for d in canonical})
    return canonical,legacy,occurrences,markdown,{'corrective_decisions':len(canonical),'corrective_occurrences':len(occurrences),
        'derived_corrective_rendering_descriptions':derived_rendering_descriptions}
