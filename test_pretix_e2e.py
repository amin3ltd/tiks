"""
Browser-level pretix smoke test for the local server on port 8000.

Run with:
    pytest -q test_pretix_e2e.py -s

The test intentionally does not read .env files or require environment
configuration. It assumes the local development server is already running at
http://localhost:8000 with the default admin account admin@localhost / admin.
"""

import datetime as dt
import pathlib
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

import pytest

try:
    from playwright.sync_api import BrowserContext, Locator, Page, expect, sync_playwright
except ModuleNotFoundError:
    BrowserContext = Locator = Page = object
    expect = sync_playwright = None
    HAS_PLAYWRIGHT = False
else:
    HAS_PLAYWRIGHT = True


pytestmark = pytest.mark.skipif(
    not HAS_PLAYWRIGHT,
    reason="Playwright is required for this browser E2E test. Install it with `pip install playwright`.",
)


BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@localhost"
ADMIN_PASSWORD = "admin"
ORGANIZER_NAME = "Abebe"
ORGANIZER_SLUG = "abe"
EVENT_NAME = "Simple Community Festival"
EVENT_SLUG = f"simple-festival-e2e-{int(time.time())}"
TICKET_NAME = "General Admission"
CUSTOMER_EMAIL = f"pretix-e2e-{int(time.time())}@example.test"
CUSTOMER_NAME = "Mulugeta Bekele"
CUSTOMER_PHONE = "+251911123456"
HEADLESS = True

SCREENSHOT_DIR = pathlib.Path("e2e_screenshots")
REPORT_PATH = pathlib.Path("pretix_e2e_ux_report.md")


@dataclass
class Finding:
    title: str
    detail: str
    screenshot: Optional[str] = None


@dataclass
class RunState:
    order_code: Optional[str] = None
    checkin_list_id: Optional[str] = None
    findings: list[Finding] = field(default_factory=list)
    ok: list[str] = field(default_factory=list)

    def add_ok(self, message: str) -> None:
        self.ok.append(message)

    def add_issue(self, title: str, detail: str, screenshot: Optional[pathlib.Path] = None) -> None:
        self.findings.append(Finding(title, detail, str(screenshot) if screenshot else None))

    def save_report(self) -> None:
        lines = [
            "# pretix Browser E2E Report",
            f"Generated: {dt.datetime.utcnow().isoformat()} UTC",
            f"Base URL: {BASE_URL}",
            f"Organizer: {ORGANIZER_SLUG}",
            f"Event slug: {EVENT_SLUG}",
            "",
            "## Passed Checks",
        ]
        lines.extend(f"- OK: {m}" for m in self.ok)
        lines.append("")
        lines.append("## Problems Captured")
        if self.findings:
            for finding in self.findings:
                lines.append(f"- ISSUE: **{finding.title}** - {finding.detail}")
                if finding.screenshot:
                    lines.append(f"  Screenshot: `{finding.screenshot}`")
        else:
            lines.append("- No browser, route, or workflow problems captured.")
        REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(scope="session")
def browser_context() -> BrowserContext:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(viewport={"width": 1366, "height": 900})
        yield context
        context.close()
        browser.close()


@pytest.fixture
def state() -> RunState:
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    return RunState()


@pytest.fixture
def page(browser_context: BrowserContext, request, state: RunState) -> Page:
    page = browser_context.new_page()
    page.set_default_timeout(15000)
    page.on("console", lambda msg: record_console_issue(page, state, msg))
    page.on("pageerror", lambda exc: state.add_issue("JavaScript error", str(exc), take_screenshot(page, "js_error")))
    page.on("requestfailed", lambda req: record_failed_request(state, req))
    page.on("response", lambda resp: record_bad_response(page, state, resp))
    yield page
    if getattr(request.node, "rep_call", None) and request.node.rep_call.failed:
        take_screenshot(page, f"{request.node.name}_failure")
    page.close()


def record_console_issue(page: Page, state: RunState, msg) -> None:
    if msg.type in {"error", "warning"}:
        text = msg.text
        if "favicon" in text.lower():
            return
        state.add_issue(f"Browser console {msg.type}", text, take_screenshot(page, f"console_{msg.type}"))


