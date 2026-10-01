"""Generate sample_real_heatmap.png using ImageSpaceHeatmapGenerator from sample_real_observations.json."""
import json
from pathlib import Path
from crowdsight.service.analytics.heatmaps import ImageSpaceHeatmapGenerator

json_path = Path("web/public/sample_real_observations.json")
output_png = Path("web/public/sample_real_heatmap.png")

with json_path.open("r", encoding="utf-8") as f:
    data = json.load(f)

obs_list = list(data["frames"].values())
res = ImageSpaceHeatmapGenerator.generate(
    observations=obs_list,
    image_width=data["metadata"]["width"],
    image_height=data["metadata"]["height"],
)

with output_png.open("wb") as f:
    f.write(res.png_bytes)

print(f"Generated heatmap saved to {output_png} ({len(res.png_bytes)} bytes)")
