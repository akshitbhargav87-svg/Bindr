from types import SimpleNamespace
from uuid import uuid4
import pytest


def test_missing_meta_credentials_never_infers_mock(adapter_module, ai_available, monkeypatch):
    # Explicit Meta production configuration; unrelated inherited keys cannot rescue it.
    monkeypatch.setenv('AI_PROVIDER', 'meta')
    settings = getattr(adapter_module, 'settings', None)
    if settings is not None:
        monkeypatch.setattr(settings, 'AI_PROVIDER', 'meta')
        monkeypatch.setattr(settings, 'MODEL_API_KEY', None)
    from backend.app.ai.providers.mock import MockAIProvider
    calls = []
    def forbid_mock(*a, **kw):
        calls.append(True)
        raise AssertionError('Missing production credentials invoked mock inference')
    monkeypatch.setattr(MockAIProvider, 'extract_commitment', forbid_mock)
    with pytest.raises(adapter_module.AIServiceUnavailableError):
        adapter_module.AIModuleAdapter().extract_commitments(str(uuid4()), [{'evidence_id': str(uuid4()), 'text': 'We will refund INR 100.00.', 'occurred_at': None}])
    assert not calls


@pytest.mark.parametrize('matching_index', [0, 1])
def test_quote_is_linked_to_its_actual_evidence(adapter_module, monkeypatch, matching_index):
    quote = 'We will refund INR 4999.00 for order DEMO-42.'
    evidence = [{'evidence_id': str(uuid4()), 'text': 'Unrelated receipt metadata.', 'occurred_at': None} for _ in range(2)]
    evidence[matching_index]['text'] = quote
    # Stub only AI inference. Exercise the real adapter's source translation.
    result = SimpleNamespace(commitment_category=SimpleNamespace(value='refund'), commitment_description='Refund',
                             supporting_quotation=quote, amount=4999.0, currency='INR', missing_or_ambiguous_fields=[])
    adapter = adapter_module.AIModuleAdapter()
    # Current pipeline processes each source independently; stub only inference.
    # An unrelated file returns no commitment rather than borrowing another file's quote.
    import backend.app.ai
    def infer(**kw):
        text = kw['file_source'].decode('utf-8')
        if quote not in text:
            return SimpleNamespace(commitment_category=SimpleNamespace(value='no_commitment'), raw_source_text=text)
        return SimpleNamespace(**vars(result), raw_source_text=text)
    monkeypatch.setattr(backend.app.ai, 'extract_commitment_from_evidence', infer)
    monkeypatch.setattr(adapter, '_get_engine', lambda: SimpleNamespace(provider=None))
    out = adapter.extract_commitments(str(uuid4()), evidence)
    sources = out['candidates'][0]['sources']
    assert sources
    texts = {e['evidence_id']: e['text'] for e in evidence}
    for source in sources:
        assert source['evidence_id'] in texts
        assert source['quote'] in texts[source['evidence_id']]
    assert any(s['evidence_id'] == evidence[matching_index]['evidence_id'] for s in sources)
