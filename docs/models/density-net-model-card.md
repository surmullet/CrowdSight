# Model card: source `density_net`

## Status

Separate crowd-density-map estimator available as `../heat_map/models/density_net.pt`. SHA-256 `72fa74348afb87fd1b40eaeca2948badae58d2bfd13a70d1e19bad72a19faa0d` was verified locally against the source checkpoint. This is not the user's person-box detector and does not produce boxes or track IDs.

## Intended use

Experimental crowd-count estimation and a frame-relative density surface for dense UAV imagery. Estimated count is a continuous model output and must not be described as an exact person headcount. It is not a geographic density map.

## Source implementation facts

- Compact encoder-decoder CNN in `heat_map/src/crowd/model.py`, input RGB/BGR handling in source estimator to be confirmed at integration.
- Source documentation describes 448-pixel tiles, quarter-resolution map, training target scale 100, tile batch size 8, and AMP disabled.
- Source docs state DroneCrowd was used for training and describe a 36-frame held-out comparison with mean ground truth 114 per frame.
- Recorded comparison in source README: this model MAE 20.8, RMSE 24.2, bias -1.1; detector `best.pt` MAE 36.5, RMSE 43.0, bias -34.5. These values are not independently verified here because the referenced evaluation report/manifest was not found in the scanned files.

## Limitations

The source README describes tile seams and non-person high-density responses (including birds and roof clutter) on moving-camera 4K footage. The estimator trades box/identity output for density coverage. It has no direct per-person tracking. Counts and alerts require independent site-specific evaluation; the reported benchmark does not establish pilot-site accuracy.

## Release requirements

Verify training run/config, DroneCrowd dataset release and license, train/validation/test sequence split, preprocessing and color order, checkpoint provenance, exact runtime versions, and evaluation artifact. Compare against manual site labels. Keep estimated counts distinct from detector counts and preserve uncertainty/coverage reporting.
