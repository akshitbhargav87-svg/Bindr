"""Opt-in loopback combined QA server. Only the paid inference operation is synthetic."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from backend.app.main import app
from backend.app.api.v2.reviews import get_intelligence
from backend.app.services.ai_adapter import AIModuleAdapter
from backend.app.tests.test_intelligence_combined import CombinedEngine
from backend.app.api.v2.jobs import get_db


def main():
    import os
    if '--synthetic-inference' not in sys.argv or os.getenv('ENVIRONMENT')!='development' or os.getenv('AUTH_PROVIDER')!='anonymous':
        raise SystemExit('Explicit development/anonymous/synthetic configuration is required.')
    app.dependency_overrides[get_intelligence]=lambda:CombinedEngine()
    # Test-only, explicit worker step: no public production dispatch endpoint is added.
    from fastapi import Depends
    from backend.app.models.jobs import Job
    from backend.app.services.platform.exports import build
    @app.post('/__qa/process-exports')
    def process(db=Depends(get_db)):
        rows=db.query(Job).filter_by(kind='export',state='queued').all()
        for row in rows:
            build(db,row);row.state='succeeded'
        db.commit();return {'processed':len(rows)}
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8033,access_log=False)


if __name__=='__main__':main()
