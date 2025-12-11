# DCIM Bulk Upload CSV Templates

This folder contains template CSV files for bulk uploading DCIM entities. All templates use existing locations and buildings from the seed data.

## Available Templates

### 1. `devices.csv`
Template for bulk uploading device entities.

**Required Columns:**
- `name` - Device name (unique per device)
- `serial_no` - Serial number
- `position` - Position in rack (U, integer >= 0)
- `face` - Device face: `front` or `rear`
- `status` - Device status (e.g., `active`, `inactive`, `maintenance`)
- `devicetype_name` - Device type name (must exist or be created first)
- `location_name` - Location name (must exist: Mumbai, Chennai, or NDR)
- `building_name` - Building name (must exist: MUM-B1, MUM-B2, CHE-B1, CHE-B2, NDR-B1, NDR-B2)
- `rack_name` - Rack name (must exist or be created first)
- `datacenter_name` - Datacenter name (must exist or be created first)
- `wing_name` - Wing name (must exist or be created first)
- `floor_name` - Floor name (must exist or be created first)
- `make_name` - Make/manufacturer name (must exist or be created first)
- `model_name` - Model name (must exist or be created first)
- `ip` - IP address
- `po_number` - Purchase order number
- `asset_user` - Asset user status (e.g., `in use`, `instock`, `na`)
- `asset_owner_name` - Asset owner name (must exist or be created first)
- `application_name` - Application name (must exist or be created first)
- `warranty_start_date` - Warranty start date (YYYY-MM-DD)
- `warranty_end_date` - Warranty end date (YYYY-MM-DD)
- `amc_start_date` - AMC start date (YYYY-MM-DD)
- `amc_end_date` - AMC end date (YYYY-MM-DD)
- `description` - Device description

**Note:** The `space_required` field is automatically calculated from the model height and should not be included in the CSV.

**Usage:**
```bash
# Upload via API with entity_type=devices
POST /api/dcim/bulk-upload?entity_type=devices&skip_errors=false
```

---

### 2. `racks.csv`
Template for bulk uploading rack entities.

**Required Columns:**
- `name` - Rack name (must be unique)
- `location_name` - Location name (must exist)
- `building_name` - Building name (must exist)
- `wing_name` - Wing name (must exist)
- `floor_name` - Floor name (must exist)
- `datacenter_name` - Datacenter name (must exist)
- `status` - Rack status (e.g., `active`, `inactive`, `maintenance`)
- `height` - Rack height in U (integer > 0, typically 42, 45, 48)
- `description` - Rack description

**Usage:**
```bash
# Upload via API with entity_type=racks
POST /api/dcim/bulk-upload?entity_type=racks&skip_errors=false
```

---

### 3. `entity_wfd.csv`
Template for bulk uploading hierarchical entities: Wings, Floors, and Datacenters.

**Required Columns:**
- `location_name` - Location name (must exist)
- `building_name` - Building name (must exist)
- `wing_name` - Wing name (will be created, must be unique within location+building)
- `floor_name` - Floor name (will be created, must be unique within location+building+wing)
- `datacenter_name` - Datacenter name (will be created, must be unique within location+building+wing+floor)
- `description` - Description for all three entities

**Processing Order:**
1. Wings are processed first
2. Floors are processed second (depend on wings)
3. Datacenters are processed last (depend on floors)

**Usage:**
```bash
# Upload via API with entity_type=entity_wfd
POST /api/dcim/bulk-upload?entity_type=entity_wfd&skip_errors=false
```

---

### 4. `entity_asset_details.csv`
Template for bulk uploading Asset Owners and Applications.

**Required Columns:**
- `asset_owner_name` - Asset owner name (will be created, must be unique within location)
- `location_name` - Location name (must exist)
- `application_name` - Application name (will be created, must be unique within asset owner)
- `description` - Description for both entities

**Processing Order:**
1. Asset Owners are processed first
2. Applications are processed second (depend on asset owners)

**Usage:**
```bash
# Upload via API with entity_type=entity_asset_details
POST /api/dcim/bulk-upload?entity_type=entity_asset_details&skip_errors=false
```

---

### 5. `entity_devicetypes.csv`
Template for bulk uploading Makes, Device Types, and Models.

**Required Columns:**
- `make_name` - Make/manufacturer name (will be created, must be unique)
- `devicetype_name` - Device type name (will be created, must be unique)
- `model_name` - Model name (will be created, must be unique)
- `height` - Model height in U (integer > 0)
- `description` - Description for all three entities

**Processing Order:**
1. Makes are processed first
2. Device Types are processed second (depend on makes)
3. Models are processed last (depend on makes and device types)

**Usage:**
```bash
# Upload via API with entity_type=entity_devicetypes
POST /api/dcim/bulk-upload?entity_type=entity_devicetypes&skip_errors=false
```

---

## Important Notes

### Unique Constraints
The following entities have unique name constraints:
- **Location**: `name` must be unique
- **Building**: `name` must be unique
- **Rack**: `name` must be unique
- **Make**: `name` must be unique
- **Model**: `name` must be unique
- **DeviceType**: `name` must be unique

### Existing Seed Data
All templates use existing locations and buildings from seed data:
- **Locations**: Mumbai, Chennai, NDR
- **Buildings**: MUM-B1, MUM-B2, CHE-B1, CHE-B2, NDR-B1, NDR-B2

### Upload Order
For a complete setup, upload in this order:
1. `entity_devicetypes.csv` - Creates makes, device types, and models
2. `entity_asset_details.csv` - Creates asset owners and applications
3. `entity_wfd.csv` - Creates wings, floors, and datacenters (if needed)
4. `racks.csv` - Creates racks
5. `devices.csv` - Creates devices (requires all above entities to exist)

### Error Handling
- Set `skip_errors=true` to continue processing remaining rows on error
- Set `skip_errors=false` to stop on first error (default)
- All errors are reported in the email sent after processing

### Date Format
All date fields must be in `YYYY-MM-DD` format (e.g., `2024-01-01`).

### Column Name Variations
The bulk upload router supports various column name formats (case-insensitive):
- `hostname`, `host name`, `device name` → `name`
- `rack no`, `rack_no`, `rack number` → `rack_name`
- `manufacturer`, `make` → `make_name`
- `ip address`, `ip_address` → `ip`
- And many more (see `CSV_COLUMN_MAPPING` in `bulk_upload_router.py`)

