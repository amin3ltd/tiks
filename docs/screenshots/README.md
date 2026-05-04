# tiks documentation screenshots

The documentation app currently uses real screenshots from the existing end-to-end screenshot set.

## Current files

- `admin-login.png`: admin/control login screen.
- `organizer-event-created.png`: organizer event creation and setup screen.
- `customer-event-page.png`: public customer-facing event page.
- `customer-checkout.png`: customer checkout and confirmation flow.
- `checkin-devices.png`: device and check-in related control pages.

## When to update

Update these screenshots when the matching tiks screens change enough that the documentation no longer looks like the product.

## Capture rules

- Use real tiks screens, not mockups.
- Use English UI text.
- Avoid private customer data, private emails, real payment details, and real event secrets.
- Keep file names stable unless you also update `docs/index.html` and `src/pretix/static/tiksdocs/index.html`.

## Syncing into the app

The docs source lives in `docs/`. The copy served by tiks lives in `src/pretix/static/tiksdocs/`.

After replacing images here, copy them into:

```text
src/pretix/static/tiksdocs/screenshots/
```
