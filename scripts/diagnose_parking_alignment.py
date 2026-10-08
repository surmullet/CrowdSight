"""Compare fixed-view homography and partial-affine drift on development video.

This measures heuristic acceptance, not registration correctness or accuracy.
"""
import argparse
import json
from pathlib import Path
import hashlib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    import cv2
    import numpy as np
    selection = json.loads(args.selection.read_bytes())
    video = args.selection.parent/selection['video']
    digest = hashlib.sha256()
    with video.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    if digest.hexdigest() != selection['source_sha256']:
        raise ValueError('Source mismatch')
    cap = cv2.VideoCapture(str(video))
    orb = cv2.ORB_create(nfeatures=1800)
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    corners = np.float32([[0,0],[1279,0],[1279,719],[0,719]]).reshape(-1,1,2)
    rows = []
    indices = sorted(set(range(0, selection['frame_count'], max(1,round(selection['fps'])))) | set(selection['frame_indices']))
    for index in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES,index)
        ok, frame = cap.read()
        if not ok:
            raise ValueError(f'Decode failure {index}')
        gray = cv2.cvtColor(cv2.resize(frame,(1280,720), interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY)
        points, desc = orb.detectAndCompute(gray,None)
        if index == 0:
            reference, reference_desc = points, desc
        row = {'frame_index':index,'homography':{'accepted':False},'partial_affine':{'accepted':False}}
        if desc is not None and reference_desc is not None:
            matches = [pair[0] for pair in matcher.knnMatch(reference_desc,desc,k=2) if len(pair)==2 and pair[0].distance < .7*pair[1].distance]
            if len(matches)>=30:
                a=np.float32([reference[m.queryIdx].pt for m in matches]).reshape(-1,1,2)
                b=np.float32([points[m.trainIdx].pt for m in matches]).reshape(-1,1,2)
                for name in ('homography','partial_affine'):
                    if name=='homography':
                        transform,mask=cv2.findHomography(a,b,cv2.RANSAC,2.5)
                    else:
                        affine,mask=cv2.estimateAffinePartial2D(a,b,method=cv2.RANSAC,ransacReprojThreshold=2.5)
                        transform=np.vstack([affine,[0,0,1]]) if affine is not None else None
                    if transform is None or mask is None or not np.isfinite(transform).all():
                        continue
                    drift=float(np.linalg.norm(cv2.perspectiveTransform(corners,transform)-corners,axis=2).max())
                    residual=np.linalg.norm(cv2.perspectiveTransform(a,transform)-b,axis=2).reshape(-1)
                    inliers=mask.reshape(-1).astype(bool)
                    median=float(np.median(residual[inliers])) if inliers.any() else None
                    accepted=bool(inliers.sum()>=30 and inliers.mean()>=.6 and drift<=3 and (name=='homography' or (median is not None and median<=2)))
                    row[name]={'accepted':accepted,'drift_px':drift,'inliers':int(inliers.sum()),'inlier_ratio':float(inliers.mean()),'median_residual_px':median}
        rows.append(row)
    cap.release()
    report={'scope':'DEVELOPMENT_ONLY_HEURISTIC_NOT_GROUND_TRUTH','source_sha256':selection['source_sha256'],
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'updates':len(rows),'accepted':{name:sum(r[name]['accepted'] for r in rows) for name in ('homography','partial_affine')},'rows':rows}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2,allow_nan=False)
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}))


if __name__=='__main__':
    main()
