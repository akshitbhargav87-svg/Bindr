#!/usr/bin/env python3
"""Run contract regressions against an explicit local source tree; never fetch or mutate Git."""
import argparse
import os
import secrets
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Source root containing backend/; unchanged by this runner')
    parser.add_argument('--auth-hook', type=Path, help='Test-only Python file exporting authenticate(client, session)')
    parser.add_argument('--diagnostic-anonymous', action='store_true', help='Exercise local routes without auth; does not verify authenticated workflows')
    parser.add_argument('--ocr-model-dir', type=Path, help='Directory containing already-downloaded public OCR model assets; network stays blocked')
    parser.add_argument('--junit', type=Path, help='Optional report outside production source')
    args = parser.parse_args()
    source = args.source.resolve()
    if not source.is_dir():
        parser.error('Source directory does not exist')
    if args.auth_hook and args.diagnostic_anonymous:
        parser.error('Choose authentication hook OR anonymous diagnostic mode')
    tests = Path(__file__).resolve().parents[1] / 'tests' / 'regression'
    ocr_path = args.ocr_model_dir or (Path(os.environ['OCR_MODEL_DIR']) if os.getenv('OCR_MODEL_DIR') else None)
    if ocr_path and not ocr_path.is_dir():
        parser.error('OCR model directory does not exist')
    env = os.environ.copy()
    # No credentials or inherited live DB/storage may reach the test process.
    for key in list(env):
        if any(word in key.upper() for word in ('API_KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'DATABASE_URL', 'EVIDENCE_', 'AI_', 'META_', 'MODEL_')):
            env.pop(key)
    if ocr_path:
        env['OCR_MODEL_DIR'] = str(ocr_path.resolve())
    env.update(AI_PROVIDER='mock', AUTH_SECRET=secrets.token_urlsafe(48), PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    # Prevent accidental import from cwd/PYTHONPATH and avoid loading target .env files.
    env.pop('PYTHONPATH', None)
    with tempfile.TemporaryDirectory(prefix='bindr-regression-run-') as work:
        env['DATABASE_URL'] = 'sqlite:///' + str(Path(work) / 'bootstrap.sqlite')
        env['EVIDENCE_STORAGE_DIR'] = str(Path(work) / 'evidence')
        env['EVIDENCE_LOCAL_DIR'] = env['EVIDENCE_STORAGE_DIR']
        cmd = [sys.executable, '-m', 'pytest', str(tests), '--confcutdir', str(tests),
               '-q', '-ra', '--tb=short', '-p', 'no:cacheprovider', '--bindr-source', str(source)]
        if args.auth_hook:
            cmd += ['--bindr-auth-hook', str(args.auth_hook.resolve())]
        if args.diagnostic_anonymous:
            cmd += ['--bindr-diagnostic-anonymous']
        if args.junit:
            cmd += ['--junitxml', str(args.junit.resolve())]
        print('Mode:', 'diagnostic anonymous (authentication NOT verified)' if args.diagnostic_anonymous else 'authentication required for protected HTTP workflows', flush=True)
        return subprocess.call(cmd, cwd=work, env=env)


if __name__ == '__main__':
    raise SystemExit(main())
