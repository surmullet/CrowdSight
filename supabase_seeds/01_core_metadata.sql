-- ========================================================
-- CrowdSight Seed - Part 01: Core Metadata (Clean & Sequential IDs)
-- Tables: media_assets (3), zone_sets (2), zone_set_versions (7),
--         sessions (3), artifacts (6), audit_log (1)
-- Idempotent: ON CONFLICT (id) DO NOTHING
-- ========================================================

BEGIN;

-- 1. Table: media_assets
INSERT INTO media_assets (id, display_name, relpath, sha256, duration_s, fps, frame_count, width, height, codec, browser_playable, proxy_relpath, created_at)
VALUES
  ('media-01-crowd6', 'crowd6.mp4', 'crowd6.mp4', 'd3e6d0b724df74a3c165baa6fb541a32b4f95016a83e653f2ab52c3e9b2637b8', 25.12, 25.0, 628, 1280, 720, 'h264', true, NULL, '2026-10-01 08:42:36.022612'),
  ('media-02-150', '150.mp4', '150.mp4', '68fab50085ee8954b2e77ba11e61134cddefd0383435faaa2c58c32f40178787', 57.44, 25.0, 1436, 1920, 1440, 'h264', true, NULL, '2026-10-01 02:55:01.253872'),
  ('media-03-crowd', 'crowd.mp4', 'crowd.mp4', '4af588a274c4687894e13fa1fbaff0b35e5377ecc0b9f8892dfc5fe9d03bf23d', 5.666666666666667, 30.0, 170, 1920, 1080, 'h264', true, NULL, '2026-10-01 09:19:21.910403')
ON CONFLICT (id) DO NOTHING;

-- 2. Table: zone_sets
INSERT INTO zone_sets (id, name, created_at)
VALUES
  ('zones-150', 'Khu vuc Giam sat A & B', '2026-10-01 07:55:28.958754'),
  ('zones-crowd6', 'Khu vực giám sát (crowd6.mp4)', '2026-10-01 08:56:16.192117')
ON CONFLICT (id) DO NOTHING;

