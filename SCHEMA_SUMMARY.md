# DCIM Database Schema Summary

This document describes the complete database schema created by the Alembic migrations.

## Schema Overview

The schema is organized into several functional areas:
1. **User Management & Authentication**
2. **Location Hierarchy** (Location → Building → Wing → Floor → Datacenter)
3. **Device Management** (Devices, Device Types, Manufacturers, Models)
4. **Rack Management**
5. **Asset & Application Management**
6. **Audit Logging**
7. **RBAC (Role-Based Access Control)**

---

## 1. User Management & Authentication

### `dcim_users`
- **Primary Key**: `user_id` (Integer)
- **Columns**:
  - `user_id` (Integer, PK)
  - `username` (String(64), unique, not null)
  - `email` (String(255), unique, not null)
  - `full_name` (String(255))
  - `is_active` (Boolean, default: true)
  - `created_at` (DateTime, default: CURRENT_TIMESTAMP)
  - `last_login` (DateTime, nullable)

### `dcim_users_token`
- **Primary Key**: `token_id` (Integer, autoincrement)
- **Foreign Keys**:
  - `user_id` → `dcim_users.user_id`
- **Columns**:
  - `token_id` (Integer, PK, autoincrement)
  - `token_key` (String(255), unique, not null)
  - `user_id` (Integer, FK → dcim_users.user_id, not null)
  - `created` (DateTime, default: CURRENT_TIMESTAMP)
  - `expires` (DateTime, nullable)
  - `last_used` (DateTime, nullable)

---

## 2. Location Hierarchy

The location hierarchy follows this structure:
**Location** → **Building** → **Wing** → **Floor** → **Datacenter**

### `dcim_location`
- **Primary Key**: `location_id` (Integer)
- **Columns**:
  - `location_id` (Integer, PK, autoincrement)
  - `name` (String(128), unique, not null)

### `dcim_building`
- **Primary Key**: `building_id` (Integer)
- **Foreign Keys**:
  - `location_id` → `dcim_location.location_id`
- **Columns**:
  - `building_id` (Integer, PK, autoincrement)
  - `name` (String(128), unique, not null)
  - `status` (String(32), default: 'active', not null)
  - `location_id` (Integer, FK → dcim_location.location_id, not null)

### `dcim_wing`
- **Primary Key**: `wings_id` (Integer)
- **Foreign Keys**:
  - `location_id` → `dcim_location.location_id`
  - `building_id` → `dcim_building.building_id`
- **Columns**:
  - `wings_id` (Integer, PK, autoincrement)
  - `name` (String(128), unique, not null)
  - `location_id` (Integer, FK → dcim_location.location_id, not null)
  - `building_id` (Integer, FK → dcim_building.building_id, not null)

### `dcim_floor`
- **Primary Key**: `floor_id` (Integer)
- **Foreign Keys**:
  - `location_id` → `dcim_location.location_id`
  - `building_id` → `dcim_building.building_id`
  - `wings_id` → `dcim_wing.wings_id`
- **Columns**:
  - `floor_id` (Integer, PK, autoincrement)
  - `name` (String(128), unique, not null)
  - `location_id` (Integer, FK → dcim_location.location_id, not null)
  - `building_id` (Integer, FK → dcim_building.building_id, not null)
  - `wings_id` (Integer, FK → dcim_wing.wings_id, not null)

### `dcim_datacenter`
- **Primary Key**: `dc_id` (Integer)
- **Foreign Keys**:
  - `location_id` → `dcim_location.location_id`
  - `building_id` → `dcim_building.building_id`
  - `wings_id` → `dcim_wing.wings_id`
  - `floor_id` → `dcim_floor.floor_id`
- **Columns**:
  - `dc_id` (Integer, PK, autoincrement)
  - `name` (String(128), unique, not null)
  - `location_id` (Integer, FK → dcim_location.location_id, not null)
  - `building_id` (Integer, FK → dcim_building.building_id, not null)
  - `wings_id` (Integer, FK → dcim_wing.wings_id, not null)
  - `floor_id` (Integer, FK → dcim_floor.floor_id, not null)

---

## 3. Rack Management

### `dcim_rack`
- **Primary Key**: `id` (Integer)
- **Foreign Keys**:
  - `building_id` → `dcim_building.building_id`
  - `location_id` → `dcim_location.location_id`
- **Columns**:
  - `id` (Integer, PK, autoincrement)
  - `name` (String(128), unique, not null)
  - `building_id` (Integer, FK → dcim_building.building_id, not null)
  - `location_id` (Integer, FK → dcim_location.location_id, not null)
  - `status` (String(32), default: 'active', not null)
  - `width` (Integer, nullable)
  - `height` (Integer, nullable)
  - `space_used` (Integer, default 0, not null) - consumed rack units
  - `space_available` (Integer, default 0, not null) - remaining rack units
  - `created_at` (DateTime, default: CURRENT_TIMESTAMP, not null)
  - `last_updated` (DateTime, default: CURRENT_TIMESTAMP, not null)

