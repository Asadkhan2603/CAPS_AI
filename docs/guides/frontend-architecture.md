# Frontend Architecture Guide

## Overview

The frontend is a React 18 + Vite single-page application with route-level code splitting, provider-based state composition, a centralized API client, and a shared dashboard shell for authenticated pages.

Primary entry points:
- [main.jsx](/frontend/src/main.jsx)
- [App.jsx](/frontend/src/App.jsx)
- [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx)

Core architectural characteristics:
- React component architecture with hook-based state
- Vite build and dev runtime
- React Router for route composition
- context providers for auth, theme, and toast state
- centralized axios-based API client with auth refresh logic
- mixed page model: shared CRUD screens plus richer domain-specific workflow pages

## Top-Level Frontend Tree

```text
frontend/
|-- Dockerfile
|-- package.json
`-- src/
    |-- main.jsx
    |-- App.jsx
    |-- api/
    |-- auth/
    |-- components/
    |   |-- admin/
    |   |-- charts/
    |   |-- communication/
    |   |-- layout/
    |   |-- system/
    |   |-- Teacher/
    |   `-- ui/
    |-- config/
    |-- context/
    |-- hooks/
    |-- pages/
    |-- routes/
    |-- services/
    |-- styles/
    `-- utils/
```

## Runtime Bootstrap Flow

Bootstrap happens in [main.jsx](/frontend/src/main.jsx).

Provider stack order:
1. `BrowserRouter`
2. `ThemeProvider`
3. `AuthProvider`
4. `ToastProvider`

This order matters:
- routing must wrap the app shell
- theme applies global document state
- auth is needed by route guards and layout
- toast is cross-cutting UI feedback across all screens

Application root:
- [App.jsx](/frontend/src/App.jsx)

`App.jsx` wraps the route system with:
- `ErrorBoundary`

Architectural implication:
- route rendering failures are isolated by a global boundary rather than crashing the whole React tree silently

## Routing Architecture

Primary route map:
- [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx)

### Route Composition Pattern

The route system uses:
- lazy-loaded pages through `React.lazy`
- `Suspense` fallback with `PageSkeleton`
- authenticated dashboard layout nesting
- `ProtectedRoute` for auth and feature gating

Pattern:
1. public routes such as login and register are mounted directly
2. authenticated routes are nested under `DashboardLayout`
3. each route can add its own access rule through `FEATURE_ACCESS`

### Protected Route Behavior

Implementation:
- [ProtectedRoute.jsx](/frontend/src/routes/ProtectedRoute.jsx)

Current behavior:
- shows `PageLoader` while auth session is being checked
- redirects unauthenticated users to `/login`
- evaluates route access through `canAccessFeature(...)`
- redirects denied users to `/dashboard`

Inputs accepted by the route guard:
- `allowedRoles`
- `requiredTeacherExtensions`
- `requiredAdminTypes`

Important architectural point:
- frontend route gating is for UX and route protection
- backend authorization remains the real security boundary

## Access Control Architecture

Primary config:
- [featureAccess.js](/frontend/src/config/featureAccess.js)

Permission utility:
- [permissions.js](/frontend/src/utils/permissions.js)

### What FEATURE_ACCESS Does

It defines route and feature eligibility by:
- base role
- required admin subtype
- required teacher extension roles
- governance delete prompt configuration for shared CRUD pages

Examples of route-level subtype enforcement currently present:
- admin dashboard pages restricted by subtype
- academic setup pages restricted by admin subtype
- section and canonical lower academic entities allow `department_admin` at frontend level where intended

### Governance UI Integration

`FEATURE_ACCESS` also carries UI metadata for delete governance flows in shared CRUD pages.

This is consumed by:
- [EntityManager.jsx](/frontend/src/components/ui/EntityManager.jsx)

Result:
- delete prompts can be configured per feature without hardcoding them page by page

## Auth State Architecture

Primary implementation:
- [AuthContext.jsx](/frontend/src/context/AuthContext.jsx)

### Auth Responsibilities

`AuthProvider` owns:
- current access token
- current user object
- session validation state
- login flow
- logout flow
- user refresh flow
- idle timeout enforcement
- max session lifetime enforcement

### Storage Model

Stored in session storage through the API client helpers:
- access token
- refresh token
- user payload
- session started timestamp
- last activity timestamp

Important session behavior:
- session idle timeout defaults to 30 minutes unless overridden
- max session defaults to 8 hours unless overridden
- auth storage versioning can invalidate old client-side sessions on auth model changes

### Session Validation Flow

On app load:
1. read token from storage
2. if token exists, call `/auth/me`
3. hydrate user state on success
4. clear session on failure or expired timing window

During runtime:
- activity events update last-activity timestamp
- interval checks enforce idle timeout and max session age
- `401` retry logic in `apiClient` attempts refresh token exchange automatically

Architectural implication:
- session management is reasonably centralized and more robust than a simple token-in-memory pattern

## Theme Architecture

Implementation:
- [ThemeContext.jsx](/frontend/src/context/ThemeContext.jsx)

Current behavior:
- persists theme in `localStorage`
- toggles `dark` class on `document.documentElement`
- exposes `theme`, `isDark`, and `toggleTheme`

Architectural consequence:
- theme is global document state, not page-local visual state

## Toast And Feedback Architecture

Implementation:
- [ToastContext.jsx](/frontend/src/context/ToastContext.jsx)
- [useToast.js](/frontend/src/hooks/useToast.js)

Current behavior:
- creates short-lived in-memory toast entries
- assigns `crypto.randomUUID()` ids
- automatically dismisses after default timeout

Usage pattern:
- pages and shared components push success/info/error toasts
- `DashboardLayout` renders the shared `Toast` UI

## Layout Architecture

Primary authenticated shell:
- [DashboardLayout.jsx](/frontend/src/components/layout/DashboardLayout.jsx)

Supporting layout components live under:
- `frontend/src/components/layout`

### DashboardLayout Responsibilities

- persistent sidebar shell
- topbar shell
- responsive mobile sidebar state
- collapse state for desktop sidebar
- route transition animation using `framer-motion`
- toast rendering
- logout wiring into layout actions

Result:
- business pages focus on page content while navigation, chrome, and feedback remain centralized

## API Client Architecture

Primary implementation:
- [apiClient.js](/frontend/src/services/apiClient.js)

### Responsibilities

- define shared axios instance
- attach bearer token
- attach request and trace ids
- record local trace history for recent API calls
- unwrap success envelopes
- normalize error envelopes
- perform refresh-token retry on `401`
- clear auth state when refresh fails

### Client-Side Trace Buffer

`apiClient` keeps a small in-memory rolling trace list.

Tracked fields include:
- time
- method
- url
- status
- duration
- trace id
- request id
- error id

Architectural significance:
- this is a lightweight support and diagnostics aid built into the browser client

## Services Layer Architecture

Current services directory:
- `adminGovernanceApi.js`
- `aiService.js`
- `apiClient.js`
- `sectionsApi.js`
- `timetableApi.js`

Current service-layer pattern:
- not every page uses a dedicated service wrapper
- some pages call `apiClient` directly
- some domains expose a thin wrapper around repeated API paths

Implication:
- the service layer is partial, not uniformly enforced
- API calling style is currently mixed between direct page calls and service abstraction

## Page Architecture

Primary page directory:
- `frontend/src/pages`

Page categories in the current frontend:

### 1. Shared CRUD Pages

These pages often use `EntityManager` and a config-driven form/table setup.

Examples:
- Departments
- Branches
- Years
- many academic setup pages
- Evaluations in admin/teacher list mode

Strength:
- very fast to scaffold and keep visually consistent

Weakness:
- complex workflow semantics can be hidden behind generic CRUD controls

### 2. Domain-Specific Workflow Pages

These pages implement custom behavior beyond CRUD.

Examples:
- `Teacher/EvaluateSubmission.jsx`
- communication feed and announcements screens
- admin governance, system, compliance, and recovery pages
- clubs and event workflows

Strength:
- can express real workflow logic and richer state transitions

Weakness:
- custom pages can drift from shared governance or error-handling patterns if not carefully aligned

### 3. Dashboard And Summary Pages

Examples:
- dashboard
- analytics
- admin dashboard
- compliance and analytics summary pages

These are read-model consumers of backend aggregate APIs.

## Shared UI Architecture

Shared UI components live under:
- `frontend/src/components/ui`

Important shared component:
- [EntityManager.jsx](/frontend/src/components/ui/EntityManager.jsx)

### EntityManager Responsibilities

- list loading with filters
- create form rendering
- edit modal support where enabled
- delete flow
- governance review prompt for destructive actions
- integration with `FEATURE_ACCESS` delete-governance config
- shared table rendering and pagination behavior

Architectural significance:
- `EntityManager` is one of the most important frontend primitives in the repo
- it effectively acts as the frontend CRUD framework for many modules

Current limitation:
- modules with more operational nuance often outgrow it and require custom pages

## Visual And Styling Architecture

Global styling entry:
- `frontend/src/styles/global.css`

Current frontend stack includes:
- Tailwind CSS
- framer-motion
- lucide-react
- recharts

Visual architecture characteristics:
- utility-first styling approach
- animated shell and transitions
- icon-based admin and workflow UI
- dashboard-oriented responsive layout

## Build And Tooling Architecture

From [package.json](/frontend/package.json):
- dev server: `vite`
- build: `vite build`
- preview: `vite preview`
- lint: ESLint
- tests: Vitest

Key dependencies:
- React 18
- React Router 6
- axios
- framer-motion
- lucide-react
- recharts

Dev tooling:
- Vite
- ESLint
- Vitest
- Tailwind CSS

## Frontend Runtime Risks

### 1. Mixed Service Boundary

Some pages use direct `apiClient` calls while others use dedicated service modules.

Risk:
- inconsistent reuse
- inconsistent API abstraction depth

### 2. Shared CRUD Versus Workflow Pages

The app mixes generic CRUD and custom domain screens.

Risk:
- UX and governance patterns can diverge
- backend features may be available but not surfaced in the generic UI

### 3. Frontend/Backend Contract Drift

Examples already seen in the codebase and audits:
- backend may expose richer fields than the page renders
- some UI routes allow access where backend writes still require stricter permissions
- legacy academic endpoints still influence some pages despite canonical hierarchy adoption

### 4. Prompt-Based Admin Actions

Some privileged flows still use thin prompt interactions rather than structured forms or modals.

Risk:
- weak operator UX
- weak metadata quality for governance-heavy actions

## Frontend Strengths

1. Centralized route map.
2. Clear provider stack.
3. Robust auth context with idle and max-session enforcement.
4. Shared API client with refresh retry and trace tracking.
5. Shared dashboard shell for consistent UX.
6. `EntityManager` provides a reusable CRUD framework.

## Main Structural Weaknesses

1. Service abstraction is partial.
2. Generic CRUD pages can hide important workflow complexity.
3. Backend capabilities are richer than some current screens expose.
4. Access control logic exists both in backend and frontend, so policy drift must be watched continuously.
5. Custom workflow pages and shared CRUD pages are not yet fully normalized around one governance interaction style.

## Recommended Reading Order For Frontend Engineers

1. [main.jsx](/frontend/src/main.jsx)
2. [App.jsx](/frontend/src/App.jsx)
3. [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx)
4. [ProtectedRoute.jsx](/frontend/src/routes/ProtectedRoute.jsx)
5. [featureAccess.js](/frontend/src/config/featureAccess.js)
6. [AuthContext.jsx](/frontend/src/context/AuthContext.jsx)
7. [apiClient.js](/frontend/src/services/apiClient.js)
8. [DashboardLayout.jsx](/frontend/src/components/layout/DashboardLayout.jsx)
9. [EntityManager.jsx](/frontend/src/components/ui/EntityManager.jsx)
10. domain pages relevant to the module being changed

## Architecture Summary

The frontend is best understood as a modular dashboard SPA with a strong shared shell and transport layer, but with mixed page abstraction depth.

It is not a component library-first architecture and not a heavy state-machine frontend. It is a pragmatic application client with:
- provider-based global state
- route and feature gating
- centralized transport and auth retry logic
- reusable CRUD scaffolding
- custom pages for the workflows that outgrow CRUD

That is a reasonable architecture for the current system size. The main gains now come from normalizing the mixed service/page patterns, not from replacing the frontend foundation.