-- 3. Table: zone_set_versions
INSERT INTO zone_set_versions (id, zone_set_id, version, image_width, image_height, polygon_data, sha256, created_at)
VALUES
  ('zsv-150-v1', 'zones-150', 1, 1920, 1440, '{"zones": [{"zone_id": "zone-a", "name": "Khu vuc A", "vertices": [[200.0, 300.0], [600.0, 300.0], [550.0, 800.0], [150.0, 800.0]], "blind_regions": [], "description": null}]}'::jsonb, '4c5bf24dc3653b770bf287c9ca8b5a5c0a19125f6ca024b50e07b86416f59469', '2026-10-01 07:55:28.962746'),
  ('zsv-150-v2', 'zones-150', 2, 1920, 1440, '{"zones": [{"zone_id": "zone-a", "name": "Khu v\u1ef1c Gi\u00e1m s\u00e1t A (B\u00ean tr\u00e1i)", "vertices": [[495.0, 545.0], [1056.0, 432.0], [960.0, 1368.0], [96.0, 1368.0]], "blind_regions": [], "description": null}, {"zone_id": "zone-b", "name": "Khu v\u1ef1c Gi\u00e1m s\u00e1t B (B\u00ean ph\u1ea3i)", "vertices": [[1056.0, 360.0], [1824.0, 360.0], [1824.0, 1368.0], [960.0, 1368.0]], "blind_regions": [], "description": null}]}'::jsonb, 'cdcbb15cc871ae7e8395311506430760e45ffa6760c590d029b26ccaf5d636ef', '2026-10-01 08:04:29.984545'),
  ('zsv-150-v3', 'zones-150', 3, 1920, 1440, '{"zones": [{"zone_id": "zone-a", "name": "Khu v\u1ef1c Gi\u00e1m s\u00e1t A (B\u00ean tr\u00e1i)", "vertices": [[192.0, 432.0], [1056.0, 432.0], [960.0, 1368.0], [96.0, 1368.0]], "blind_regions": [], "description": null}, {"zone_id": "zone-b", "name": "Khu v\u1ef1c Gi\u00e1m s\u00e1t B (B\u00ean ph\u1ea3i)", "vertices": [[1056.0, 360.0], [1824.0, 360.0], [1824.0, 1368.0], [960.0, 1368.0]], "blind_regions": [], "description": null}]}'::jsonb, '2febea7de9943cadb4fd377ec70326e62fb84d49c0930fc06c3ef653ce19b575', '2026-10-01 08:51:27.958005'),
  ('zsv-150-v4', 'zones-150', 4, 1920, 1440, '{"zones": [{"zone_id": "zone-a", "name": "Khu v\u1ef1c A (crowd6)", "vertices": [[0.0, 8.0], [659.0, 0.0], [609.0, 720.0], [0.0, 714.0]], "blind_regions": [], "description": null}, {"zone_id": "zone-b", "name": "Khu v\u1ef1c B (crowd6)", "vertices": [[661.0, 0.0], [1280.0, 0.0], [1196.0, 1197.0], [610.0, 720.0]], "blind_regions": [], "description": null}]}'::jsonb, '06a479333b5528801d32f26cfb934af19b67047f7a5720da21149dbebe0d95bf', '2026-10-02 08:23:30.319968'),
  ('zsv-crowd6-v1', 'zones-crowd6', 1, 1280, 720, '{"zones": [{"zone_id": "zone-1790844922083", "name": "Khu v\u1ef1c A", "vertices": [[10.0, 16.0], [692.0, 11.0], [666.0, 720.0], [18.0, 661.0]], "blind_regions": [], "description": null}, {"zone_id": "zone-1790844944916", "name": "Khu v\u1ef1c B", "vertices": [[707.0, 6.0], [1272.0, 90.0], [1280.0, 698.0], [682.0, 711.0]], "blind_regions": [], "description": null}]}'::jsonb, 'afc3f8532d060f8f8282cf868d19e9dad46f29e5385ebc4246784b9f927ee844', '2026-10-01 08:56:16.194682'),
  ('zsv-crowd6-v2', 'zones-crowd6', 2, 1280, 720, '{"zones": [{"zone_id": "zone-a", "name": "Khu v\u1ef1c A (crowd6)", "vertices": [[0.0, 8.0], [659.0, 0.0], [601.0, 720.0], [0.0, 714.0]], "blind_regions": [], "description": null}, {"zone_id": "zone-b", "name": "Khu v\u1ef1c B (crowd6)", "vertices": [[661.0, 0.0], [1280.0, 0.0], [1280.0, 716.0], [610.0, 720.0]], "blind_regions": [], "description": null}]}'::jsonb, '02fde49dbde27a163ee380b56d4f639114388acffa22eaeb313d26699f94bcf9', '2026-10-01 09:10:42.938582'),
  ('zsv-crowd6-v3', 'zones-crowd6', 3, 1280, 720, '{"zones": [{"zone_id": "zone-a", "name": "Khu v\u1ef1c A (crowd6)", "vertices": [[0.0, 8.0], [659.0, 0.0], [609.0, 720.0], [0.0, 714.0]], "blind_regions": [], "description": null}, {"zone_id": "zone-b", "name": "Khu v\u1ef1c B (crowd6)", "vertices": [[661.0, 0.0], [1280.0, 0.0], [1280.0, 716.0], [610.0, 720.0]], "blind_regions": [], "description": null}]}'::jsonb, '8a0a2ce0867b238aea065297cf2677ac0ccffec92dd3a3a4944daebc5840688d', '2026-10-02 07:03:58.945960')
ON CONFLICT (id) DO NOTHING;

