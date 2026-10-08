"""Download explicitly selected public video artifacts and freeze review frames.

Source manifest must record reviewed terms, byte sizes and publisher SHA-512s.
This script does not select models or create occupancy labels.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resume-partial", action="store_true", help="Resume interrupted .part downloads only; refuses prepared directories")
    args = parser.parse_args()
    root = args.output.resolve()
    repo = Path(__file__).resolve().parents[1]
    if root == repo or repo in root.parents:
        raise ValueError("Keep video artifacts outside Git")
    sources = json.loads(args.sources.read_bytes())
    root.mkdir(parents=True, exist_ok=args.resume_partial)
    if (root / "intake.json").exists():
        raise ValueError("Intake is already complete; preserve the existing run")

    def intake(item: dict) -> dict:
        import cv2
        target = root / item["id"]
        target.mkdir(exist_ok=args.resume_partial)
        video = target / item["name"]
        if Path(item["name"]).name != item["name"] or Path(item["id"]).name != item["id"]:
            raise ValueError("Source names must be simple path components")
        partial = video.with_suffix(".part")
        if any(path != partial for path in target.iterdir()):
            raise ValueError("Resume supports download-only directories, not existing prepared artifacts")
        offset = partial.stat().st_size if args.resume_partial and partial.exists() else 0
        if offset > item["size"]:
            raise ValueError("Partial download exceeds declared size")
        headers = {"User-Agent": "CrowdSight-private-evaluation/1.0"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        if offset < item["size"]:
            request = urllib.request.Request(item["url"], headers=headers)
            with urllib.request.urlopen(request, timeout=120) as response:
                if offset and (response.status != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-")):
                    raise ValueError("Server did not honor the resume range; partial file preserved")
                with partial.open("ab" if offset else "xb") as stream:
                    total = offset
                    while block := response.read(1024 * 1024):
                        total += len(block)
                        if total > item["size"]:
                            raise ValueError("Download exceeds declared size")
                        stream.write(block)
        if partial.stat().st_size != item["size"] or digest(partial, "sha512") != item["sha512"]:
            raise ValueError("Publisher size/SHA-512 verification failed")
        partial.rename(video)
        cap = cv2.VideoCapture(str(video))
        fps, count = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0 or count < 6:
            raise ValueError("Invalid video metadata")
        indices = [round(i * (count - 1) / 5) for i in range(6)]
        selection = {"source_id": item["id"], "source_sha256": digest(video), "video": item["name"],
                     "role": item["role"], "fps": fps, "frame_count": count,
                     "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                     "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                     "frame_indices": indices, "selection_before_inference": True,
                     "frames": []}
        (target / "selection-locked.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
        for index in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = cap.read()
            if not ok:
                raise ValueError(f"Cannot decode selected frame {index}")
            path = target / f"frame-{index:06d}.png"
            if not cv2.imwrite(str(path), frame):
                raise RuntimeError("Frame writing failed")
            selection["frames"].append({"frame_index": index, "media_time_s": index / fps,
                                        "path": path.name, "sha256": digest(path)})
            preview = cv2.resize(frame, (1280, round(frame.shape[0] * 1280 / frame.shape[1])))
            cv2.imwrite(str(target / f"preview-{index:06d}.jpg"), preview)
        cap.release()
        (target / "frames.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
        print(f"Verified {item['id']}: {count} frames, selected {indices}", flush=True)
        return selection

    with ThreadPoolExecutor(max_workers=3) as executor:
        selections = list(executor.map(intake, sources["videos"]))
    report = {"status": "PREPARED", "sources_sha256": digest(args.sources),
              "script_sha256": digest(Path(__file__)), "selections": selections}
    (root / "intake.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