def record_bad_response(page: Page, state: RunState, response) -> None:
    if response.status >= 500:
        state.add_issue("Browser HTTP error", f"{response.status} {response.url}", take_screenshot(page, "http_error"))


def record_failed_request(state: RunState, request) -> None:
    failure = request.failure or ""
    if "ERR_ABORTED" in failure:
        return
    state.add_issue("Browser request failed", f"{request.method} {request.url}: {failure}")


def take_screenshot(page: Page, label: str) -> pathlib.Path:
    filename = SCREENSHOT_DIR / f"{label}_{int(time.time() * 1000)}.png"
    page.screenshot(path=str(filename), full_page=True)
    return filename


def visible_first(locators: Iterable[Locator]) -> Optional[Locator]:
    for locator in locators:
        try:
            if locator.count() and locator.first.is_visible():
                return locator.first
        except Exception:
            continue
    return None


def editable_first(locators: Iterable[Locator]) -> Optional[Locator]:
    for locator in locators:
        try:
            if not locator.count():
                continue
            field = locator.first
            if field.is_visible() and field.is_editable():
                return field
        except Exception:
            continue
    return None


def open_page(page: Page, state: RunState, path: str, title: str, allow_404: bool = False) -> None:
    response = page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    status = response.status if response else 0
    if status >= 500 or (status == 404 and not allow_404):
        shot = take_screenshot(page, f"http_{status}_{slugify(title)}")
        state.add_issue("Broken route", f"{path} returned HTTP {status}", shot)
        raise AssertionError(f"{path} returned HTTP {status}")
    body = page.locator("body")
    expect(body).not_to_contain_text(re.compile(r"Internal Server Error|Traceback|OperationalError", re.I))
    state.add_ok(f"{title} loaded ({path})")


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def candidates_by_text(page: Page, names: Iterable[str]) -> list[Locator]:
    candidates: list[Locator] = []
    for name in names:
        pattern = re.compile(re.escape(name), re.I)
        candidates.extend([
            page.get_by_role("button", name=pattern),
            page.get_by_role("link", name=pattern),
            page.locator(f"button:has-text('{name}')"),
            page.locator(f"a:has-text('{name}')"),
            page.locator(f"input[type='submit'][value*='{name}']"),
        ])
    return candidates


def click_action(page: Page, names: Iterable[str], description: str) -> None:
    target = visible_first(candidates_by_text(page, names))
    if not target:
        raise AssertionError(f"Could not find action: {description}")
    target.scroll_into_view_if_needed()
    target.click()
    page.wait_for_load_state("domcontentloaded")


def wait_for_action(page: Page, names: Iterable[str], description: str, timeout: int = 45000) -> None:
    deadline = time.time() + timeout / 1000
    last_text = ""
    while time.time() < deadline:
        target = visible_first(candidates_by_text(page, names))
        if target:
            return
        last_text = page.locator("body").inner_text()[:1200]
        page.wait_for_timeout(500)
    raise AssertionError(f"Could not find action after waiting: {description}. Page text: {last_text}")


def fill_field(page: Page, names: Iterable[str], value: str, description: str) -> None:
    candidates: list[Locator] = []
    for name in names:
        pattern = re.compile(re.escape(name), re.I)
        candidates.extend([
            page.locator(f"input[name='{name}']"),
            page.locator(f"textarea[name='{name}']"),
            page.locator(f"input[id*='{name}']"),
            page.locator(f"textarea[id*='{name}']"),
            page.get_by_placeholder(pattern),
            page.get_by_label(pattern).locator("input, textarea"),
            page.get_by_label(pattern),
        ])
    field = editable_first(candidates)
    if not field:
        raise AssertionError(f"Could not find field: {description}")
    field.scroll_into_view_if_needed()
    field.fill(value)


def set_checkbox(page: Page, selector: str, checked: bool = True) -> None:
    box = page.locator(selector).first
    if box.count() and box.is_visible() and box.is_checked() != checked:
        box.check() if checked else box.uncheck()