---

## 4. Device Management

### `dcim_device`
- **Primary Key**: `id` (Integer)
- **Foreign Keys** (added in migration 017):
  - `devicetype_id` → `dcim_device_types.id`
  - `manufactures_id` → `dcim_manufactures.id`
  - `application_mapped_id` → `dcim_applications_mapped.id`
- **Other Foreign Keys**:
  - `building_id` → `dcim_building.building_id`
  - `location_id` → `dcim_location.location_id`
  - `rack_id` → `dcim_rack.id`
  - `dc_id` → `dcim_datacenter.dc_id`
  - `wings_id` → `dcim_wing.wings_id`
  - `floor_id` → `dcim_floor.floor_id`
- **Columns**:
  - `id` (Integer, PK)
  - `device_name` (String(255), not null)
  - `serial_no` (String(255), nullable)
  - `position` (Integer, nullable) - Rack start unit
  - `face` (String(16), not null) - front / rear
  - `status` (String(32), default: 'active', not null)
  - `devicetype_id` (Integer, FK → dcim_device_types.id, nullable)
  - `building_id` (Integer, FK → dcim_building.building_id, not null)
  - `location_id` (Integer, FK → dcim_location.location_id, not null)
  - `rack_id` (Integer, FK → dcim_rack.id, nullable)
  - `dc_id` (Integer, FK → dcim_datacenter.dc_id, nullable)
  - `wings_id` (Integer, FK → dcim_wing.wings_id, nullable)
  - `floor_id` (Integer, FK → dcim_floor.floor_id, nullable)
  - `manufactures_id` (Integer, FK → dcim_manufactures.id, nullable)
  - `ip` (String(64), nullable)
  - `po_number` (String(128), nullable)
  - `asset_user` (String(32), default: 'instock', not null) - instock / in use / na
  - `application_mapped_id` (Integer, FK → dcim_applications_mapped.id, nullable)
  - `warranty_start_date` (Date, nullable)
  - `warranty_end_date` (Date, nullable)
  - `amc_start_date` (Date, nullable)
  - `amc_end_date` (Date, nullable)
  - `space_required` (Integer, nullable) - for height calculation
  - `created_at` (DateTime, default: CURRENT_TIMESTAMP, not null)
  - `last_updated` (DateTime, default: CURRENT_TIMESTAMP, not null)

### `dcim_device_types`
- **Primary Key**: `device_name` (String(255))
- **Foreign Keys**:
  - `manufactures_id` → `dcim_manufactures.id` (ondelete: SET NULL)
  - `models_name` → `dcim_models.name` (ondelete: SET NULL)
- **Columns**:
  - `id` (Integer, unique)
  - `device_name` (String(255), PK)
  - `manufactures_id` (Integer, FK → dcim_manufactures.id, nullable)
  - `models_name` (String, FK → dcim_models.name, nullable)

### `dcim_manufactures`
- **Primary Key**: `id` (Integer)
- **Columns**:
  - `id` (Integer, PK)
  - `manu_name` (String(255), unique, not null)

### `dcim_models`
- **Primary Key**: `name` (String(128))
- **Foreign Keys**:
  - `manufacturers_id` → `dcim_manufactures.id` (ondelete: CASCADE)
- **Columns**:
  - `id` (Integer, not null)
  - `name` (String(128), PK)
  - `manufacturers_id` (Integer, FK → dcim_manufactures.id, not null)

---

## 5. Asset & Application Management

### `dcim_asset_owner`
- **Primary Key**: `owner_name` (String(255))
- **Foreign Keys**:
  - `location_id` → `dcim_location.location_id`
- **Columns**:
  - `id` (Integer, unique)
  - `owner_name` (String(255), PK, not null)
  - `location_id` (Integer, FK → dcim_location.location_id, nullable)

### `dcim_applications_mapped`
- **Primary Key**: `application_mapped_name` (String(255))
- **Foreign Keys**:
  - `asset_owner_id` → `dcim_asset_owner.id`
- **Columns**:
  - `id` (Integer, PK)
  - `application_mapped_name` (String(255), PK, not null)
  - `asset_owner_id` (Integer, FK → dcim_asset_owner.id, nullable)

### `dcim_environment`
- **Primary Key**: `id` (Integer)
- **Columns**:
  - `id` (Integer, PK)
  - `env_name` (String(128), unique, not null)
  - `env_code` (String(64), unique, not null)

---

## 6. Audit Logging

### `dcim_audit_logs`
- **Primary Key**: `id` (Integer)
- **Foreign Keys**:
  - `user_id` → `dcim_users.user_id`
