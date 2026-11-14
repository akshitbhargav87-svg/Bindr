"""Always available checks; never interpret snapshots as proof of runtime integration."""
import hashlib
import json
from pathlib import Path
from uuid import UUID
import pytest


@pytest.mark.parametrize('name', ['new-refund', 'revised-commitment', 'overdue-case', 'resolved-case'])
def test_synthetic_fixture_references(name):
    root = Path(__file__).resolve().parents[1] / 'fixtures'
    f = json.loads((root / (name + '.json')).read_text())
    data = f['expected']
    evidence = {e['id']: e for e in data['evidence']}
    commitments = {k['id']: k for k in data['commitments']}
    extractions = {x['id']: x for x in data['extractions']}
    for e in evidence.values():
        UUID(e['id'])
        content = f['evidence_text'][e['id']].encode()
        assert hashlib.sha256(content).hexdigest() == e['sha256']
        assert len(content) == e['size_bytes']
    for k in commitments.values():
        assert set(k['evidence_ids']) <= evidence.keys()
        assert k['extraction_id'] in extractions
        assert k['id'] in extractions[k['extraction_id']]['reviewed_commitment_ids']
        if k['supersedes_id']:
            old = commitments[k['supersedes_id']]
            assert old['status'] == 'superseded'
            assert set(old['evidence_ids']) <= set(k['evidence_ids'])
    for x in extractions.values():
        for c in x['candidates']:
            for source in c['sources']:
                assert source['quote'] in f['evidence_text'][source['evidence_id']]
