# Crowd evaluation dataset record

Complete one record for each source video/flight/site partition before model inference. Keep this record beside the private dataset under access control. Do not commit footage, identifiable labels, credentials, or restricted metadata to Git.

## Identity and access

- Dataset ID/version:
- Source ID and site/camera description:
- Source video filename and SHA-256:
- Source owner and contact:
- Collection date range and timezone:
- Resolution, frame rate, camera/view geometry:
- Data location and access-control owner:
- Permission/consent basis and permitted uses:
- Permission evidence reference and SHA-256:
- Permission reviewer ID, review date, and decision for model evaluation:
- Retention/deletion date:
- Privacy review and redaction requirements:

## Partition and independence

- Partition role: train / validation / test
- Partition unit: video / site / flight / camera-date
- Immutable partition ID:
- Partition lock date/time, before candidate predictions: yes / no
- Split manifest version and SHA-256:
- Neighboring frames or related views in other partitions: no / yes / unknown
- Candidate model profile/checkpoint SHA-256:
- Candidate training-data manifest or source-run reference:
- Training/test overlap status: verified_disjoint / verified_overlap / overlap_possible / unknown_or_mixed
- Evidence supporting disjointness (manifest IDs, source hashes, run record):
- Independence-review artifact reference and SHA-256:
- Independent reviewer name/ID, review date, and decision:

Do not set `verified_disjoint` based only on different filenames or different frame indices. Use `verified_overlap` when a source hash or partition is known to overlap, `overlap_possible` when evidence suggests overlap but cannot confirm it, and `unknown_or_mixed` when lineage is unresolved. Only `verified_disjoint` can support held-out-candidate status, and only with complete hashed inventories plus a referenced, hash-identified independent review. The evaluator does not inspect the referenced review artifact; a named reviewer must verify its content and authorization before any result is described as verified held-out or release-approved.

## Annotation protocol

- Annotation guide/version:
- Reviewer IDs (stored privately if needed):
- Sampling protocol and selected frame list hash:
- Definition of a visible person and partial/occluded-person policy:
- Bounding-box convention: original-image pixel `xyxy`:
- Uncertain-region policy:
- Independent second-review rate and adjudication procedure:
- Zone geometry version and coordinate convention:
- Scene-stratum vocabulary:

## Known limitations

- Unsupported camera or scene conditions:
- Unrepresented operating conditions:
- Missing/corrupt frames and handling:
- Known annotation disagreements:
- Restrictions on report distribution:

## Release checklist

- [ ] Source hash recomputed from the exact source video.
- [ ] Permission and retention terms recorded and approved for this use.
- [ ] Split unit and partition are fixed before inference/model selection.
- [ ] Every sampled frame has a complete review or an explicit uncertain status.
- [ ] Model-specific train/test overlap status is evidence-backed.
- [ ] Footage and restricted labels remain outside Git.
- [ ] Site owner approved the evaluation protocol and eventual acceptance criteria.
