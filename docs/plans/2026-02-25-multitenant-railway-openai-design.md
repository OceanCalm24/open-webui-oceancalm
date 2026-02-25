# Multi-Tenant Railway + OpenAI Design

**Date:** 2026-02-25
**Status:** Approved

## Overview

A multi-tenant fork of Open WebUI deployed as a single Railway service. All clients share one URL and one PostgreSQL database but have fully isolated data via row-level tenant scoping. The agency's branding is applied universally — no per-client branding. OpenAI API provides model inference; Ollama is not used.

**Scale:** 25 tenants in year one.

---

## Architecture

Single Railway deployment — no proxy layer, no per-tenant infrastructure provisioning.

| Service | What it is |
|---|---|
| `open-webui` | Forked Open WebUI app, deployed from GitHub |
| `postgres` | Railway PostgreSQL plugin |
| `volume` | Railway persistent volume at `/app/backend/data` for uploaded files |

### User Tiers

| Tier | Who | Access |
|---|---|---|
| **Super Admin** | Agency team (~5 people) | All tenants, all data, tenant management |
| **Tenant Admin** | Each client's admin | Their tenant's users and settings only |
| **Tenant User** | Regular client users | Their own chats and data only |

All tiers log in at the same URL with the same login screen. Tenant context is established at login and carried in the JWT.

---

## Database Design

### New Table: `tenants`

```
id          UUID, primary key
name        string — display name (e.g. "Acme Corp")
slug        string, unique — used in filters/logging (e.g. "acme-corp")
is_active   boolean — soft disable without deleting
settings    JSON — per-tenant config overrides (e.g. custom system prompt)
created_at  timestamp
```

### Modified Tables

`tenant_id` (UUID, FK → `tenants.id`) added to all core tables:

| Table | Notes |
|---|---|
| `user` | NULL for super admins, required for all others |
| `chat` | Core isolation — each client's conversations stay separate |
| `message` | Scoped via chat, indexed directly for query performance |
| `group` | Client-specific user groups |
| `document` / `knowledge` | Client-specific RAG documents |
| `tool` / `function` | Client-specific custom tools |
| `model` | Per-tenant model access lists |
| `prompt` | Client-specific saved prompts |
| `file` | Uploaded files scoped to tenant |
| `memory` | User memories scoped to tenant |

### Migration Strategy

A single Alembic migration delivers:
1. Creates the `tenants` table
2. Adds `tenant_id` columns to all tables above
3. Seeds one default super-admin tenant (nullable) for existing super admin users

Migrations run automatically on startup via the existing `ENABLE_DB_MIGRATIONS=true` setting.

---

## Authentication & Tenant Context

### Login Flow — Tenant Users

1. User visits `yourdomain.com` and enters email + password
2. Backend resolves their `user` record, reads `tenant_id`
3. JWT issued with standard claims + `tenant_id` claim
4. All subsequent requests carry the JWT in a cookie (unchanged from stock Open WebUI)
5. FastAPI dependency `get_tenant_context` extracts `tenant_id` on every request
6. All queries scoped automatically to that `tenant_id`

### Login Flow — Super Admins

1. Same login screen, no special URL
2. Backend sees `user.is_super_admin = true`
3. JWT issued with `tenant_id = null` and `is_super_admin = true`
4. Super admins land on the Tenants control plane view
5. When acting on a specific tenant, the UI sends `X-Tenant-ID: <id>` on requests
6. Middleware permits this override only for super admins

### New User Registration

- `ENABLE_SIGNUP = false` — self-registration disabled globally
- Super admins create tenant admin accounts from the control plane
- Tenant admins invite their own users from within their tenant
- Every non-super-admin user is assigned a `tenant_id` at creation — unscoped users cannot exist

### What Does Not Change

- Password hashing and JWT signing logic
- Session management and cookie handling
- OAuth configuration (if enabled later)
- The login UI

---

## Admin UI & Control Plane

The control plane lives inside the existing Open WebUI admin panel as a new **"Tenants"** section, visible to super admins only. No separate application.

### Super Admin — Tenant List View

- Table: tenant name, slug, active user count, chat count, estimated API cost, created date, active status
- "New Tenant" button — creates tenant record + first tenant admin account
- Click any row to drill into tenant detail

### Super Admin — Tenant Detail View

- Tenant settings: name, active/inactive toggle, system prompt override, model access
- User list: add/remove users, reset passwords, change roles (all scoped to this tenant)
- Usage stats: messages sent, tokens consumed, estimated OpenAI cost
- "Enter as Admin" button: switches super admin into tenant context to see exactly what the client sees

### Tenant Admin View

- Standard Open WebUI admin panel, fully scoped to their tenant
- Can manage their users, view usage, configure system prompts
- Cannot see other tenants or the Tenants section
- Cannot create new tenants

### Provisioning a New Client

1. Super admin clicks "New Tenant"
2. Fills in: tenant name, slug, initial admin email + password
3. System creates `tenants` record + first `user` record (`role=admin`, scoped to tenant)
4. Super admin shares credentials with client
5. Client logs in at `yourdomain.com` — lands in their isolated instance

No infrastructure changes required to add a new tenant.

---

## Railway Deployment

### Environment Variables

```
DATABASE_URL        = (auto-provided by Railway PostgreSQL plugin)
OPENAI_API_KEY      = sk-...
OPENAI_API_BASE_URL = https://api.openai.com/v1
WEBUI_SECRET_KEY    = (strong random string, generated once)
ENABLE_SIGNUP       = false
ENABLE_LOGIN_FORM   = true
CORS_ALLOW_ORIGIN   = https://yourdomain.com
ENABLE_DB_MIGRATIONS = true
```

### Custom Domain

- One custom domain pointing to the `open-webui` Railway service
- Railway manages SSL automatically via Let's Encrypt
- No per-tenant DNS configuration

### Deployment Pipeline

- Push to `main` branch on GitHub → Railway auto-deploys
- Builds using the existing `Dockerfile` (no build process changes)
- Database migrations run automatically on startup
- Rolling deploys — no downtime

### Scaling

- Single Railway instance sufficient for 25 tenants
- Vertical scaling (more RAM/CPU) available in Railway settings with no config changes
- PostgreSQL scales independently via Railway plugin settings

### Estimated Cost

| Item | Est. Monthly Cost |
|---|---|
| Railway Pro plan | ~$20 |
| PostgreSQL plugin | ~$5–15 |
| **Infrastructure total** | **~$25–40/month** |
| OpenAI API | Variable — billed per usage |

---

## Key Implementation Risks

| Risk | Mitigation |
|---|---|
| Upstream Open WebUI updates conflict with tenant changes | Pin to a stable version; review upstream diffs before merging |
| Query missing a tenant filter leaks data across tenants | Middleware enforces tenant context; add integration tests per endpoint |
| Alembic migration fails on existing data | Migration is additive only (new columns, nullable initially); safe to run on any existing DB |
| Super admin `X-Tenant-ID` override abused | Middleware validates `is_super_admin` flag before allowing override; flag is not user-settable |
