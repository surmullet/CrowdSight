"""Render prediction-blind crop review sheets for frozen video samples/layouts."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", required=True, type=Path)
    parser.add_argument("--layouts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    import cv2
    import numpy as np
    layouts = json.loads(args.layouts.read_bytes())
    args.output.mkdir(parents=True, exist_ok=False)
    for source, spec in layouts["videos"].items():
        selection = json.loads((args.intake / source / "frames.json").read_bytes())
        frames = []
        for row in selection["frames"]:
            raw = (args.intake / source / row["path"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != row["sha256"]:
                raise ValueError("Review frame hash mismatch")
            frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
            frames.append(cv2.resize(frame, tuple(layouts["reference_size"]), interpolation=cv2.INTER_AREA))
        sheet = np.full((len(spec["spaces"]) * 115, len(frames) * 180, 3), 245, np.uint8)
        for i, space in enumerate(spec["spaces"]):
            x0, y0, x1, y1 = space["box"]
            for j, frame in enumerate(frames):
                crop = cv2.resize(frame[y0:y1, x0:x1], (176, 88))
                y, x = i * 115, j * 180
                sheet[y + 24:y + 112, x:x + 176] = crop
                label = f"{space['id']} f{selection['frames'][j]['frame_index']}"
                cv2.putText(sheet, label, (x + 3, y + 17), cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 0, 0), 1)
        cv2.imwrite(str(args.output / f"{source}-blind-crops.jpg"), sheet)
        overview = frames[0].copy()
        for space in spec["spaces"]:
            x0, y0, x1, y1 = space["box"]
            cv2.rectangle(overview, (x0, y0), (x1, y1), (0, 255, 255), 1)
            cv2.putText(overview, space["id"], (x0, y0 - 4), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 255), 1)
        cv2.imwrite(str(args.output / f"{source}-layout.jpg"), overview)
    (args.output / "review-provenance.json").write_text(json.dumps({
        "layouts_sha256": hashlib.sha256(args.layouts.read_bytes()).hexdigest(),
        "prediction_blind": True, "labels_generated": False,
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
