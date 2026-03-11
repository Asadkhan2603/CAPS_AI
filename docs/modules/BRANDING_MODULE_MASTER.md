# Branding Module Master

## Module Overview
This section provides a standardized summary for the module. Refer to the detailed sections below for full context.

## Responsibilities
- Core responsibilities are described in the detailed sections below.

## Components
- Primary backend endpoints, schemas, and UI surfaces are listed below.

## API Endpoints
- Refer to the API endpoint inventory in this document.

## Data Models
- Refer to the data model details in this document.

## Workflows
- Refer to the workflow and lifecycle sections below.

## Dependencies
- Refer to dependency notes in this document.

## Known Limitations
- Refer to current limitations described below.

## Improvements
- Refer to improvement opportunities listed below.


## Module Tree

```text
Branding Module
|-- Global Logo Upload
|-- Branding Settings Record
|-- Sidebar Logo Rendering
`-- File Storage Under uploads/branding
```

## Internal Entity And Flow Tree

```text
Admin logo upload
`-- File write
    `-- Settings metadata update
        `-- Frontend logo fetch and display
```

Primary implementation sources:

- [branding.py](/backend/app/api/v1/endpoints/branding.py)
- [Sidebar.jsx](/frontend/src/components/layout/Sidebar.jsx)
- [apiClient.js](/frontend/src/services/apiClient.js)

Adjacent but separate branding-related references:

- [ThemeContext.jsx](/frontend/src/context/ThemeContext.jsx)
- [auth.py](/backend/app/api/v1/endpoints/auth.py)
- [Topbar.jsx](/frontend/src/components/layout/Topbar.jsx)
- [ProfilePage.jsx](/frontend/src/pages/ProfilePage.jsx)

This document describes the Branding Module as implemented today.

In CAPS AI, branding is currently a narrow institutional-logo feature. It is not yet a full brand-management or theming subsystem.

## 1. Module Overview

The Branding Module provides shared university or institute logo support for the platform shell.

Current implemented capabilities:

1. store one global logo file
2. expose logo metadata
3. serve the current logo file
4. allow admins to replace the logo from the sidebar

Important implementation reality:

- branding is currently global, not tenant-specific
- there is only one active logo
- no color palette, typography, or institutional profile settings are persisted through this module
- dark or light mode is handled separately in the frontend theme context
- user avatars are handled separately in the auth or profile subsystem

The correct description of the current module is:

- `Branding Module = Global Logo Upload + Metadata + Delivery`

## 2. Branding Boundary

The current branding boundary is intentionally small.

### In scope today

- institutional logo upload
- institutional logo retrieval
- logo metadata storage in `settings`
- sidebar display of the institutional logo

### Out of scope today

- full theme customization
- per-user avatars
- per-role or per-campus branding
- text identity editing such as:
  - university name
  - short name
  - tagline
- color token customization
- favicon management
- login-page branding administration

This distinction matters because the UI visually contains branding-adjacent elements, but only one small part of them is actually configurable through the backend.

## 3. Data Model And Storage

## 3.1 File storage location

File:

- [branding.py](/backend/app/api/v1/endpoints/branding.py)

Logo files are stored on local disk under:

- `uploads/branding`

The module keeps only one active file by deleting any existing `logo.*` file before saving the replacement.

Saved naming convention:

- `logo.png`
- `logo.jpg`
- `logo.jpeg`
- `logo.webp`
- `logo.svg`

depending on the uploaded suffix

This means the filesystem is the actual content store.

## 3.2 Metadata storage

Branding metadata is stored in:

- `settings`

Current key used:

- `key = "branding_logo"`

Persisted metadata fields:

- `key`
- `filename`
- `mime_type`
- `size_bytes`
- `updated_at`
- `updated_by`

Important note:

- the system checks both metadata existence and file existence
- if either is missing, the module reports `has_logo = false`

This is a pragmatic dual-source consistency check.

## 3.3 Current constraints

Logo validation rules:

- allowed suffixes:
  - `.png`
  - `.jpg`
  - `.jpeg`
  - `.webp`
  - `.svg`
- maximum size:
  - `2 MB`
- empty uploads are rejected

There is no current validation for:

