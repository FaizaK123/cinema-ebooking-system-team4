# Sprint 3 API (for the frontend)

All endpoints return JSON. Errors look like `{ "error": "message", "errors": { "fieldName": "message" } }`
(`errors` only when a specific field is wrong). Dates are `YYYY-MM-DD`, times are 24-hour `HH:MM`.
Send JSON with `Content-Type: application/json`, except Add Movie (multipart form).

## Customer

| Method + path | Login | What it does |
|---|---|---|
| `GET /api/movies`, `GET /api/movies/<id>` | no | Movies now include real showtimes: `showtimes` (`{date: ["2:00 PM", ...]}`, same shape as before) and `showings` (`[{showId, date, time, timeLabel, showroom, ...}]`). Only upcoming showtimes appear. |
| `GET /api/movies/<id>/showtimes` | no | `{movieId, movieTitle, showtimes: [...]}` |
| `GET /api/ticket-types` | no | `[{type: "ADULT", label, price}, ...]` (Adult 12, Child 8, Senior 9) |
| `GET /api/shows/<showId>` | no | Show details, movie, ticket prices, `availableSeats`, `bookable` |
| `GET /api/shows/<showId>/seats` | no | Seat map: `rows`, `seatsPerRow`, `seats: [{seatId, row, number, label, status}]`, `counts`. `status` is `AVAILABLE`, `BOOKED`, `HELD` (someone else is checking out) or `SELECTED` (this visitor's seats) |
| `POST /api/booking/start` | no | Body `{showId, tickets: {adult, child, senior}}`. Validates counts, returns the total, and starts a new seat choice. |
| `POST /api/booking/seats` | no | Body `{seatIds: [..]}` (plus `showId`, `tickets` if `start` wasn't called). Seat count must equal ticket count. Reserves the seats. `409` + `unavailableSeats` if any seat is taken. |
| `GET /api/booking/current` | no | The booking in progress or `{selection: null}` (use after a refresh or login) |
| `DELETE /api/booking/current` | no | Cancel and release the seats |
| `GET /api/booking/order-summary` | **yes** | "Proceed to Checkout". `401` with `loginRequired: true` if not logged in: send them to the login page, then call it again. Returns movie, show, seats, `tickets` (type, quantity, pricePerTicket, lineTotal), `totalBeforeTax`, `email`, `accountEmail`, `emailConfirmed` |
| `POST /api/booking/email` | **yes** | Body `{email}`; empty body or empty `email` keeps the account email |
| `GET /api/booking/payment` | **yes** | Payment page (mockup) data: `order`, `email`, `savedCards`. `409` with `needsEmail` until the email is confirmed |

Seats are reserved for the browser session when `POST /api/booking/seats` succeeds, and stay reserved through login.
A reservation lasts 5 minutes (`SEAT_HOLD_MINUTES` in `infrastructure/config.py`); each checkout call renews it.
If it lapses, checkout calls return `409` with `expired: true`. Logging out releases the seats.

## Admin (all need the admin login; customers get 403)

| Method + path | What it does |
|---|---|
| `POST /api/admin/movies` | **Multipart form**: `title`, `description`, `releaseDate`, `duration` (minutes), `rating` (G, PG, PG-13, R, NC-17), `genres` (repeat the field once per genre), file field `poster` (JPG/PNG, 5 MB max), optional `trailer` (YouTube embed link), optional `status`. Status defaults from the release date. |
| `GET /api/admin/showrooms` | `[{id, name, capacity, rows, seatsPerRow}]`. Add `?date=&time=` to get `available` per showroom for that moment. |
| `GET /api/admin/showtimes` | All scheduled showtimes (`?movieId=` to filter) |
| `POST /api/admin/showtimes` | Body `{movieId, showroomId, date, time}`. `409` if that showroom already has a showing at that date and time (response lists which showrooms are free). Past times are rejected. |
| `GET /api/admin/promotions` | Saved promotions |
| `POST /api/admin/promotions` | Body `{promoCode, discountPercent, description, startDate, endDate, emailSubject, emailBody, sendEmail?}`. Saves it and emails it to active customers who opted in to promotions (nobody else). `sendEmail: false` only saves. |

## Tests

```
python -m unittest discover -s backend/tests -t .
```
They use a throwaway database and never send real email.
