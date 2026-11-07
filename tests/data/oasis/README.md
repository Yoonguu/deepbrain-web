# 외부 채점용 OASIS 테스트 파일

사용자가 공개 데모에 등록하고 GitHub white 브랜치에 포함하도록 승인한 4개 파일이다. VERSION은 9.0.0이다.

| 역할 | 파일 |
|---|---|
| Fixed 영상 | OASIS_OAS1_0001_MR1/aligned_norm.nii.gz |
| Moving 영상 | OASIS_OAS1_0010_MR1/aligned_norm.nii.gz |
| Fixed 평가 라벨 | OASIS_OAS1_0001_MR1/aligned_seg35.nii.gz |
| Moving 평가 라벨 | OASIS_OAS1_0010_MR1/aligned_seg35.nii.gz |

모두 160×192×224, 1mm 격자다. 원본 경로·크기·SHA-256은 ../oasis_pair.json에서 확인할 수 있다. 원본 영상의 데이터셋 이용 조건을 준수해야 하며, 이 저장소에서 별도 이용 허가를 부여하는 것은 아니다.

프로젝트 루트에서 Python 3.12와 requirements.txt, requirements-dl.txt를 준비한 뒤 실행한다. PyTorch 설치는 CPU 또는 CUDA 환경에 맞춘다.

```bash
python scripts/verify_oasis_pair.py --data-root tests/data/oasis --selected-only --deep-learning --output /tmp/oasis-grading.json
```

이 명령은 임시 DB에서 실제 모델 정합, 변형장, nearest-neighbor 라벨 변형과 5개 지표를 검증한다. 결과는 지정한 JSON에 기록하며 실행 중인 웹 DB를 변경하지 않는다. --deep-learning을 생략하면 파일과 정합 전 지표만 검사한다.

웹에서 직접 확인하려면 두 aligned_norm 파일을 각각 Fixed와 Moving으로 열고, 라벨 파일은 정량 평가에 사용한다. 이전 실측 수치는 docs/verification/v9-oasis.json에 있다.