def guarded_step(state: RunState, page: Page, title: str, step: Callable[[], None], required: bool = True) -> None:
    try:
        step()
        state.add_ok(title)
    except Exception as exc:
        shot = take_screenshot(page, slugify(title))
        state.add_issue(title, str(exc), shot)
        if required:
            raise


def login_control_panel(page: Page, state: RunState, email: str = ADMIN_EMAIL, password: str = ADMIN_PASSWORD) -> None:
    page.context.clear_cookies()
    open_page(page, state, "/control/login", "Control login page")
    fill_field(page, ["email", "Email"], email, "login email")
    fill_field(page, ["password", "Password"], password, "login password")
    click_action(page, ["Log in", "Sign in", "Login"], "login")
    expect(page).to_have_url(re.compile(r"/control"))


def ensure_organizer(page: Page, state: RunState) -> None:
    open_page(page, state, f"/control/organizer/{ORGANIZER_SLUG}/", "Organizer dashboard", allow_404=True)
    if page.locator("body").inner_text().lower().find("page not found") == -1:
        expect(page.locator("body")).to_contain_text(re.compile(ORGANIZER_NAME, re.I))
        return

    open_page(page, state, "/control/organizers/add", "Organizer creation")
    fill_field(page, ["name"], ORGANIZER_NAME, "organizer name")
    fill_field(page, ["slug"], ORGANIZER_SLUG, "organizer slug")
    click_action(page, ["Create", "Save"], "save organizer")
    open_page(page, state, f"/control/organizer/{ORGANIZER_SLUG}/", "New organizer dashboard")


