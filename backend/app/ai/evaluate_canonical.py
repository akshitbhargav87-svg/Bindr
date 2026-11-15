"""Fresh OFFLINE diagnostic; does not rewrite original QA or imply live acceptance."""
import argparse
import json
from pathlib import Path
from time import monotonic


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('storage/track-b-retests/canonical-offline.json'))
    args=parser.parse_args()
    from backend.app.core.config import settings
    from backend.app.services.ai_adapter import AIModuleAdapter, AIAdapterError
    settings.AI_PROVIDER='mock'
    root=Path(__file__).resolve().parents[3]
    fixtures=json.loads((root/'tests/contracts/intelligence/canonical-inputs.json').read_text(encoding='utf-8'))
    results=[]
    for f in fixtures:
        started=monotonic()
        entry={'fixture_id':f['id'],'communication_date':f['communication_date'],
               'provider':'offline-rule-based','scope':'local adapter only; no live model or v2 service acceptance'}
        try:
            entry['output']=AIModuleAdapter().extract_commitments('synthetic-'+f['id'],[{'evidence_id':'e-'+f['id'],'text':f['text']}],merchant_name=f['company'])
        except AIAdapterError as e:
            entry['error']={'code':e.code,'message':str(e)}
        entry['duration_ms']=round((monotonic()-started)*1000)
        results.append(entry)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'schema_version':1,'mode':'offline diagnostic','results':results},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{'id':r['fixture_id'],'candidates':len(r.get('output',{}).get('candidates',[])),'error':r.get('error',{}).get('code'),'ms':r['duration_ms']} for r in results]))


if __name__=='__main__':main()
