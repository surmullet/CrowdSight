"""Parking-space occupancy model integration contracts."""

from crowdsight.parking.adapter import (
    ParkingModelProfile,
    ParkingOccupancyModel,
    load_parking_model_profile,
    validate_parking_predictions,
    verify_parking_checkpoint,
)

__all__ = [
    "ParkingModelProfile",
    "ParkingOccupancyModel",
    "load_parking_model_profile",
    "validate_parking_predictions",
    "verify_parking_checkpoint",
]
