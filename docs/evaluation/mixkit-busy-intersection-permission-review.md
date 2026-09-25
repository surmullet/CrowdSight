# Mixkit intersection clip permission review

**Record ID:** `mixkit-busy-intersection-noncommercial-evaluation-2026-09-25`  
**Reviewer:** Product lead (user authorization; role-based reviewer ID: `product-lead-user-authorization-2026-09-25`)  
**Decision date:** 2026-09-25  
**Approved scope:** Noncommercial internal model evaluation and manual/SAM-assisted annotation of the already selected 30-frame sample.  
**Not approved by this record:** Model training, commercial deployment, publication/redistribution of the video or extracted frames, or any use beyond the named evaluation.

## Source and license evidence

- Clip: [Busy intersection aerial view](https://mixkit.co/free-stock-video/busy-intersection-aerial-view-60/)
- Source page: `https://mixkit.co/free-stock-video/busy-intersection-aerial-view-60/`
- License page: `https://mixkit.co/license/modal/videoFree/`
- Terms page: `https://mixkit.co/terms/`
- Review basis checked 2026-09-25: the source page identifies this clip as being under the Mixkit Stock Video Free License. Mixkit's Free License page says items may be used in commercial and noncommercial projects and permits downloading, copying, modification, distribution, public performance, and broadcast, subject to the User Terms. The User Terms also restrict particular uses and explain that third-party components may have separate rights.
- User authorization: the product lead requested that an alternative video be found and specified noncommercial use. This record applies that authorization to the exact Mixkit clip and the limited scope above.

## Handling conditions

1. Keep the original video, extracted frames, SAM proposals, reviewed labels, and prediction files in private local/approved artifact storage. Do not commit or publicly distribute them.
2. Use annotations only for the named internal evaluation. SAM output remains pseudo-label material until a human reviewer completes and signs off each selected frame.
3. Do not use this clip as a training source or infer that this record establishes permission for another Mixkit asset, a different use, identifiable-person processing, or commercial deployment.
4. Keep the independent model-training-source review separate. This permission decision does not establish that the clip is independent from all upstream pretraining data, and does not make any resulting metrics a verified held-out result.
5. Recheck the source/license/terms pages before expanding the scope or redistributing any derived artifact.

This is an operational project permission record based on the named public terms and the product lead's instruction. It is not a legal opinion and does not resolve third-party rights beyond the license statements reviewed above.
