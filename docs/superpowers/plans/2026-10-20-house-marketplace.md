# House Marketplace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a seller-only property registration flow and public property listing and detail pages.

**Architecture:** Add a dedicated SQLAlchemy `Property` model and `/properties` REST routes. Resolve seller access from the authenticated user's email and `PROPERTY_SELLER_EMAIL`; expose the resolved role through `/user/me`. Add Vue pages and a small testable property presentation helper while preserving the existing `/boards` feature.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, SQLite, Vue 3, Vue Router, Jest, pytest.

**Spec:** `docs/superpowers/specs/2026-10-20-house-marketplace-design.md`

## Global Constraints

- Store property records in a separate `property` SQLite table; keep the existing `board` table and `/boards` routes intact.
- Use `app.db` as the default SQLite database file.
- `PROPERTY_SELLER_EMAIL` identifies the only seller; compare trimmed email values case-insensitively. An empty setting grants no seller registration access.
- `GET /properties` and `GET /properties/{idx}` are public; `POST /properties` requires a valid session and the configured seller.
- The property API fields are `idx`, `title`, `address`, `price_krw`, `area_m2`, `room_count`, `description`, and `image_url` (nullable). Create requests omit `idx`.
- Validate `title` (1–200 chars), `address` (1–300 chars), `price_krw` (integer ≥ 0), `area_m2` (> 0), `room_count` (integer ≥ 0), `description` (1–5000 chars), and optional HTTP(S) `image_url`.
- Lists return newest records first. A missing detail returns 404, unauthenticated registration returns 401, and a non-seller or unset seller configuration returns 403.
- Do not add offer, contact, contract, payment, image-upload, or listing-edit workflows.
- The seller account uses existing email/password authentication. Buyers and public visitors can browse listings without signing in.

## Review Focus

- No `PROPERTY_SELLER_EMAIL` is configured: seller registration returns 403 and no account can register a property. (Task 1 test.)
- The configured email differs only by case or surrounding whitespace: it still identifies the seller. (Task 1 test.)
- An old or invalid login cookie is supplied to property registration: the API returns 401. (Task 1 test.)
- A required numeric listing value is zero, negative, or non-numeric: only price and room count accept zero; area must be positive. (Tasks 1 and 2 tests.)
- A property has no image URL: list and detail render a local placeholder without a broken image. (Task 2 test.)

---

### Task 1: Property API and seller access

**Files:**
- Create: `app/models/property.py`
- Create: `app/schemas/property.py`
- Create: `app/api/dependencies.py`
- Create: `app/api/routers/property.py`
- Create: `tests/test_properties.py`
- Modify: `app/core/config.py`
- Modify: `.env.example`
- Modify: `app/main.py`
- Modify: `app/api/routers/user.py`
- Modify: `app/schemas/user.py`

**Interfaces:**
- `PropertyCreate`: `title: str`, `address: str`, `price_krw: int`, `area_m2: float`, `room_count: int`, `description: str`, `image_url: AnyHttpUrl | None`.
- `PropertyRead`: `idx: int`, all `PropertyCreate` fields with `image_url: str | None`; do not expose `seller_user_idx`.
- `GET /properties -> list[PropertyRead]`, sorted by `Property.idx DESC`.
- `GET /properties/{idx} -> PropertyRead`, HTTP 404 when absent.
- `POST /properties -> PropertyRead`, creates a row owned by the authenticated configured seller.
- `GET /user/me -> {name, email, provider, role}`, where role is `seller` or `buyer` from the configured email.
- `get_current_user(request, db) -> User` validates `EN_AT` and raises the existing 401 session error. Use it from `/user/me` and property registration.

- [ ] **Step 1: Write failing API tests** in `tests/test_properties.py` for empty/newest-first list, detail success/404, seller create persistence, buyer and unauthenticated create denial, unset seller configuration, case/whitespace-normalized seller email, role response, and invalid payload bounds.
- [ ] **Step 2: Run the focused tests and confirm they fail for missing property behavior.** Run `python -m pytest tests/test_properties.py -q`.
- [ ] **Step 3: Implement the model, schemas, auth dependency, settings, and routes.** Add `PROPERTY_SELLER_EMAIL` (default empty); set the default database URL to `sqlite:///app.db`; import the model and router before `Base.metadata.create_all`.
- [ ] **Step 4: Run focused and full backend tests.** Run `python -m pytest tests/test_properties.py -q`, then `python -m pytest`.
- [ ] **Step 5: Self-review the API diff and commit the backend task.**

### Task 2: Property marketplace frontend

**Files:**
- Create: `frontend/src/pages/PropertyListPage.vue`
- Create: `frontend/src/pages/PropertyDetailPage.vue`
- Create: `frontend/src/pages/PropertyCreatePage.vue`
- Create: `frontend/src/lib/property-view.js`
- Create: `frontend/src/lib/property-view.test.js`
- Modify: `frontend/src/api.js`
- Modify: `frontend/src/api.test.js`
- Modify: `frontend/src/router.js`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/style.css`
- Modify: `frontend/src/pages/LoginPage.vue`
- Modify: `frontend/src/pages/SignupPage.vue`
- Modify: `frontend/index.html`

**Interfaces:**
- `createApiClient().listProperties()` calls `GET /properties`.
- `createApiClient().readProperty(idx)` calls `GET /properties/{encoded idx}`.
- `createApiClient().registerProperty(data)` calls `POST /properties` with JSON and cookies.
- Property routes are `/properties`, `/properties/new`, and `/properties/:idx`; route names are `property-list`, `property-create`, and `property-detail`. `/` and the fallback route go to `property-list`.
- `property-view.js` exports `formatPrice(priceKrw)`, `formatArea(areaM2)`, `getPropertyListState({loading, error, properties})`, `getSellerAccessState({loading, error, role})`, and `validatePropertyForm(data)`; pages use these helpers for displayed values and state decisions.

- [ ] **Step 1: Write failing Jest tests** for all three API calls, list and seller-access states, price/area formatting, and invalid/valid form values.
- [ ] **Step 2: Run the focused Jest tests and confirm they fail for the missing property methods/helpers.** Run `npm test -- --runTestsByPath src/api.test.js src/lib/property-view.test.js` from `frontend/`.
- [ ] **Step 3: Implement the API methods, helpers, routes, and responsive pages.** Public users can browse; only `role === "seller"` gets the registration form; buyers are directed to sign in or return to listings; successful creation navigates to the new detail page. Show loading, empty, error, and not-found states.
- [ ] **Step 4: Run focused and full frontend Jest tests, then build.** Run `npm test -- --runInBand`, then `npm run build` from `frontend/`.
- [ ] **Step 5: Self-review the frontend diff and commit the frontend task.**

### Integration

- [ ] Apply only each task's patch after the shared snapshot base to the primary feature checkout; do not merge or cherry-pick the snapshot commit, which contains pre-existing user changes.
- [ ] Run `python -m pytest` from the repository root and `npm test -- --runInBand` plus `npm run build` from `frontend/`.
- [ ] Review the combined diff against the design spec and fix any integration mismatch in a focused commit.
