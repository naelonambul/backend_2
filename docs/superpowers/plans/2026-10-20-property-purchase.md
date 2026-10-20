# Property Purchase and PortOne Payment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Keep backend and frontend implementation in their assigned, separate worktrees.

**Goal:** Add a full-price property purchase flow using PortOne V2 and Toss Payments new module, with server-side payment verification and duplicate-sale prevention.

**Architecture:** The backend creates a 15-minute pending purchase using the database listing price, reserves the listing with a SQLite partial unique index, and confirms payment by retrieving it from PortOne V2. The frontend opens the PortOne V2 SDK from the property detail page and sends browser return data to an authenticated confirmation endpoint; browser data alone never marks an order paid.

**Tech Stack:** Vue 3, Vite, Jest, FastAPI, SQLAlchemy 2, SQLite, Pydantic, httpx, PortOne Browser SDK V2.

**Spec:** `docs/superpowers/specs/2026-10-20-property-purchase-design.md`

## Global Constraints

- The frontend is the Vue app in `frontend/`; the backend is the FastAPI app in `app/`; the default database is SQLite `app.db`.
- The configured `PROPERTY_SELLER_EMAIL` account is the only seller. Other authenticated accounts are buyers.
- The amount comes from `Property.price_krw` in the database, never from a client-supplied amount. Currency is `KRW`.
- Use PortOne V2 with a Toss Payments new-module channel. Do not modify existing PortOne console settings.
- Public frontend variables are `VITE_PORTONE_STORE_ID` and `VITE_PORTONE_CHANNEL_KEY`; the server-only secret is `PORTONE_API_SECRET`.
- PortOne calls are mocked in automated tests; no test may require live PG credentials.
- Keep payment confirmation and cancellation idempotent. Do not log or expose secrets.

## Review Focus

- A zero or negative listing price cannot produce a payment request; test that order creation rejects it without calling PortOne.
- A forged payment ID, non-`PAID` status, amount mismatch, or currency mismatch never marks a purchase paid; test each mismatch through the confirmation endpoint.
- An expired order that becomes paid cannot sell a listing reserved or sold by another order; test late-payment cancellation and retain `refund_pending` if cancellation fails.
- A buyer cannot confirm another user's order, and the seller cannot start a purchase; test unauthenticated 401, seller/self-purchase 403, and owner mismatch responses.
- Missing payment configuration or a PortOne timeout cannot leak a secret or mark an order paid; test 503 configuration handling and a retryable API error.

---

### Task 1: Backend purchase persistence, APIs, and payment verification

**Owner:** `backend_impl`, in its assigned isolated worktree.

**Files:**
- Create: `app/models/purchase.py`
- Modify: `app/models/__init__.py`, `app/main.py`, `app/core/config.py`, `.env.example`
- Create: `app/schemas/purchase.py`, `app/services/portone.py`, `app/api/routers/purchase.py`
- Modify: `app/schemas/property.py`, `app/api/routers/property.py`
- Create: `tests/test_purchases.py`
- Modify: `tests/test_properties.py`

**Interfaces:**
- Consumes: existing `Property`, `User`, `get_current_user`, `is_configured_seller`, and SQLAlchemy `Session` patterns.
- Produces: `POST /properties/{property_idx}/purchases` with no request body; response `{purchase_id: str, payment_id: str, order_name: str, amount: int, currency: "KRW", expires_at: datetime}`.
- Produces: `POST /purchases/{purchase_id}/confirm` accepting `{payment_id: str}`; response `{purchase_id: str, status: "pending" | "paid" | "failed" | "cancelled" | "refund_pending"}`. A terminal unsuccessful PortOne result releases the reservation; a nonterminal result stays pending.
- Produces: `availability: "available" | "reserved" | "sold"` on both property read responses.
- Produces: injectable `PortOneClient.get_payment(payment_id: str)` and `PortOneClient.cancel_payment(payment_id: str, reason: str)` methods; the client uses `Authorization: PortOne <PORTONE_API_SECRET>` and the PortOne V2 REST API.
- Persist `purchase` UUID, unique `payment_id`, property and buyer foreign keys, integer `amount_krw`, `currency`, status, and timestamps. A SQLite partial unique index covers `(property_idx)` while status is `pending`, `paid`, or `refund_pending`.

- [ ] **Step 1: Write failing purchase API tests**