- **Columns**:
  - `id` (Integer, PK)
  - `time` (DateTime, default: CURRENT_TIMESTAMP, not null)
  - `user_id` (Integer, FK → dcim_users.user_id, nullable)
  - `action` (String(128), not null)
  - `type` (String(128), not null)
  - `object_id` (Integer, nullable)
  - `message` (Text, nullable)

---

## 7. RBAC (Role-Based Access Control)

### `dcim_rbac_roles`
- **Primary Key**: `id` (Integer)
- **Columns**:
  - `id` (Integer, PK)
  - `name` (String(100), not null)
  - `code` (String(50), unique, not null)
  - `description` (String(255), nullable)
  - `is_active` (Boolean, default: true, not null)

### `dcim_rbac_user_roles`
- **Primary Key**: `id` (Integer)
- **Foreign Keys**:
  - `user_id` → `dcim_users.user_id`
  - `role_id` → `dcim_rbac_roles.id`
- **Columns**:
  - `id` (Integer, PK)
  - `user_id` (Integer, FK → dcim_users.user_id, not null)
  - `role_id` (Integer, FK → dcim_rbac_roles.id, not null)

### `dcim_modules`
- **Primary Key**: `id` (Integer)
- **Columns**:
  - `id` (Integer, PK)
  - `header_name` (String(200), not null)
  - `icon` (String(255), nullable)
  - `code` (String(100), unique, not null)
  - `sort_order` (Integer, nullable)

### `dcim_submodules`
- **Primary Key**: `id` (Integer)
- **Foreign Keys**:
  - `module_id` → `dcim_modules.id`
- **Columns**:
  - `id` (Integer, PK)
  - `module_id` (Integer, FK → dcim_modules.id, not null)
  - `display_name` (String(200), not null)
  - `page_url` (String(255), not null)
  - `icon` (String(255), nullable)
  - `code` (String(100), unique, not null)
  - `sort_order` (Integer, nullable)

### `dcim_rbac_role_submodule_access`
- **Composite Key**: `role_id` + `submodule_id`
- **Foreign Keys**:
  - `role_id` → `dcim_rbac_roles.id`
  - `submodule_id` → `dcim_submodules.id`
- **Columns**:
  - `role_id` (Integer, FK → dcim_rbac_roles.id, not null)
  - `submodule_id` (Integer, FK → dcim_submodules.id, not null)
  - `can_view` (Boolean, default: true, not null)

---

## Migration Order

The migrations are applied in this order:

1. `001_create_dcim_users` - User management
2. `002_create_dcim_users_token` - Authentication tokens
3. `003_create_dcim_locations` - Locations
4. `004_create_dcim_buildings` - Buildings
5. `005_create_dcim_wings` - Wings
6. `006_create_dcim_floors` - Floors
7. `007_create_dcim_datacenters` - Datacenters
8. `008_create_dcim_racks` - Racks
9. `009_create_dcim_devices` - Devices (FKs added later in 017)
10. `010_create_dcim_device_types` - Device types
11. `011_create_dcim_manufactures` - Manufacturers
12. `012_create_dcim_models` - Models
13. `013_create_dcim_audit_logs` - Audit logs
14. `014_create_dcim_environment` - Environments
15. `015_create_dcim_asset_owner` - Asset owners
16. `016_create_dcim_applications_mapped` - Application mappings
17. `017_create_dcim_rbac_roles` - RBAC roles (also adds deferred FKs to dcim_device)
18. `018_create_dcim_rbac_user_roles` - User-role assignments
19. `019_create_dcim_modules` - Modules
20. `020_create_dcim_submodules` - Submodules
21. `021_create_dcim_rbac_role_submodule_access` - Role-submodule permissions
22. `022_add_rack_space_usage_columns` - Rack capacity tracking

---

## Key Relationships

### Location Hierarchy
```
dcim_location (root)
  └── dcim_building
      └── dcim_wing
          └── dcim_floor
              └── dcim_datacenter
```

### Device Relationships
```
dcim_device
  ├── References: dcim_device_types, dcim_manufactures, dcim_applications_mapped
  ├── Location: dcim_location, dcim_building, dcim_wing, dcim_floor, dcim_datacenter
  └── Rack: dcim_rack
```

### RBAC Structure
```
dcim_users
  └── dcim_rbac_user_roles
      └── dcim_rbac_roles
          └── dcim_rbac_role_submodule_access
              └── dcim_submodules
                  └── dcim_modules
```

---

## Notes

- All location-related tables use integer IDs as primary keys (location_id, building_id, wings_id, floor_id, dc_id)
- Foreign keys to `dcim_device_types`, `dcim_manufactures`, and `dcim_applications_mapped` are added in migration 017 (after those tables are created)
- The schema uses Oracle database (based on the connection string format)
- Timestamps use `CURRENT_TIMESTAMP` as default values
- Several tables have nullable foreign keys to support optional relationships

