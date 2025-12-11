# app/models/entity_models.py
"""
DCIM entity models matching Alembic migrations.
All tables use 'dcim' schema with lowercase column names.
"""
from datetime import datetime, date

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date, Boolean
from sqlalchemy.orm import relationship

from app.db.base import Base


# -------------------------------------------------------
# LOCATION
# Migration: 003_create_dcim_location
# -------------------------------------------------------
class Location(Base):
    __tablename__ = "dcim_location"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)

    # Relationships
    buildings = relationship(
        "Building",
        back_populates="location",
        cascade="all, delete-orphan",
    )
    wings = relationship(
        "Wing",
        back_populates="location",
        cascade="all, delete-orphan",
    )
    floors = relationship(
        "Floor",
        back_populates="location",
        cascade="all, delete-orphan",
    )
    datacenters = relationship(
        "Datacenter",
        back_populates="location",
        cascade="all, delete-orphan",
    )
    racks = relationship(
        "Rack",
        back_populates="location",
        cascade="all, delete-orphan",
    )
    devices = relationship(
        "Device",
        back_populates="location",
        cascade="all, delete-orphan",
    )
    asset_owners = relationship(
        "AssetOwner",
        back_populates="location",
        cascade="all, delete-orphan",
    )


# -------------------------------------------------------
# BUILDING
# Migration: 004_create_dcim_building
# -------------------------------------------------------
class Building(Base):
    __tablename__ = "dcim_building"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    status = Column(String(255), nullable=False, default="active")
    location_id = Column(
        Integer,
        ForeignKey("dcim.dcim_location.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description = Column(String(255), nullable=True)

    # Relationships
    location = relationship("Location", back_populates="buildings")
    wings = relationship(
        "Wing",
        back_populates="building",
        cascade="all, delete-orphan",
    )
    floors = relationship(
        "Floor",
        back_populates="building",
        cascade="all, delete-orphan",
    )
    datacenters = relationship(
        "Datacenter",
        back_populates="building",
        cascade="all, delete-orphan",
    )
    racks = relationship(
        "Rack",
        back_populates="building",
        cascade="all, delete-orphan",
    )
    devices = relationship(
        "Device",
        back_populates="building",
        cascade="all, delete-orphan",
    )


# -------------------------------------------------------
# WING
# Migration: 005_create_dcim_wing
# -------------------------------------------------------
class Wing(Base):
    __tablename__ = "dcim_wing"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    location_id = Column(
        Integer,
        ForeignKey("dcim.dcim_location.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building_id = Column(
        Integer,
        ForeignKey("dcim.dcim_building.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description = Column(String(255), nullable=True)

    # Relationships
    location = relationship("Location", back_populates="wings")
    building = relationship("Building", back_populates="wings")
    floors = relationship(
        "Floor",
        back_populates="wing",
        cascade="all, delete-orphan",
    )
    datacenters = relationship(
        "Datacenter",
        back_populates="wing",
        cascade="all, delete-orphan",
    )
    racks = relationship(
        "Rack",
        back_populates="wing",
        cascade="all, delete-orphan",
    )
    devices = relationship(
        "Device",
        back_populates="wing",
        cascade="all, delete-orphan",
    )


# -------------------------------------------------------
# FLOOR
# Migration: 006_create_dcim_floor
# -------------------------------------------------------
class Floor(Base):
    __tablename__ = "dcim_floor"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    location_id = Column(
        Integer,
        ForeignKey("dcim.dcim_location.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building_id = Column(
        Integer,
        ForeignKey("dcim.dcim_building.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    wing_id = Column(
        Integer,
        ForeignKey("dcim.dcim_wing.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description = Column(String(255), nullable=True)

    # Relationships
    location = relationship("Location", back_populates="floors")
    building = relationship("Building", back_populates="floors")
    wing = relationship("Wing", back_populates="floors")
    datacenters = relationship(
        "Datacenter",
        back_populates="floor",
        cascade="all, delete-orphan",
    )
    racks = relationship(
        "Rack",
        back_populates="floor",
        cascade="all, delete-orphan",
    )
    devices = relationship(
        "Device",
        back_populates="floor",
        cascade="all, delete-orphan",
    )


# -------------------------------------------------------
# DATACENTER
# Migration: 007_create_dcim_datacenter
# -------------------------------------------------------
class Datacenter(Base):
    __tablename__ = "dcim_datacenter"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    location_id = Column(
        Integer,
        ForeignKey("dcim.dcim_location.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building_id = Column(
        Integer,
        ForeignKey("dcim.dcim_building.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    wing_id = Column(
        Integer,
        ForeignKey("dcim.dcim_wing.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    floor_id = Column(
        Integer,
        ForeignKey("dcim.dcim_floor.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description = Column(String(255), nullable=True)

    # Relationships
    location = relationship("Location", back_populates="datacenters")
    building = relationship("Building", back_populates="datacenters")
    wing = relationship("Wing", back_populates="datacenters")
    floor = relationship("Floor", back_populates="datacenters")
    racks = relationship(
        "Rack",
        back_populates="datacenter",
        cascade="all, delete-orphan",
    )
    devices = relationship(
        "Device",
        back_populates="datacenter",
        cascade="all, delete-orphan",
    )


# -------------------------------------------------------
# RACK
# Migration: 008_create_dcim_rack
# -------------------------------------------------------
class Rack(Base):
    __tablename__ = "dcim_rack"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    building_id = Column(
        Integer,
        ForeignKey("dcim.dcim_building.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id = Column(
        Integer,
        ForeignKey("dcim.dcim_location.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    wing_id = Column(
        Integer,
        ForeignKey("dcim.dcim_wing.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    floor_id = Column(
        Integer,
        ForeignKey("dcim.dcim_floor.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    datacenter_id = Column(
        Integer,
        ForeignKey("dcim.dcim_datacenter.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(255), nullable=False, default="active")
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    space_used = Column(Integer, nullable=False, default=0)
    space_available = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_updated = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    description = Column(String(255), nullable=True)

    # Relationships
    building = relationship("Building", back_populates="racks")
    location = relationship("Location", back_populates="racks")
    wing = relationship("Wing", back_populates="racks")
    floor = relationship("Floor", back_populates="racks")
    datacenter = relationship("Datacenter", back_populates="racks")
    devices = relationship(
        "Device",
        back_populates="rack",
        cascade="all, delete-orphan",
    )


# -------------------------------------------------------
# MAKE
# Migration: 009_create_dcim_make
# -------------------------------------------------------
class Make(Base):
    __tablename__ = "dcim_make"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)

    # Relationships
    models = relationship(
        "Model",
        back_populates="make",
        cascade="all, delete-orphan",
    )
    device_types = relationship(
        "DeviceType",
        back_populates="make",
        cascade="all, delete-orphan",
    )
    devices = relationship(
        "Device",
        back_populates="make",
        cascade="all, delete-orphan",
    )


# -------------------------------------------------------
# MODEL (formerly MODULE)
# Migration: 010_create_dcim_model
# -------------------------------------------------------
class Model(Base):
    __tablename__ = "dcim_model"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    make_id = Column(
        Integer,
        ForeignKey("dcim.dcim_make.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_type_id = Column(
        Integer,
        ForeignKey("dcim.dcim_device_type.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    height = Column(Integer, nullable=False)
    description = Column(String(255), nullable=True)

    # Model images
    front_image_path = Column(String(512), nullable=True)
    rear_image_path = Column(String(512), nullable=True)

    # Relationships
    make = relationship("Make", back_populates="models")
    device_type = relationship("DeviceType", back_populates="models")


# -------------------------------------------------------
# DEVICE TYPE
# Migration: 011_create_dcim_device_type
# -------------------------------------------------------
class DeviceType(Base):
    __tablename__ = "dcim_device_type"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    make_id = Column(
        Integer,
        ForeignKey("dcim.dcim_make.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description = Column(String(255), nullable=True)

    # Relationships
    make = relationship("Make", back_populates="device_types")
    models = relationship(
        "Model",
        back_populates="device_type",
        cascade="all, delete-orphan",
    )
    devices = relationship(
        "Device",
        back_populates="device_type",
        cascade="all, delete-orphan",
    )


# -------------------------------------------------------
# ASSET OWNER
# Migration: 012_create_dcim_asset_owner
# -------------------------------------------------------
class AssetOwner(Base):
    __tablename__ = "dcim_asset_owner"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    location_id = Column(
        Integer,
        ForeignKey("dcim.dcim_location.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    description = Column(String(255), nullable=True)

    # Relationships
    location = relationship("Location", back_populates="asset_owners")
    applications = relationship(
        "ApplicationMapped",
        back_populates="asset_owner",
        cascade="all, delete-orphan",
    )


# -------------------------------------------------------
# APPLICATIONS MAPPED
# Migration: 013_create_dcim_applications_mapped
# -------------------------------------------------------
class ApplicationMapped(Base):
    __tablename__ = "dcim_applications_mapped"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    asset_owner_id = Column(
        Integer,
        ForeignKey("dcim.dcim_asset_owner.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    description = Column(String(255), nullable=True)

    # Relationships
    asset_owner = relationship("AssetOwner", back_populates="applications")
    devices = relationship(
        "Device",
        back_populates="application_mapped",
        cascade="all, delete-orphan",
    )


# -------------------------------------------------------
# DEVICE
# Migration: 014_create_dcim_device
# -------------------------------------------------------
class Device(Base):
    __tablename__ = "dcim_device"
    __table_args__ = {"schema": "dcim"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    serial_no = Column(String(255), nullable=True, index=True)
    position = Column(Integer, nullable=True)  # Rack start unit
    face_front = Column(Boolean, nullable=False, default=False)
    face_rear = Column(Boolean, nullable=False, default=False)
    status = Column(String(255), nullable=False, default="active")

    # Foreign Keys
    devicetype_id = Column(
        Integer,
        ForeignKey("dcim.dcim_device_type.id", ondelete="SET NULL"),
        nullable=True,
    )
    building_id = Column(
        Integer,
        ForeignKey("dcim.dcim_building.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id = Column(
        Integer,
        ForeignKey("dcim.dcim_location.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rack_id = Column(
        Integer,
        ForeignKey("dcim.dcim_rack.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dc_id = Column(
        Integer,
        ForeignKey("dcim.dcim_datacenter.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    wings_id = Column(
        Integer,
        ForeignKey("dcim.dcim_wing.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    floor_id = Column(
        Integer,
        ForeignKey("dcim.dcim_floor.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    make_id = Column(
        Integer,
        ForeignKey("dcim.dcim_make.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    ip = Column(String(255), nullable=True)
    po_number = Column(String(255), nullable=True)
    asset_user = Column(String(255), nullable=False, default="instock")

    applications_mapped_id = Column(
        Integer,
        ForeignKey("dcim.dcim_applications_mapped.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Warranty
    warranty_start_date = Column(Date, nullable=True)
    warranty_end_date = Column(Date, nullable=True)

    # AMC
    amc_start_date = Column(Date, nullable=True)
    amc_end_date = Column(Date, nullable=True)

    # Space required for height calculation
    space_required = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_updated = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    description = Column(String(255), nullable=True)

    # Relationships
    building = relationship("Building", back_populates="devices")
    location = relationship("Location", back_populates="devices")
    rack = relationship("Rack", back_populates="devices")
    datacenter = relationship("Datacenter", back_populates="devices")
    wing = relationship("Wing", back_populates="devices")
    floor = relationship("Floor", back_populates="devices")
    device_type = relationship("DeviceType", back_populates="devices")
    make = relationship("Make", back_populates="devices")
    application_mapped = relationship("ApplicationMapped", back_populates="devices")
