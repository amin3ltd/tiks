# tiks role documentation app

This folder contains the static documentation web app used by tiks.

## How it works

Open one role at a time:

```text
index.html?role=customer
index.html?role=organizer
index.html?role=staff
index.html?role=checkin
index.html?role=admin
index.html?role=all
```

The main tiks system links to the static copy at `/static/tiksdocs/index.html` and passes the role in the query string. Customer pages link to the customer guide. Organizer and event pages link to organizer or staff guides. Administrator pages link to the admin guide.

This is role-separated documentation, not a security boundary. Real access control still belongs to the tiks application permissions.

## Screenshots

The `screenshots/` folder uses real screenshots captured from this repository's end-to-end runs:

- `admin-login.png`
- `organizer-event-created.png`
- `customer-event-page.png`
- `customer-checkout.png`
- `checkin-devices.png`

Replace these files when the product UI changes significantly.

## Local preview

```bash
cd docs
python3 -m http.server 8080
```

Then open:

```text
http://localhost:8080/?role=customer
```
