# FieldPilot API: a guide for the front end

This guide is for whoever builds a screen on the FieldPilot backend. It
covers the flows of D082 (login) and D083 (plot → plan → sowing → harvest →
passport), with request and response examples. Every route is also listed
in [`architecture.md` §7](architecture.md#7-rest-api), and FastAPI serves
an interactive reference at `http://localhost:8000/docs` while
`make dev` runs.

- [1. Basics](#1-basics)
- [2. Login and sessions](#2-login-and-sessions)
- [3. Plots and their site data](#3-plots-and-their-site-data)
- [4. The planting plan](#4-the-planting-plan)
- [5. Confirming the sowing](#5-confirming-the-sowing)
- [6. Confirming the harvest](#6-confirming-the-harvest)
- [7. The public passport](#7-the-public-passport)
- [8. Selling the harvest (farmer and warehouse)](#8-selling-the-harvest-farmer-and-warehouse)
- [9. The store (customers)](#9-the-store-customers)
- [10. Errors](#10-errors)
- [11. Values and enums](#11-values-and-enums)

---

## 1. Basics

| | |
|---|---|
| Base URL | `http://localhost:8000` (`BACKEND_PORT` changes it) |
| Format | JSON in and out; dates `YYYY-MM-DD`; datetimes ISO 8601 in UTC |
| Language | Everything is English by default (`APP_LANGUAGE=en`, D084). Every `message` is in `APP_LANGUAGE` and safe to show the user as is. Fields ending in `_es` stay Spanish for older clients; read the neutral field (`reason`, `name`, `display_name`, `crop_name`) |
| Auth | `Authorization: Bearer <access_token>` on every route except those marked **public** |

**Roles.**
- `farmer`: farm screens and their listings.
- `customer`: the store.
- `operator`: the warehouse (receipts and deliveries).
- `admin`: everything.

A screen should hide what the role cannot use, but the backend always
checks the role again (403).

**Demo mode.** With `APP_PROFILE=demo` and `AUTH_REQUIRED=0` in `.env`, the
farm routes work without a token, acting as one demo farmer. That keeps the
current dashboard running. Build every new screen with tokens: production
never runs without them.

---

## 2. Login and sessions

### 2.1 Register

First read the privacy policy version the form must accept. This route is
**public**.

```http
GET /auth/privacy-policy
```
```json
{ "version": "2026-11-03" }
```

Then register. This route is **public**.

```http
POST /auth/register
Content-Type: application/json

{
  "phone": "300 123 4567",
  "full_name": "Ana Pérez",
  "password": "cafe-con-panela",
  "role": "farmer",
  "accept_privacy_policy": true,
  "privacy_policy_version": "2026-11-03"
}
```

**Response: 201.** The user is logged in at once.

```json
{
  "user": { "id": 7, "phone": "+573001234567", "full_name": "Ana Pérez", "role": "farmer" },
  "tokens": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "Xq3...",
    "token_type": "bearer",
    "expires_in": 900
  }
}
```

**The fields.**
- **`phone`:** a Colombian mobile, 10 digits starting with 3. The user may
  type spaces, dashes or `+57`; the backend stores `+57XXXXXXXXXX`.
- **`password`:** from 10 to 128 characters, and it must not contain the
  phone number.
- **`role`:** only `farmer` or `customer`. Operators and admins are created
  on the server with `make user`.

**Errors.**

| Code | Error | Meaning |
|---|---|---|
| 409 | `PhoneTakenError` | The phone already has an account |
| 409 | `StalePolicyError` | The policy version changed: fetch it again and ask again |
| 422 | `ConsentRequiredError` | The policy was not accepted |
| 422 | `InvalidPhoneError` | Not a Colombian mobile |
| 422 | `WeakPasswordError` | The password breaks a rule; the message says which |

### 2.2 Log in

This route is **public**.

```http
POST /auth/login
{ "phone": "3001234567", "password": "cafe-con-panela" }
```

**Response: 200**, with a token pair:
```json
{ "access_token": "...", "refresh_token": "...", "token_type": "bearer", "expires_in": 900 }
```

**Errors.**
- **401 `InvalidCredentialsError`:** the same answer for an unknown phone
  and a wrong password. Do not tell the user which one it was.
- **423 `AccountLockedError`:** 5 failures in a row lock the account for 15
  minutes. Show the message and disable the button.

### 2.3 Keep the session alive

- **The access token** lasts `expires_in` seconds (15 minutes).
- **The refresh token** lasts 30 days. **It is single-use**: every refresh
  returns a new pair, and the old refresh token stops working.

```http
POST /auth/refresh
{ "refresh_token": "Xq3..." }
```
```json
{ "access_token": "...new...", "refresh_token": "...new...", "token_type": "bearer", "expires_in": 900 }
```

**The recommended client logic:**

1. Keep both tokens. Prefer memory for the access token, and secure
   storage for the refresh token.
2. When a call returns **401** with `InvalidSessionError`, call
   `/auth/refresh` **once**, store the new pair, and retry the call.
3. If the refresh itself returns 401, the session is over: go to login.
4. **Never run two refreshes at the same time.** Sending a used refresh
   token again is treated as theft and closes every session of that login.
   Queue the calls behind a single refresh in progress.

### 2.4 Who am I, and logging out

```http
GET /auth/me                     → { "id": 7, "phone": "+573001234567", "full_name": "Ana Pérez", "role": "farmer" }
POST /auth/logout                { "refresh_token": "..." }   → 204 (this device)
POST /auth/logout-all                                          → 204 (every device)
```

All three need the access token. After logging out, delete both tokens on
the client.

---

## 3. Plots and their site data

### 3.1 Create a plot

Needs the `farmer` or `admin` role.

```http
POST /plots
{
  "name": "Finca La Esperanza",
  "municipality": "La Plata",
  "department": "Huila",
  "latitude": 2.39,
  "longitude": -75.89,
  "area_ha": 3.5
}
```

**Response: 201.**
```json
{
  "id": 2, "name": "Finca La Esperanza", "municipality": "La Plata", "department": "Huila",
  "latitude": 2.39, "longitude": -75.89, "area_ha": 3.5, "utc_offset_hours": -5.0
}
```

**The fields.**
- **The coordinates** must be in Colombia: latitude from −4.3 to 13.5,
  longitude from −82 to −66.8. The planner was trained there.
- **`area_ha`:** over 0 and at most 1000.
- A farmer who creates a plot **becomes its member**: only members see it.

Creating the plot also **starts building its site data** in the
background: the weather since 1991, the soil and El Niño. It takes about 1
to 3 minutes.

### 3.2 Wait for the site data

```http
GET /plots/2/site
```
```json
{
  "status": "pending",
  "requested_at": "2026-11-03T15:02:11Z",
  "finished_at": null,
  "message": null,
  "weather_until": null,
  "built_on": null
}
```

| `status` | What to show |
|---|---|
| `pending` | "Preparing your plot's data…". Poll every 10 s |
| `ready` | The plan can be asked for. `weather_until` is the last day of real weather |
| `failed` | Show `message` and offer a retry: `POST /plots/2/site` |
| `missing` | No data and no job (an old plot). Offer `POST /plots/2/site` |

`POST /plots/{id}/site` rebuilds the data and answers 202 with the new
state. It answers 409 `SiteJobPendingError` while a build is running.

### 3.3 List the plots

`GET /plots` returns only the plots of the logged-in user; an admin sees
all. The other plot routes (`/zones`, `/imagery`, …) answer 403 to a user
who is not a member.

---

## 4. The planting plan

```http
GET /plots/2/planting-plan?from=2026-11-09&weeks=4
```

**Parameters.**
- **`from`:** optional. Without it, the plan starts on the plot's local
  today.
- **`weeks`:** from 1 to 12; the default is 4.

```json
{
  "plot_id": 2,
  "generated_at": "2026-11-03T15:10:00Z",
  "model": "planner-2026-11-03",
  "site_built_on": "2026-11-03",
  "weeks": [
    {
      "sowing_date": "2026-11-09",
      "weather_until": "2026-10-31",
      "oni": 2.16,
      "oni_latest_published": false,
      "outlooks": [
        {
          "crop": "soybean", "name": "Soybean", "name_es": "Soya",
          "sowing_date": "2026-11-09", "harvest_date": "2027-03-04",
          "rel_yield_p10": 0.58, "rel_yield_p50": 0.72, "rel_yield_p90": 0.84,
          "p_success": 0.93, "irrigation_mm_p50": 142.0,
          "heat_days": 3.0, "cold_days": 0.0, "automatable": false
        }
      ]
    }
  ]
}
```

**How to show it.**
- **The order:** `outlooks` is already sorted best first, by `rel_yield_p50`
  and then `p_success`. **The first three are "recommended".** Section 5
  uses the same rule.
- **`rel_yield_*`** is a fraction of the crop's potential yield under rain
  only. Show it as a percentage, with the p10 to p90 range as the
  uncertainty.
- **`p_success`** is the probability that the yield reaches 60 % of the
  potential.
- **`irrigation_mm_p50`** is the extra water the crop would need on top of
  the rain.
- **`automatable: false`** means stage 2 cannot run that crop yet. It can
  be sown and harvested, but nothing is irrigated automatically. Show it as
  "advice only".
- **`model`:** `b0-climatology` means the trained network is not in use.
  Say so on screen.
- **`oni_latest_published: true`** means that week used the latest El Niño
  value, not the one due by sowing time.

**Errors.**
- **409 `MissingDataError`:** the site data is not ready (§3.2).
- **403:** the user is not a member of the plot.

---

## 5. Confirming the sowing

A plan is advice. **A cycle starts only when the farmer confirms that they
sowed.**

```http
POST /plots/2/cycles
{ "crop": "soybean", "sowing_date": "2026-11-09", "accept_own_risk": false }
```

**Response: 201.**
```json
{
  "id": 5, "plot_id": 2, "crop": "soybean", "sowing_date": "2026-11-09",
  "status": "active", "automated": false, "own_risk": false,
  "plan": { "model": "planner-2026-11-03", "rank": 1, "rel_yield_p50": 0.72, "p_success": 0.93 },
  "harvested_on": null, "lot_code": null,
  "accumulated_gdd": 0.0, "gdd_updated_through": null, "stages": []
}
```

**The rules.**
1. **The sowing date has already happened:** at most today, and at most 60
   days back. Otherwise it is 422 `InvalidSowingDateError`.
2. **The plot has no active cycle.** Otherwise it is 409
   `ActiveCycleExistsError`.
3. **`crop`** may be any crop the farmer grows, as a lowercase slug
   (`soybean`, `aguacate_hass`). The planner's crops are in §9.
4. **The crop must be in the top 3 of the plan for that sowing week.**
   Otherwise it is 422 `OwnRiskRequiredError`. That covers three cases: the
   crop ranks lower, it is not a planner crop, or the plot has no site
   data.

   **The screen flow:**
   1. Send `accept_own_risk: false` first.
   2. On 422 `OwnRiskRequiredError`, show its `message`, which names the
      recommended crops.
   3. Ask the farmer to confirm explicitly: "I sow at my own
      risk".
   4. Send the same request again with `accept_own_risk: true`.
5. **The answer says how the cycle runs:**
   - **`automated: true`:** stage 2 (irrigation, phenology) runs it.
   - **`automated: false`:** a manual record.
   - **`plan`:** what the planner predicted. It is `null` when the planner
     could not judge.

`GET /cycles` and `GET /cycles/{id}` return the same shape.

---

## 6. Confirming the harvest

**This is the only way a lot is born.**

```http
POST /cycles/5/harvest
{ "harvested_on": "2027-03-02", "quantity_kg": 5200.5, "grade": "first" }
```

**Response: 201.**
```json
{
  "code": "FP-2-20270302-1",
  "cycle_id": 5, "plot_id": 2, "crop": "soybean",
  "harvested_on": "2027-03-02", "quantity_kg": 5200.5, "grade": "first",
  "passport_path": "/trace/FP-2-20270302-1"
}
```

**The rules.**

| Rule | Error |
|---|---|
| The cycle is `active`: it was not harvested before | 409 `InvalidTransitionError` |
| `harvested_on` is after the sowing date and not in the future | 422 `InvalidHarvestError` |
| `quantity_kg` is above 0 and at most 100 000 kg per hectare of the plot | 422 `InvalidHarvestError` |
| `grade` is `extra`, `first` or `second` | 422 (validation) |
| No task of the cycle is waiting for approval or scheduled. Approve or reject them first | 409 `OpenTasksError` |

**After the harvest.**
- The cycle is `completed`, with `harvested_on` and `lot_code` set. It
  never becomes active again.
- `GET /plots/{id}/lots` lists the plot's lots.

---

## 7. The public passport

This route is **public**: no token. It is what the QR code on the product
opens.

```http
GET /trace/FP-2-20270302-1
```

```json
{
  "lot_code": "FP-2-20270302-1",
  "crop": "soybean",
  "crop_name": "Soybean",
  "crop_name_es": "Soya",
  "producer": "Producer from La Plata, Huila",
  "municipality": "La Plata",
  "department": "Huila",
  "area_ha": 3.5,
  "sowing_date": "2026-11-09",
  "harvested_on": "2027-03-02",
  "quantity_kg": 5200.5,
  "grade": "first",
  "cultivation": {
    "automated": false,
    "data_source": "declared",
    "irrigation_mm_total": null,
    "irrigation_events": null,
    "inputs_applied": []
  },
  "plan": {
    "known": true,
    "followed_recommendation": true,
    "own_risk": false,
    "model": "planner-2026-11-03",
    "rank": 1,
    "predicted_rel_yield_p50": 0.72,
    "predicted_p_success": 0.93
  },
  "integrity": {
    "verified": true,
    "chain_head": "9f2c…",
    "source_digest": "41ab…",
    "trace_events": 4
  },
  "journey": [
    { "step": "commissioning", "on": "2027-03-02", "quantity_kg": 5200.5, "place": null },
    { "step": "shipping", "on": "2027-03-03", "quantity_kg": 5000.0, "place": "FieldPilot Bogotá D.C. warehouse" },
    { "step": "receiving", "on": "2027-03-04", "quantity_kg": 4980.0, "place": "FieldPilot Bogotá D.C. warehouse" },
    { "step": "retail_selling", "on": "2027-03-06", "quantity_kg": 3.0, "place": null }
  ]
}
```

**How to show it.**
- **The QR** encodes the front end's page for the lot, for example
  `https://<front>/trazabilidad/FP-2-20270302-1`. That page calls this
  route.
- **`cultivation.data_source`:**
  - `measured`: stage 2 recorded the water and inputs. Show the totals.
  - `declared`: a manual cycle. The totals are `null`; show "recorded by
    the producer".
- **`inputs_applied`** lists `{ "type": "fertilizer" | "agrochemical",
  "date": "YYYY-MM-DD" }`.
- **`plan`:**
  - `known: false` means the cycle predates the sowing confirmation (the
    demo seed). Show "no planning information".
  - `followed_recommendation: false` comes with `own_risk: true`: the
    farmer chose that crop or date on purpose.
- **`integrity.verified`:**
  - `true`: show a "Verified" badge.
  - `false`: someone changed the records after the harvest. Show a warning;
    never hide it.
- **`journey`** is the lot's chain in order: harvest, the trip to the
  warehouse, the receipt, and every sale handed to a customer (D085). Draw
  it as a timeline.
- **Never shown, by design:** coordinates, people's names, phone numbers,
  sensor readings and prices.

**Error:** 404 `NotFoundError` for an unknown code.

---

## 8. Selling the harvest (farmer and warehouse)

A lot is born at the harvest (§6). The farmer lists it, takes it to a
warehouse, and an operator confirms the receipt; only then can customers buy
it. Money is in Colombian pesos (`*_cop`), quantities in kilograms (D085).

### 8.1 Warehouses

```http
GET /warehouses
```
```json
[ { "id": 1, "code": "BOG-01", "name": "FieldPilot Bogotá D.C. warehouse",
    "municipality": "Bogotá, D.C.", "department": "Bogotá, D.C.", "cold_storage": true } ]
```

### 8.2 List a lot (farmer)

```http
POST /lots/FP-2-20270302-1/listings
{ "farmer_price_per_kg_cop": 3000, "quantity_kg": 5000, "warehouse_id": 1 }
```

**Response: 201.**
```json
{
  "id": 4, "lot_code": "FP-2-20270302-1", "crop": "soybean", "crop_name": "Soybean",
  "status": "awaiting_delivery", "quantity_kg": 5000,
  "farmer_price_per_kg_cop": 3000.0, "shelf_price_per_kg_cop": 3450.0, "farmer_share_pct": 87.0,
  "warehouse": { "id": 1, "code": "BOG-01", "name": "FieldPilot Bogotá D.C. warehouse" },
  "stock_kg": 0.0, "sold_kg": 0.0, "payouts_cop": 0.0, "shipment": null,
  "best_before": "2027-08-29", "days_left": 180, "clearance": null
}
```

**The fields.**
- **`warehouse_id`** is optional; the default is the Bogotá warehouse.
- **`quantity_kg`** is a whole number and at most the harvested kg.
- **The price:** the shelf price adds COP 300/kg of logistics and 5 % of
  the farmer's price for the platform. Show `farmer_share_pct`: the farmer
  never gets less than 80 %.

**Errors.**

| Code | Error | Meaning |
|---|---|---|
| 403 | `ForbiddenError` | Not a member of the lot's plot |
| 409 | `ListingStateError` | The lot already has a listing |
| 422 | `PriceTooLowError` | The farmer's share would fall under 80 %; raise the price |

### 8.3 Take it to the warehouse (farmer), receive it (operator)

```http
POST /listings/4/dispatch          → 201 { "id": 9, "listing_id": 4, "warehouse": {...}, "status": "dispatched",
                                            "dispatched_kg": 5000.0, "received_kg": null, "temperature_c": null }
POST /shipments/9/receive          { "received_kg": 4980, "temperature_c": 8.5 }   (operator or admin)
                                   → 200 the listing, now "active", with "stock_kg": 4980.0
```

**The rules.**
- **What the operator records.** `received_kg` is at most what was
  dispatched; the difference is recorded as shrinkage.
- **Each step adds a trace event to the lot's passport:** `shipping` at
  dispatch, then `receiving` at the receipt.
- **Withdrawing.** `POST /listings/4/withdraw` cancels a listing that has
  not been dispatched yet.

### 8.4 Offers of the day (farmer)

```http
POST /listings/4/offers
{ "discount_pct": 15, "starts_on": "2027-03-05", "ends_on": "2027-03-07" }
```

- **The discount** is 1 to 30 % off the farmer's price, for at most 7 days,
  on an active listing.
- **The guard still holds:** if the discount would drop the farmer's share
  under 80 %, it is 422 `PriceTooLowError`.
- **`GET /listings`** shows the farmer each listing with its stock, the kg
  sold and the payouts earned.

### 8.5 Clearance before the shelf life ends (automatic, D086)

Nobody creates these: the price drops by itself as the best-before day
nears. **The best-before day** is the harvest day plus the crop's shelf
life (`config/market.yaml`, for example 14 days for tomato). The discount
follows the share of shelf life left:

| Life left | Discount | Tomato (14 days) |
|---|---|---|
| 40 % or less | 10 % | from 5 days left |
| 20 % or less | 20 % | from 2 days left |
| 10 % or less | 35 % | from 1 day left |

**The rules.**
- **The deepest discount applies:** the farmer's offer or the clearance
  step, never both.
- **The farmer's share stays at 80 % or more.** A step that would break it
  is reduced until it does not.
- **The farmer sees it in `GET /listings`:** `best_before`, `days_left` and
  `clearance` (`null`, or `{ "discount_pct": 20, "ends_on": "2027-03-15" }`).
- **After the best-before day** the product is no longer sold. The
  operator's `POST /listings/expire` (also run at startup) writes the
  remaining stock off as spoilage, and the listing becomes `expired`:

```http
POST /listings/expire              → 200 [ the listings that expired, as in §8.2 ]
```

---

## 9. The store (customers)

Customers register with `"role": "customer"` (§2.1) and use the same
login and refresh flow. **Every store route needs a customer token**, even
in demo mode, except those marked **public**.

### 9.1 Catalogue and offers (public)

```http
GET /store/products?q=tomato
```
```json
[
  {
    "id": 4, "crop": "soybean", "crop_name": "Soybean", "unit": "kg",
    "price": { "farmer_cop": 2550.0, "logistics_cop": 300.0, "platform_cop": 127.5,
               "total_cop": 2977.5, "farmer_share_pct": 85.6, "discount_pct": 15 },
    "offer": { "source": "offer", "discount_pct": 15, "ends_on": "2027-03-07" },
    "available_kg": 4980.0,
    "harvested_on": "2027-03-02", "best_before": "2027-08-29", "days_left": 175,
    "producer": "Producer from La Plata, Huila",
    "warehouse": "FieldPilot Bogotá D.C. warehouse",
    "lot_code": "FP-2-20270302-1", "passport_path": "/trace/FP-2-20270302-1"
  }
]
```

**How to show it.**
- **The price** is per kg, with the farmer's share visible, which is the
  story of the product.
- **`passport_path`** opens the lot's traceability: harvest, warehouse and
  sale.
- **`GET /store/offers/today`** lists today's validated offers, each with
  its product.
- **`offer.source`** is `offer` (the farmer's) or `clearance` (automatic,
  because the best-before day is near, §8.5). `ends_on` is the last day of
  that price. Show `days_left` next to a clearance price: it is the reason
  for it.

### 9.2 Profile

```http
PUT /store/profile
{ "delivery_address": "Calle 80 # 10-20, Bogotá", "consent_profiling": true }
```

`consent_profiling` turns on the recommendations based on the customer's
own history (Ley 1581 de 2012). Without it, they use only fresh harvests,
offers and popularity.

### 9.3 Cart

```http
PUT /store/cart/items/4      { "quantity_kg": 3 }     (0 removes the line)
GET /store/cart
```
```json
{
  "lines": [ { "listing_id": 4, "crop_name": "Soybean", "quantity_kg": 3,
               "unit_price_cop": 2977.5, "line_total_cop": 8932.5,
               "available_kg": 4980.0, "problem": null } ],
  "total_cop": 8932.5,
  "can_checkout": true
}
```

**How it behaves.**
- **The cart is repriced on every read.** `problem` is `out_of_stock`
  (less stock than asked), `not_available` (the listing is no longer
  sold) or `expired` (past its best-before day, §8.5).
- **`can_checkout`** is false while a line has a problem.

### 9.4 Checkout and the purchase record

```http
POST /store/checkout
{ "delivery_address": "Calle 80 # 10-20, Bogotá" }
```

**Response: 201**, the order:
```json
{
  "id": 12, "status": "paid", "total_cop": 8932.5, "payment_ref": "MOCK-…",
  "delivery_address": "Calle 80 # 10-20, Bogotá",
  "placed_at": "…", "delivered_at": null,
  "lines": [ { "listing_id": 4, "lot_code": "FP-2-20270302-1", "crop": "soybean",
               "crop_name": "Soybean", "quantity_kg": 3, "unit_price_cop": 2977.5,
               "line_total_cop": 8932.5, "producer": "Producer from La Plata, Huila",
               "passport_path": "/trace/FP-2-20270302-1" } ]
}
```

**The rules.**
- **The delivery address** is optional when the profile has one.
- **Errors:**
  - 409 `EmptyCartError`;
  - 409 `OutOfStockError`: read the cart again;
  - 402 `PaymentDeclinedError`: never with the mock gateway.
- **The purchase record:** `GET /store/orders` lists the customer's orders,
  newest first; `GET /store/orders/{id}` returns one.
- **Cancelling.** `POST /store/orders/{id}/cancel` cancels a `paid` order
  and returns its stock.
- **Delivery.** The operator hands the order over with
  `POST /orders/{id}/deliver`. The order becomes `delivered`, and the
  passport gains a `retail_selling` event.

### 9.5 Recommendations and the shopping assistant

```http
GET /store/recommendations?k=5
```
```json
[ { "product": { "id": 4, "crop_name": "Soybean", "...": "..." }, "score": 1.42,
    "reasons": ["REPURCHASE_DUE", "ON_OFFER"],
    "evidence": { "last_bought": "2027-02-20", "median_interval_days": 7, "discount_pct": 15 } } ]
```

**Reason codes**, to show as short tags:

| Code | Tag |
|---|---|
| `REPURCHASE_DUE` | "time to buy again" |
| `BOUGHT_TOGETHER` | "goes with what you buy" |
| `FRESH_HARVEST` | "just harvested" |
| `ON_OFFER` | "offer of the day" |
| `POPULAR` | "popular" |

```http
POST /store/assistant
{ "question": "I'm cooking for six on Sunday, what do I need?" }
```
```json
{ "answer": "…", "proposal": { "id": 3, "items": [ { "listing_id": 4, "quantity_kg": 2 } ],
                               "note": "…", "status": "open" },
  "run_id": "…" }
```

**How it works.**
- **What the assistant does.** It reads the customer's history,
  recommendations and today's offers. It may **propose** a cart; it never
  buys.
- **Accepting a proposal.** Show the proposal with an "Add to cart" button,
  which calls `POST /store/cart-proposals/{id}/accept` and returns the
  cart.
- **Without a model.** Under `MOCK_LLM=1` the assistant answers 503
  (`ChatUnavailableError`). Everything else in the store works without a
  model.

---

## 10. Errors

Errors raised by the backend's own code share one shape:

```json
{ "error": "OwnRiskRequiredError", "message": "Soybean is not among the recommended crops for that week…" }
```

A malformed body (a wrong type, a missing field) is caught earlier, by
FastAPI's validation, with its own shape:

```json
{ "detail": [ { "loc": ["body", "area_ha"], "msg": "Input should be greater than 0", "type": "greater_than" } ] }
```

Both are 422. Tell them apart by the key: `error` or `detail`.

| Code | When |
|---|---|
| 401 | No token, an expired or forged token, or a wrong login. Comes with `WWW-Authenticate: Bearer` |
| 403 | The role or the plot membership does not allow it |
| 404 | The plot, cycle, lot or crop does not exist |
| 402 | The payment was declined |
| 409 | The state does not allow it now: an active cycle, open tasks, a site not ready, a phone already taken, out of stock, an empty cart |
| 422 | The data breaks a rule |
| 423 | The account is locked |
| 503 | The language model is unavailable (chat), with a fixed message |

---

## 11. Values and enums

| Field | Values |
|---|---|
| `role` | `farmer`, `customer`, `operator`, `admin` |
| Site `status` | `missing`, `pending`, `ready`, `failed` |
| Cycle `status` | `active`, `completed` |
| `grade` | `extra`, `first`, `second` |
| Planner crops | `maize`, `common_bean`, `sorghum`, `soybean`, `groundnut`, `cotton`, `tomato`, `potato` |
| Automated crops (stage 2) | `maize` (one YAML per crop in `config/crops/`) |
| Trace `biz_step` | `commissioning`, `shipping`, `receiving`, `retail_selling` (D085) |
| Listing `status` | `awaiting_delivery`, `in_transit`, `active`, `sold_out`, `withdrawn`, `expired` |
| Offer `source` | `offer`, `clearance` (D086) |
| Order `status` | `paid`, `delivered`, `cancelled` |
| Recommendation reasons | `REPURCHASE_DUE`, `BOUGHT_TOGETHER`, `FRESH_HARVEST`, `ON_OFFER`, `POPULAR` |

Crop names come with each outlook (`name`) and with the passport
(`crop_name`) in `APP_LANGUAGE`; `name_es` and `crop_name_es` always carry the
Spanish name.
