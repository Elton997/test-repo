"""
Shared listing-related enums kept lightweight so routers can import them
without pulling in the heavier helper modules that touch SQLAlchemy models.
"""
from enum import Enum


class ListingType(str, Enum):
    racks = "racks"
    devices = "devices"
    device_types = "device_types"
    locations = "locations"
    buildings = "buildings"
    wings = "wings"
    floors = "floors"
    datacenters = "datacenters"
    asset_owner = "asset_owner"
    makes = "makes"
    models = "models"
    applications = "applications"