Add tests named `test_purchase_requires_login`, `test_buyer_creates_pending_purchase_using_database_price`, `test_seller_and_self_purchase_are_forbidden`, `test_only_one_active_purchase_exists_per_property`, `test_expired_pending_purchase_releases_property`, `test_zero_price_property_cannot_be_purchased`, `test_purchase_returns_503_when_portone_secret_is_missing`, `test_confirmation_requires_order_owner_and_matching_payment_id`, `test_paid_confirmation_requires_exact_amount_currency_and_paid_status`, `test_terminal_unsuccessful_payment_releases_reservation`, `test_portone_lookup_timeout_keeps_order_pending`, `test_paid_confirmation_is_idempotent`, and `test_late_paid_order_is_cancelled_or_kept_refund_pending`. Assert status codes, persisted statuses, the DB-derived amount, and PortOne mock calls.

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `python -m pytest tests/test_purchases.py -q`
Expected: FAIL because the purchase model, router, schemas, and PortOne client do not exist yet.

- [ ] **Step 3: Implement purchase persistence and environment configuration**

Create `Purchase` with the listed fields and a SQLite partial unique index. Register the model before `Base.metadata.create_all`. Generate PortOne `payment_id` values as `str(uuid.uuid4())`, which fits Toss Payments' documented identifier format. Add `PORTONE_API_SECRET` to `Settings` and `.env.example`. Expire stale `pending` records transactionally before creating a new order; reject a non-positive stored price with 422. Return 503 without creating an order when `PORTONE_API_SECRET` is missing.

- [ ] **Step 4: Implement injectable PortOne V2 retrieval and cancellation**

Implement `PortOneClient.get_payment(payment_id: str)` and `cancel_payment(payment_id: str, reason: str)` in `app/services/portone.py` with `httpx`, a bounded timeout, server-only authorization, response validation, and sanitized errors. Raise a retryable application error on network or 5xx failures; leave a purchase pending when payment lookup times out.

- [ ] **Step 5: Implement purchase and confirmation endpoints plus listing availability**

Create the two routes in `app/api/routers/purchase.py`. Require a buyer session; reject seller/self-purchase; derive amount and order name from the property. Confirmation must fetch the payment, compare ID, status, exact total, and currency, then use a transaction to mark only the unique, unexpired order paid. Mark terminal unsuccessful PortOne states `failed` or `cancelled` and release their reservation. Cancel late, conflicting, or mismatched paid transactions; keep failed cancellations in `refund_pending`. Register the router. Add `availability` to property schemas and compute `sold` before `reserved` before `available` for list and detail responses.

- [ ] **Step 6: Run backend purchase and property tests**

Run: `python -m pytest tests/test_purchases.py tests/test_properties.py -q`
Expected: PASS, including the five Review Focus cases owned by this task.

- [ ] **Step 7: Commit backend changes in the backend worktree**

Commit only the backend files listed in this task with message `feat: add verified property purchase API`.

### Task 2: Frontend PortOne checkout and return flow