- image dimensions
- aspect ratio
- content safety
- SVG sanitization beyond file extension acceptance

## 4. Backend Logic Implemented

## 4.1 Logo metadata endpoint

Route:

- `GET /api/v1/branding/logo/meta`

Purpose:

- tell the frontend whether a logo exists
- expose last update timestamp and filename

Behavior:

- reads `settings` record with key `branding_logo`
- checks whether a `logo.*` file exists in `uploads/branding`
- returns:
  - `has_logo = false` if metadata or file is missing
  - otherwise:
    - `has_logo = true`
    - `updated_at`
    - `filename`

Access:

- public to authenticated clients through normal API routing

There is no explicit role gate on this route.

## 4.2 Logo file endpoint

Route:

- `GET /api/v1/branding/logo`

Purpose:

- serve the active institutional logo file

Behavior:

- resolves current `logo.*` file from disk
- returns `404` if missing
- serves file directly through `FileResponse`

This is the content-delivery endpoint used by the sidebar.

## 4.3 Logo upload endpoint

Route:

- `POST /api/v1/branding/logo`

Access:

- `require_roles(["admin"])`

Behavior:

1. validate suffix
2. read full upload into memory
3. reject empty upload
4. reject files larger than `2 MB`
5. create branding directory if missing
6. delete all existing `logo.*` files
7. save replacement file
8. upsert metadata in `settings`
9. return upload confirmation with timestamp

Stored side effects:

- local file replacement
- `settings.branding_logo` upsert

Current response fields:

- `message`
- `filename`
- `updated_at`

## 5. Frontend Implementation

## 5.1 Sidebar branding behavior

File:

- [Sidebar.jsx](/frontend/src/components/layout/Sidebar.jsx)

Current behavior:

- on mount, the sidebar calls:
  - `GET /branding/logo/meta`
- if `has_logo` is true:
  - constructs logo URL as `/api/v1/branding/logo?v=<updated_at>`
- if no logo exists:
  - shows placeholder panel:
    - `COLLEGE / UNIVERSITY LOGO`

This is the only major frontend consumer of the branding API today.

## 5.2 Admin upload UX

In the sidebar:

- admins get an `Upload Logo` button
- hidden file input accepts supported image types
- upload posts multipart form data to:
  - `POST /branding/logo`
- on success:
  - local sidebar state updates
  - `logoVersion` is refreshed
  - a success toast is shown

The cache-busting strategy is:

- append `?v=<updated_at>` or fallback timestamp

This is simple and effective.

## 5.3 Non-admin behavior

Non-admin users:

- can view the logo if available
- cannot upload or change it

This is enforced in the UI by hiding upload controls and in the backend by admin-only route access.

## 6. Adjacent But Separate Concerns

The codebase contains other UI identity surfaces that may look like branding but belong to different modules.

## 6.1 Theme mode

File:

- [ThemeContext.jsx](/frontend/src/context/ThemeContext.jsx)

Theme mode currently manages:

- light or dark preference
- local storage persistence

This is frontend personalization, not institutional branding.

## 6.2 User avatar handling

Files:

- [auth.py](/backend/app/api/v1/endpoints/auth.py)
- [Topbar.jsx](/frontend/src/components/layout/Topbar.jsx)
- [ProfilePage.jsx](/frontend/src/pages/ProfilePage.jsx)

Avatar support provides:

- per-user profile image upload
- protected avatar serving
- topbar and profile rendering

This is identity personalization, not global branding.

## 6.3 Hard-coded product identity

Current shell copy such as:

- `CAPS AI`
- `Control Center`

is still hard-coded in frontend layout components.

That means the Branding Module does not yet control the full visible institutional identity of the product.

## 7. Business Rules

### Rule 1: There is only one active institutional logo

Uploading a new logo replaces the previous one.

### Rule 2: Only admins can change branding

Logo upload is admin-only.

### Rule 3: Branding metadata must agree with file presence

The metadata endpoint requires both:

- settings record
- actual file

to report `has_logo = true`

### Rule 4: Branding is shell-level only

The current module affects shared layout branding, not page-specific themes or content branding.

## 8. Strengths Of Current Implementation

### Strong Area 1: Minimal and coherent scope

The module does one thing clearly:

- manage a global logo

