# House Marketplace Design

## Goal

Turn the existing Vue and FastAPI application into a small property marketplace where one configured seller can publish homes and buyers can browse listing cards and details.

## Agreed context and constraints

- The app uses Vue in `frontend/`, FastAPI in `app/`, and SQLite in `app.db` by default.
- There is one seller. The seller is the existing email-login account whose email matches `PROPERTY_SELLER_EMAIL`; other accounts are buyers.
- Listing and detail reads are public. Property creation requires authentication and the configured seller identity.
- The existing board table and board routes remain intact. Properties use a separate table.
- Buyers can browse listings and listing details. This scope does not include offers, contact workflows, contracts, or payments.

## Data model

Add a `property` table with an integer primary key and these fields:

- `title`: listing headline
- `address`: listing location text
- `price_krw`: sale price in Korean won
- `area_m2`: area in square metres
- `room_count`: number of rooms; zero is allowed for a studio listing
- `description`: listing description
- `image_url`: optional image URL; uploads are out of scope
- `seller_user_idx`: foreign key to the seller's existing user record

Register the model with SQLAlchemy metadata so the existing table initialization creates the table. No user-role database migration is needed: the seller role is derived from the configured email.

## API and access

- `GET /properties` returns all properties ordered newest first by primary key.
- `GET /properties/{idx}` returns the complete listing or HTTP 404 for an unknown identifier.
- `POST /properties` accepts `title`, `address`, `price_krw`, `area_m2`, `room_count`, `description`, and optional `image_url`; it returns the created listing.
- `POST /properties` returns HTTP 401 when there is no valid login session. It returns HTTP 403 when the authenticated email does not match `PROPERTY_SELLER_EMAIL` or that setting is empty.
- `/user/me` returns `role: "seller"` for the configured email and `role: "buyer"` for all other authenticated users.
- Normalize the configured and authenticated email values by trimming whitespace and comparing case-insensitively.
- Add `PROPERTY_SELLER_EMAIL` to `Settings` and `.env.example`. The seller uses the existing email/password login; Kakao accounts without an email cannot be selected as the seller.

## Frontend

- Add property list, property detail, and seller-only property creation pages, plus routes under `/properties`.
- Set `/` and the unknown-route fallback to the property list.
- Keep the existing `/boards` routes available without using them as the marketplace home.
- The list page calls the public list API and shows loading, empty, and request-error states. Each card links to its detail page.
- The detail page displays the full listing and links back to the list. An absent image URL uses a local visual placeholder.
- The creation page checks `/user/me` before presenting the form. Buyers are directed to sign in or return to listings; the API remains the authority and rejects non-seller requests.
- The form validates required text fields, non-negative integer price and room count, and positive area before sending the request. On success it opens the newly created detail page.
- Use the existing responsive styling conventions while replacing note-specific home branding and navigation with marketplace wording.

## Errors and validation

- Apply Pydantic bounds to required fields and reject negative price, room count, and non-positive area.
- Return a clear 404 for missing listings, 401 for unauthenticated registration, and 403 for a non-seller or missing seller configuration.
- The frontend preserves retry paths for failed list/detail requests and displays server validation messages on the registration form.

## Verification

- Pytest covers public listing order and empty results, detail success and not-found behavior, successful seller registration, unauthenticated registration, buyer registration denial, missing seller configuration, and invalid listing values.
- Jest covers the new API methods, property route/page behavior, loading/error/empty states, seller-only registration access, and successful create-to-detail navigation.
- Run the full backend pytest suite and frontend Jest suite after integration.

## Design alternatives considered

1. A dedicated `Property` model and routes with the seller identified by configuration. This keeps the listing data structured, preserves boards, and enforces one seller; selected.
2. Extend the generic board model to represent properties. This couples unrelated notes and listings and leaves property fields awkwardly encoded.
3. Render static property examples in the frontend. This does not persist seller submissions or provide a real listing API.
