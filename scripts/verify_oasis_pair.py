"""Validate the selected OASIS files and run authenticated APIs in a temporary DB.

Run from the project: python scripts/verify_oasis_pair.py --deep-learning
Research images stay in /data/test-data; this never imports them into the public demo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sys
import tempfile
import time

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))


def verify(args):
    manifest = json.loads((PROJECT / 'tests/data/oasis_pair.json').read_text())
    root = Path(args.data_root or manifest['ubuntu_root'])
    report = {'version': (PROJECT / 'VERSION').read_text().strip(), 'files': {}, 'checks': []}
    started = time.monotonic()
    for relative, expected in manifest['files'].items():
        path = root / relative
        assert path.stat().st_size == expected['bytes'], relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected['sha256'], relative
        report['files'][relative] = expected
    report['checks'].append('24 source file sizes and SHA-256 digests')

    import numpy as np
    import SimpleITK as sitk
    sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(2)
    with tempfile.TemporaryDirectory(prefix='medical-v9-oasis-') as sandbox:
        os.environ['MEDICAL_DATA_DIR'] = sandbox
        os.environ['COOKIE_SECURE'] = '0'  # Isolated TestClient only; production stays HTTPS secure.
        from fastapi.testclient import TestClient
        from backend import store
        from backend.app import app, IMAGES, add_file

        user = {'id': secrets.token_hex(16), 'department': 'isolated-oasis-verification'}
        secret = secrets.token_urlsafe(24)
        with store.connect() as connection:
            connection.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)',
                               (user['id'], 'oasis-test@example.invalid', 'OASIS test',
                                user['department'], 'head', 1, store.password(secret)))
        ids = {}
        images = {}
        for role in ['fixed', 'moving', 'fixed_labels', 'moving_labels']:
            image = sitk.ReadImage(str(root / manifest[role]))
            assert image.GetDimension() == 3 and image.GetNumberOfComponentsPerPixel() == 1
            assert np.isfinite(sitk.GetArrayViewFromImage(image)).all(), role
            images[role] = image
            fid = secrets.token_hex(16)
            shutil.copyfile(root / manifest[role], IMAGES / (fid + '.nii.gz'))
            add_file(fid, user, role + ' ' + manifest[role])
            ids[role] = fid
        fixed = images['fixed']
        for image in images.values():
            assert image.GetSize() == fixed.GetSize() == (160, 192, 224)
            for getter in ['GetSpacing', 'GetOrigin', 'GetDirection']:
                assert np.allclose(getattr(image, getter)(), getattr(fixed, getter)())
        report['geometry'] = {'size': list(fixed.GetSize()), 'spacing': list(fixed.GetSpacing())}
        report['checks'].append('four finite scalar 3D images share the trained OASIS grid')

        with TestClient(app) as client:
            response = client.post('/api/auth/login', json={
                'email': 'oasis-test@example.invalid', 'password': secret})
            response.raise_for_status()
            client.headers['X-CSRF-Token'] = client.get('/api/auth/me').json()['csrf']
            response = client.get('/api/images/' + ids['fixed'] + '.nii.gz')
            response.raise_for_status()
            assert response.content == (root / manifest['fixed']).read_bytes()

            def evaluate(prediction_id, reference_id):
                response = client.post('/api/tools/evaluate', json={
                    'prediction_id': prediction_id, 'reference_id': reference_id,
                    'metrics': ['dice', 'hd', 'hd95', 'asd', 'assd']})
                response.raise_for_status()
                result = response.json()
                for metric, summary in result['summary'].items():
                    value = summary['mean']
                    assert value is not None and np.isfinite(value), metric
                    assert 0 <= value <= 1 if metric == 'dice' else value >= 0
                return result['summary']

            report['before_registration'] = evaluate(ids['moving_labels'], ids['fixed_labels'])
            report['checks'].append('authenticated NIfTI download and five real-label metrics')
            catalog = client.get('/api/dl/models').json()
            report['models'] = catalog
            if args.deep_learning:
                response = client.post('/api/deep-learning', json={
                    'fixed_id': ids['fixed'], 'moving_id': ids['moving'], 'model_id': 'lfcamorph-oasis'})
                response.raise_for_status()
                job_id = response.json()['job_id']
                deadline = time.monotonic() + 900
                while time.monotonic() < deadline:
                    job = client.get('/api/jobs/' + job_id).json()
                    if job['status'] in ('done', 'failed'):
                        break
                    time.sleep(1)
                assert job['status'] == 'done', job
                report['deep_learning'] = job['result']
                result_id = job['result']['result_id']
                warped = sitk.ReadImage(str(IMAGES / (result_id + '.nii.gz')))
                assert warped.GetSize() == fixed.GetSize()
                assert np.isfinite(sitk.GetArrayViewFromImage(warped)).all()
                field = sitk.ReadImage(str(IMAGES / (result_id + '.field.nii.gz')), sitk.sitkVectorFloat64)
                assert np.isfinite(sitk.GetArrayViewFromImage(field)).all()
                transform = sitk.DisplacementFieldTransform(field)
                labels = sitk.Resample(images['moving_labels'], images['fixed_labels'], transform,
                                       sitk.sitkNearestNeighbor, 0, images['moving_labels'].GetPixelID())
                label_id = secrets.token_hex(16)
                sitk.WriteImage(labels, str(IMAGES / (label_id + '.nii.gz')))
                add_file(label_id, user, 'warped labels', 'result', ids['fixed_labels'])
                report['after_registration'] = evaluate(label_id, ids['fixed_labels'])
                report['checks'].append('LFCAMorph API inference, finite warp/field, and warped-label evaluation')
    report.update(status='passed', runtime_s=round(time.monotonic() - started, 2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root')
    parser.add_argument('--deep-learning', action='store_true')
    parser.add_argument('--output', default='/data/medical-web-v9/oasis-verification.json')
    args = parser.parse_args()
    result = verify(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ['status', 'version', 'checks', 'runtime_s']}, ensure_ascii=False))
