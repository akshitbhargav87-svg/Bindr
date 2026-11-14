import io
import os
from pathlib import Path
import pytest
from helpers import new_case, upload, extract, review, detail


@pytest.fixture
def screenshot():
    Image = pytest.importorskip('PIL.Image', reason='PENDING: Pillow unavailable')
    from PIL import ImageDraw, ImageFont
    image = Image.new('RGB', (1100, 220), 'white')
    windows_font = str(Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / 'arial.ttf')
    for font_name in ('DejaVuSans.ttf', windows_font):
        try:
            font = ImageFont.truetype(font_name, 26)
            break
        except OSError:
            continue
    else:
        pytest.skip('PENDING: DejaVu Sans or Arial unavailable; install a test font')
    ImageDraw.Draw(image).multiline_text((30, 30), 'We will refund INR 150.00\nwithin 5 business days for order DEMO-42.', font=font, fill='black', spacing=16)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')  # No text metadata: recognition must read pixels.
    return buffer.getvalue()


@pytest.fixture
def real_ocr(source_root, monkeypatch):
    if not (source_root / 'backend/app/ai/document_processor.py').is_file():
        pytest.skip('PENDING: AI document processor code unavailable')
    pytest.importorskip('onnxruntime', reason='PENDING: ONNX runtime unavailable')
    pytest.importorskip('numpy', reason='PENDING: numpy unavailable')
    module = pytest.importorskip('rapidocr', reason='PENDING: RapidOCR unavailable')
    import backend.app.ai.document_processor as processor
    try:
        processor.get_ocr_engine.cache_clear()
        engine = processor.get_ocr_engine()
        engine._load_det_model()
        engine._load_cls_model()
        engine._load_rec_model()
    except Exception as exc:
        pytest.skip(f'PENDING: RapidOCR runtime/model assets unavailable offline ({type(exc).__name__}); install/cache assets before running')
    calls = []
    class ObservedOCR:
        def __call__(self, *args, **kw):
            output = engine(*args, **kw)  # Real inference; no fake OCR output.
            calls.append(output)
            return output
    monkeypatch.setattr(processor, 'get_ocr_engine', lambda: ObservedOCR())
    return calls


def test_real_rapidocr_reads_synthetic_pixels(source_root, screenshot, real_ocr):
    pytest.importorskip('pymupdf', reason='PENDING: PyMuPDF unavailable')
    from backend.app.ai.document_processor import DocumentProcessor
    doc = DocumentProcessor().process_bytes(screenshot, filename='refund.png')
    assert real_ocr, 'Expected real RapidOCR invocation'
    assert not doc.is_empty
    assert 'refund' in doc.raw_text.lower() and '150' in doc.raw_text


def test_http_screenshot_real_ocr_mock_ai_then_review(api, adapter_module, screenshot, real_ocr, monkeypatch):
    from backend.app.ai.providers.mock import MockAIProvider
    original = MockAIProvider.extract_commitment
    inference_texts = []
    def observe(self, text, metadata=None):
        inference_texts.append(text)
        return original(self, text=text, metadata=metadata)
    monkeypatch.setattr(MockAIProvider, 'extract_commitment', observe)
    c = new_case(api)
    e, _ = upload(api, c['id'], 'refund.png', screenshot, 'image/png')
    r = extract(api, c['id'], [e['id']])
    assert real_ocr, 'HTTP extraction bypassed RapidOCR'
    assert inference_texts and 'refund' in inference_texts[0].lower()
    assert '150' in inference_texts[0]
    assert r.status_code == 201
    d = r.json()['extraction']
    assert d['status'] == 'pending_review'
    assert detail(api, c['id'])['commitments'] == []
    assert d['candidates']
    for candidate in d['candidates']:
        for source in candidate['sources']:
            assert source['evidence_id'] == e['id']
            assert source['quote'] in inference_texts[0]
    approved = review(api, c['id'], d, e['id'], candidate_id=d['candidates'][0]['candidate_id'], amount=15000)
    assert approved.status_code == 200
    state = detail(api, c['id'])
    assert len(state['commitments']) == 1
    assert state['commitments'][0]['amount_minor'] == 15000
    assert state['commitments'][0]['evidence_ids'] == [e['id']]
    assert api.get(e['download_path']).content == screenshot