-- 4. Table: sessions
INSERT INTO sessions (id, media_asset_id, zone_set_version_id, model_profile_id, model_profile_sha256, checkpoint_sha256, tracker_config_sha256, options, status, progress, processed_frames, total_frames, error_code, user_action_hint, applicability_snapshot, synthetic, completeness, created_at, updated_at)
VALUES
  ('session-01-crowd6', 'media-01-crowd6', 'zsv-crowd6-v2', 'crowd_best_local_v2', '12ed238ead1833da63700bb2b3465488d0592bb967d1f9648a1157eee2f8af21', '12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc', '8cd88930d3be5557be0777f384eecff0a36a7011850fe613fc0a68178bfd5b01', '{"enable_tracker": true, "frame_stride": 1}'::jsonb, 'COMPLETED', 1.0, 628, 628, NULL, NULL, '{}'::jsonb, false, 'FULL', '2026-10-02 03:52:53.415725', '2026-10-02 04:00:27.362824'),
  ('session-02-crowd', 'media-03-crowd', 'zsv-crowd6-v3', 'crowd_best_local_v2', '12ed238ead1833da63700bb2b3465488d0592bb967d1f9648a1157eee2f8af21', '12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc', '8cd88930d3be5557be0777f384eecff0a36a7011850fe613fc0a68178bfd5b01', '{"enable_tracker": true, "frame_stride": 1}'::jsonb, 'COMPLETED', 1.0, 170, 170, NULL, NULL, '{}'::jsonb, false, 'FULL', '2026-10-02 07:22:00.495803', '2026-10-02 07:26:49.031546'),
  ('session-03-150', 'media-02-150', 'zsv-crowd6-v3', 'crowd_best_local_v2', '12ed238ead1833da63700bb2b3465488d0592bb967d1f9648a1157eee2f8af21', '12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc', '8cd88930d3be5557be0777f384eecff0a36a7011850fe613fc0a68178bfd5b01', '{"enable_tracker": true, "frame_stride": 1}'::jsonb, 'COMPLETED', 1.0, 1436, 1436, NULL, NULL, '{}'::jsonb, false, 'FULL', '2026-10-02 07:42:49.120893', '2026-10-02 07:51:04.886033')
ON CONFLICT (id) DO NOTHING;

-- 5. Table: artifacts
INSERT INTO artifacts (id, session_id, kind, relpath, sha256, created_at, expires_at)
VALUES
  ('art-01-crowd6-dataset', 'session-01-crowd6', 'DATASET_EXPORT', 'dataset_export/a914bc97-61a1-4840-ab7d-6c20c78afa0f/3800e5c4-f923-47aa-b6c4-705d9e23aa39.json', '006d5d3fc0d12e776d14e0d24757f9dee3de17d9f9d613787edc32e05d1fad63', '2026-10-02 04:00:26.619904', NULL),
  ('art-01-crowd6-heatmap', 'session-01-crowd6', 'HEATMAP', 'heatmap/a914bc97-61a1-4840-ab7d-6c20c78afa0f/0c818563-a823-4eb0-82f3-1c89ef70ab50.png', 'e72ba965aa061425506fac90efe537477510be37a7d45663a8fced5308f24e01', '2026-10-02 04:00:27.357116', NULL),
  ('art-02-crowd-dataset', 'session-02-crowd', 'DATASET_EXPORT', 'dataset_export/c12a71c0-4884-438b-9c2e-2b77613cbd83/aada10a3-fd95-4691-96cc-d368be690fa5.json', '0523c57a45d87d528b45b24653614f6d4c693e0758da3828c385db9bc4b82bc7', '2026-10-02 07:23:45.349201', NULL),
  ('art-02-crowd-heatmap', 'session-02-crowd', 'HEATMAP', 'heatmap/c12a71c0-4884-438b-9c2e-2b77613cbd83/c36ecc96-ad95-43b3-89c1-e27c2fba3d9f.png', '9cefe145541a743e51640561872cd7c7aa1e8afdc4e1f7b3bbef27891b74c840', '2026-10-02 07:23:45.833441', NULL),
  ('art-03-150-dataset', 'session-03-150', 'DATASET_EXPORT', 'dataset_export/8fe5393f-d235-4420-b072-285d479ec03f/a44f7fd5-dc3c-41c0-99fa-087ccf768d86.json', '1195fc0bd9f398ffa7b609847751d9a374ad7c3d3f09fbc661bbb661797bee06', '2026-10-02 07:51:04.153611', NULL),
  ('art-03-150-heatmap', 'session-03-150', 'HEATMAP', 'heatmap/8fe5393f-d235-4420-b072-285d479ec03f/e79476b8-a78e-4bf6-b98e-d7cc7bdac7d6.png', 'bb04d84b1892d6641a5f3450ddf6ad3614deb1df101bc6acb081ab13abf68eaf', '2026-10-02 07:51:04.879455', NULL)
ON CONFLICT (id) DO NOTHING;

-- 6. Table: audit_log
INSERT INTO audit_log (id, action, entity_type, entity_id, details, timestamp)
VALUES
  ('audit-0001', 'SESSION_PURGED', 'session', '84b669e2-b613-4aa5-90c9-eefc474b3e3c', '{"purged_at": "2026-10-02T07:10:04.928622"}'::jsonb, '2026-10-02 07:10:04.931118')
ON CONFLICT (id) DO NOTHING;

COMMIT;