**Owner:** `frontend_impl`, in its assigned isolated worktree. Begin after the API contract above is agreed; backend and frontend own disjoint folders.

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/api.js`, `frontend/src/router.js`, `frontend/src/pages/PropertyDetailPage.vue`, `frontend/.env.example`
- Create: `frontend/src/lib/property-purchase.js`, `frontend/src/lib/portone.js`, `frontend/src/pages/PropertyPurchaseReturnPage.vue`, `frontend/src/lib/property-purchase.test.js`

**Interfaces:**
- Consumes Task 1's `api.createPurchase(propertyIdx)` response and `api.confirmPurchase(purchaseId, { payment_id })` response.
- Produces `createApiClient()` methods `createPurchase(propertyIdx)` and `confirmPurchase(purchaseId, payload)` using the existing cookie credentials.
- Produces an injectable checkout helper that calls PortOne Browser SDK V2 `requestPayment` with `storeId`, `paymentId`, `orderName`, `totalAmount`, `currency: "KRW"`, `channelKey`, `payMethod: "CARD"`, and a redirect URL to the purchase-return page.
- Use `@portone/browser-sdk` with the documented `@portone/browser-sdk/v2` import. The return page reads the purchase ID from `sessionStorage`, takes the PortOne payment ID from the SDK response or return query, and lets the backend verify it.

- [ ] **Step 1: Write failing checkout flow tests**

Add tests named `test_checkout_uses_server_order_amount_and_v2_channel_config`, `test_checkout_stores_purchase_id_for_redirect_return`, `test_checkout_cancellation_does_not_show_success`, `test_return_confirms_with_server_and_clears_session_on_terminal_result`, `test_return_keeps_session_for_retryable_error`, `test_seller_or_unavailable_listing_cannot_start_checkout`, and `test_missing_public_portone_config_shows_setup_error`. Assert SDK arguments, API calls, session state, and visible purchase state.

- [ ] **Step 2: Run the focused Jest test and verify it fails**

Run: `npm test -- --runTestsByPath src/lib/property-purchase.test.js`
Working directory: `frontend/`
Expected: FAIL because the checkout helper, API methods, and return page do not exist yet.

- [ ] **Step 3: Add the PortOne Browser SDK and API methods**

Add `@portone/browser-sdk` and update the lockfile. Add `createPurchase(propertyIdx)` and `confirmPurchase(purchaseId, payload)` to `frontend/src/api.js`. Add empty public `VITE_PORTONE_STORE_ID` and `VITE_PORTONE_CHANNEL_KEY` entries to `frontend/.env.example`; never add a server secret there.

- [ ] **Step 4: Implement an injectable checkout helper**

Implement `startPropertyPurchase({ propertyIdx, api, portone, storeId, channelKey, redirectUrl, sessionStorage })` in `frontend/src/lib/property-purchase.js`. Create the server order first, persist only its ID in session storage, then call `portone.requestPayment` with the exact server-issued payment parameters. Only direct successful SDK responses may trigger immediate server confirmation; redirect responses continue through the return route. Cancellation and SDK errors must not display purchase success.

- [ ] **Step 5: Implement the return page and detail-page states**

Add `/properties/purchase/return` before the dynamic property route. Confirm the returned payment ID with the saved purchase ID, show retryable versus terminal errors, and preserve the session entry on retryable failures. On the detail page call the existing `getCurrentUserOrNull(api)` helper; show the full price and purchase button only to buyers for `availability === "available"`; redirect guests to login with the current detail path; disable checkout while it runs; refresh availability after confirmation.

- [ ] **Step 6: Run focused Jest tests and the full frontend suite**

Run: `npm test -- --runTestsByPath src/lib/property-purchase.test.js` then `npm test`
Working directory: `frontend/`
Expected: both commands PASS, including the five Review Focus cases owned by this task.

- [ ] **Step 7: Commit frontend changes in the frontend worktree**

Commit only the frontend files listed in this task with message `feat: add PortOne property checkout UI`.

### Task 3: Main-agent integration and browser verification

**Owner:** Main agent. Review and integrate the two worktree results without reverting unrelated project changes.

**Files:**
- Review and integrate only the Task 1 backend patch and Task 2 frontend patch.
- Do not modify PortOne dashboard settings or add real merchant credentials to the repository.

**Interfaces:**
- Uses the exact API contract produced by Task 1 and consumed by Task 2.
- Uses the existing Chrome DevTools browser session for UI verification.

- [ ] **Step 1: Review backend and frontend commits against the spec and this contract**

Check ownership and authorization, atomic unique-index behavior, payment state/amount/currency verification, redirect recovery, secret placement, and absence of unrelated changes. Resolve only cross-folder integration mismatches with the owning agent in their worktree.

- [ ] **Step 2: Run the complete backend and frontend suites after integration**

Run: `python -m pytest -q` from the repository root and `npm test` from `frontend/`.
Expected: all backend tests and all Jest tests PASS without live PG credentials.

- [ ] **Step 3: Verify the browser flow with Chrome DevTools**

Run the frontend and backend with PortOne test keys if they become available. With no channel configured, verify the detail-page states, guest redirect, missing-config message, and that no client-only result can show completion. Do not claim a real PG approval succeeded without a configured test channel.

## Execution notes

- The spec and this plan are the approved contract; the backend agent must not edit `frontend/`, and the frontend agent must not edit `app/`.
- Use the assigned backend and frontend worktrees. Each agent must leave pre-existing unrelated changes intact.
- Actual payment testing is conditional on a PortOne Toss V2 channel and server API secret; automated tests use mocks in the meantime.