### Strong Area 2: Metadata plus file consistency check

The API avoids false-positive branding state by requiring both database metadata and filesystem presence.

### Strong Area 3: Cache-busting strategy is already in place

Using the update timestamp in the logo URL prevents stale browser display after replacement.

### Strong Area 4: UI is embedded in the real application shell

Branding is not hidden behind a disconnected admin page. It is visible where users actually see it.

## 9. Gaps And Risks

### Gap 1: Local disk storage is not durable under scale

Branding files are stored on local disk:

- `uploads/branding`

Implications:

- pod or container replacement can lose the logo
- multi-instance deployments can diverge
- branding is not suitable for horizontally scaled ephemeral runtime without shared storage

### Gap 2: No audit logging for branding changes

The current upload flow does not emit an explicit audit event.

That is a weakness for an admin-controlled identity surface.

### Gap 3: No delete or reset route

There is no dedicated endpoint to:

- remove branding
- revert to default branding

### Gap 4: No branding management page

Branding is managed only through sidebar upload.

There is no dedicated admin page for:

- branding history
- preview
- metadata inspection
- rollback

### Gap 5: No theming or institutional text profile

The module cannot manage:

- university name
- short name
- slogan
- footer text
- official colors
- login page identity

### Gap 6: SVG acceptance may need stronger sanitation

The backend validates by extension only.

That may be acceptable in trusted admin-only workflows, but it is not a hardened content-safety posture.

## 10. Architectural Issues

### Issue 1: Branding is narrower than the visible product identity

The application shell contains multiple brand-like elements, but only the logo is backend-driven.

### Issue 2: Branding storage is operationally fragile

Using local disk is fine for local development and single-node deployments.

It is not a strong long-term architecture for distributed or cloud-native environments.

### Issue 3: Module boundaries are currently informal

Branding, theme, avatar, and shell identity are conceptually adjacent, but only loosely separated in code and documentation.

## 11. Testing Requirements

### Backend tests

- `GET /branding/logo/meta` returns `has_logo = false` when file or metadata is missing
- `GET /branding/logo/meta` returns metadata when both record and file exist
- `GET /branding/logo` returns `404` when logo missing
- upload rejects unsupported suffix
- upload rejects empty file
- upload rejects file larger than `2 MB`
- upload replaces previous logo
- upload updates `settings.branding_logo`
- non-admin upload is rejected

### Frontend tests

- sidebar shows placeholder when no logo exists
- sidebar renders logo when metadata endpoint returns `has_logo = true`
- admin sees upload button
- non-admin does not see upload button
- upload success refreshes the displayed image version

### Integration tests

- admin uploads logo -> sidebar shows updated file
- metadata and file delivery remain consistent across refresh
- branding survives only if storage layer is durable in target deployment

## 12. Recommended Cleanup Strategy

### Phase 1: Add audit visibility

Emit audit events for:

- branding upload
- branding replacement
- future branding delete or reset

### Phase 2: Move asset storage off local disk

Adopt a durable object store or shared media backend for branding assets.

Good candidates:

- Cloudinary, if the project standardizes on it
- object storage with stable URL delivery
- shared volume only as an intermediate step

### Phase 3: Separate branding administration from layout shell

Create a dedicated admin branding page for:

- upload
- preview
- metadata view
- reset

### Phase 4: Expand branding surface deliberately

If institutional branding matters, add configurable fields for:

- institution display name
- short label
- login-page branding
- footer branding
- color or theme tokens

### Phase 5: Clarify boundaries with avatar and theme

Document and maintain the distinction between:

- global institutional branding
- user identity media
- personal theme preference

## Final Summary

The current Branding Module in CAPS AI is small but functional.

It currently provides:

- one global institutional logo
- metadata lookup
- file delivery
- admin-side upload and replacement
- shell display in the sidebar

Its strongest qualities are:

- simplicity
- coherent scope
- effective cache busting
- immediate visibility in the UI

Its main weaknesses are:

- local-disk storage
- no audit trail
- no dedicated branding administration page
- no broader brand configuration beyond the logo

The correct next step is to keep the module narrow unless there is a real institutional need for broader theming. If that need exists, the next evolution should be a proper brand settings subsystem built on durable media storage and audited admin controls.

