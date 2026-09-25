"""Person detector and tracker adapters."""

from crowdsight.detection.adapter import (
    PersonDetector,
    PersonDetectorProfile,
    PersonTracker,
    UltralyticsPersonDetector,
    UltralyticsPersonTracker,
)
from crowdsight.detection.profile_loader import (
    load_person_detector_profile,
    load_person_tracker,
)

__all__ = [
    "PersonDetector",
    "PersonDetectorProfile",
    "PersonTracker",
    "UltralyticsPersonDetector",
    "UltralyticsPersonTracker",
    "load_person_detector_profile",
    "load_person_tracker",
]