def create_simple_event(page: Page, state: RunState) -> None:
    open_page(page, state, f"/control/organizer/{ORGANIZER_SLUG}/", "Organizer dashboard before event create")
    click_action(page, ["Create event", "New event"], "event creation")
    if page.locator("text=/Create a new event.*Step 1/i").count():
        click_action(page, ["Continue", "Next"], "continue event wizard")
    fill_field(page, ["basics-name_0", "name", "Event name"], EVENT_NAME, "event name")
    fill_field(page, ["basics-slug", "slug", "Event slug"], EVENT_SLUG, "event slug")
    start_date = (dt.date.today() + dt.timedelta(days=21)).isoformat()
    end_date = (dt.date.today() + dt.timedelta(days=22)).isoformat()
    fill_field(page, ["basics-date_from_0", "date_from", "Start date"], start_date, "event start date")
    if page.locator("input[name='basics-date_from_1']").count():
        fill_field(page, ["basics-date_from_1"], "10:00:00", "event start time")
    if page.locator("input[name='basics-date_to_0'], input[name='date_to']").count():
        fill_field(page, ["basics-date_to_0", "date_to", "End date"], end_date, "event end date")
    if page.locator("input[name='basics-date_to_1']").count():
        fill_field(page, ["basics-date_to_1"], "18:00:00", "event end time")
    timezone = page.locator("select[name='basics-timezone'], select[name='timezone']").first
    if timezone.count() and timezone.is_visible():
        timezone.select_option(value="Africa/Addis_Ababa")
    if page.locator("textarea[name='basics-location_0'], input[name='location']").count():
        fill_field(page, ["basics-location_0", "location", "Venue"], "Meskel Square, Addis Ababa", "event venue")
    set_checkbox(page, "input[name='basics-no_taxes']", True)
    click_action(page, ["Continue", "Create event", "Create", "Save"], "save event")
    if page.locator("text=/Sales tax rate|tax rate/i").count():
        set_checkbox(page, "input[name='basics-no_taxes']", True)
        click_action(page, ["Continue", "Create event", "Save"], "continue without tax")
    if page.locator("text=/Create a new event.*Step/i").count():
        click_action(page, ["Continue", "Create event"], "finish event wizard")
    open_page(page, state, f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/", "Event dashboard")


def create_product_and_quota(page: Page, state: RunState) -> None:
    open_page(page, state, f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/items/add", "Product creation")
    fill_field(page, ["name", "Item name", "Product name"], TICKET_NAME, "ticket name")
    fill_field(page, ["price", "Price"], "0.00", "ticket price")
    if page.locator("input[name='admission']").count():
        set_checkbox(page, "input[name='admission']", True)
    click_action(page, ["Create", "Save", "Add"], "save product")

    open_page(page, state, f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/quotas/add", "Quota creation")
    fill_field(page, ["name"], "Simple ticket quota", "quota name")
    fill_field(page, ["size", "Quota"], "25", "quota size")
    checkbox = page.locator("label").filter(has_text=TICKET_NAME).locator("input[type='checkbox']").first
    if checkbox.count() and checkbox.is_visible():
        checkbox.check()
    else:
        set_checkbox(page, "input[name='itemvars']", True)
    click_action(page, ["Save", "Create"], "save quota")


def create_checkin_list(page: Page, state: RunState) -> None:
    open_page(page, state, f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/checkinlists/add", "Check-in list creation")
    fill_field(page, ["name"], "Default", "check-in list name")
    set_checkbox(page, "input[name='all_products']", True)
    click_action(page, ["Save", "Create"], "save check-in list")
    body = page.locator("body").inner_text()
    match = re.search(r"/checkinlists/(\d+)/change", page.content())
    if not match:
        match = re.search(r"/checkinlists/(\d+)/", page.content())
    if match:
        state.checkin_list_id = match.group(1)
    elif "Default" not in body:
        raise AssertionError("Check-in list did not appear after creation")


def publish_event(page: Page, state: RunState) -> None:
    open_page(page, state, f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/live/", "Publish page")
    if visible_first(candidates_by_text(page, ["Take it live now", "Publish", "Go live"])):
        click_action(page, ["Take it live now", "Publish", "Go live"], "publish event")
        if visible_first(candidates_by_text(page, ["Confirm", "Yes", "Go live"])):
            click_action(page, ["Confirm", "Yes", "Go live"], "confirm publish")
    elif page.locator("input[name='live']").count():
        set_checkbox(page, "input[name='live']", True)
        click_action(page, ["Save"], "save live state")
    open_page(page, state, f"/{ORGANIZER_SLUG}/{EVENT_SLUG}/", "Public event page")


def complete_public_checkout(page: Page, state: RunState) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    open_page(page, state, f"/{ORGANIZER_SLUG}/{EVENT_SLUG}/", "Public event mobile")
    expect(page.locator("body")).to_contain_text(EVENT_NAME)
    quantity = page.locator("input[type='number'], input[name*='count']").first
    if quantity.count() and quantity.is_visible():
        quantity.fill("1")
    click_action(page, ["Add to cart", "Register", "Book"], "add ticket")
    wait_for_action(page, ["Continue", "Next", "Checkout"], "continue checkout")
    click_action(page, ["Continue", "Next", "Checkout"], "continue checkout")
    fill_field(page, ["email", "Email"], CUSTOMER_EMAIL, "buyer email")
    fill_field(page, ["name", "Full name", "Name"], CUSTOMER_NAME, "buyer name")
    if page.locator("input[name='phone']").count():
        fill_field(page, ["phone", "Phone"], CUSTOMER_PHONE, "buyer phone")
    click_action(page, ["Continue", "Next", "Review"], "continue buyer details")
    if visible_first(candidates_by_text(page, ["Free order", "Complete without payment"])):
        click_action(page, ["Free order", "Complete without payment"], "free order")
    click_action(page, ["Place order", "Complete order", "Submit registration"], "place order")
    expect(page.locator("body")).to_contain_text(
        re.compile(r"Thank you|Order completed|order has been placed|order is complete", re.I),
        timeout=30000,
    )
    text = page.locator("body").inner_text()
    match = re.search(r"\bOrder\s+([A-Z0-9]{5,})\b", text)
    state.order_code = match.group(1).upper() if match else None
    take_screenshot(page, "public_order_confirmation")
    page.set_viewport_size({"width": 1366, "height": 900})


def verify_order_management(page: Page, state: RunState) -> None:
    login_control_panel(page, state)
    if state.order_code:
        open_page(page, state, f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/orders/{state.order_code}/", "Order detail")
        expect(page.locator("body")).to_contain_text(re.compile(re.escape(CUSTOMER_NAME), re.I))
    else:
        open_page(page, state, f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/orders/", "Order list")
        expect(page.locator("body")).to_contain_text(re.compile(CUSTOMER_NAME, re.I))


def probe_organizer_routes(page: Page, state: RunState) -> None:
    routes = [
        (f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/", "event dashboard"),
        (f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/items/", "products"),
        (f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/quotas/", "quotas"),
        (f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/orders/", "orders"),
        (f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/checkins/", "check-ins"),
        (f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/checkinlists/", "check-in lists"),
        (f"/control/organizer/{ORGANIZER_SLUG}/devices", "devices"),
        (f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/settings/", "event settings"),
    ]
    for path, title in routes:
        guarded_step(state, page, f"Route probe: {title}", lambda p=path, t=title: open_page(page, state, p, t), required=False)


def verify_checkin_workflow(page: Page, state: RunState) -> None:
    open_page(page, state, f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/checkinlists/", "Check-in lists")
    if not state.checkin_list_id:
        match = re.search(r"/checkinlists/(\d+)/change", page.content())
        if match:
            state.checkin_list_id = match.group(1)
    if not state.checkin_list_id:
        raise AssertionError("No check-in list id found")
    open_page(
        page,
        state,
        f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/checkinlists/{state.checkin_list_id}/change",
        "Check-in list edit",
    )
    expect(page.locator("body")).to_contain_text(re.compile("Check-in list", re.I))
    click_action(page, ["Save"], "save check-in list without changes")
    expect(page.locator("body")).to_contain_text(re.compile("saved|Check-in list", re.I))
    open_page(
        page,
        state,
        f"/control/event/{ORGANIZER_SLUG}/{EVENT_SLUG}/checkinlists/{state.checkin_list_id}/simulator",
        "Check-in simulator",
    )
    expect(page.locator("body")).to_contain_text(re.compile("Simulator|Barcode|Check-in", re.I))


def verify_device_pages(page: Page, state: RunState) -> None:
    open_page(page, state, f"/control/organizer/{ORGANIZER_SLUG}/devices", "Device list")
    if visible_first(candidates_by_text(page, ["Create device", "Add device", "New device"])):
        click_action(page, ["Create device", "Add device", "New device"], "add device")
        if page.locator("input[name='name']").count():
            fill_field(page, ["name"], "E2E scanner", "device name")
        if page.locator("select[name='all_events']").count():
            pass
        if visible_first(candidates_by_text(page, ["Save", "Create"])):
            click_action(page, ["Save", "Create"], "save device")


def test_pretix_full_browser_functionality(page: Page, state: RunState) -> None:
    try:
        guarded_step(state, page, "Login works", lambda: login_control_panel(page, state))
        guarded_step(state, page, "Organizer exists or can be created", lambda: ensure_organizer(page, state))
        guarded_step(state, page, "Organizer can create an event", lambda: create_simple_event(page, state))
        guarded_step(state, page, "Organizer can create products and quotas", lambda: create_product_and_quota(page, state))
        guarded_step(state, page, "Organizer can create check-in list", lambda: create_checkin_list(page, state))
        guarded_step(state, page, "Organizer can publish event", lambda: publish_event(page, state))
        guarded_step(state, page, "Customer can complete public checkout", lambda: complete_public_checkout(page, state))
        guarded_step(state, page, "Organizer can manage public order", lambda: verify_order_management(page, state))
        guarded_step(state, page, "Organizer route probes do not crash", lambda: probe_organizer_routes(page, state), required=False)
        guarded_step(state, page, "Check-in edit and simulator work", lambda: verify_checkin_workflow(page, state), required=False)
        guarded_step(state, page, "Device pages are usable", lambda: verify_device_pages(page, state), required=False)
    finally:
        state.save_report()
        print(f"E2E report saved to {REPORT_PATH}")

    assert not state.findings, "\n".join(f"{f.title}: {f.detail}" for f in state.findings)
