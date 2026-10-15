"""HTTP clients for the mandi data sources (synchronous; jobs run them in a thread)."""
import time
from datetime import date, datetime

import requests

from services.mandi import config

RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Both government APIs block the default "python-requests" User-Agent (403 or a
# silent read timeout), so identify the app honestly instead.
DEFAULT_HEADERS = {
    "User-Agent": "ALIP-mandi-ingest/1.0 (AgriLink Intelligence Platform; academic project)",
    "Accept": "application/json",
}

# Agmarknet 2.0 answers in ~20-25 s; data.gov.in in ~1 s.
AGMARKNET_TIMEOUT = 90.0


def new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    return session


class SourceError(RuntimeError):
    pass


def request_json(session, method: str, url: str, *, params=None, json=None, headers=None,
                 retries: int = 4, backoff: float = 1.5, timeout: float = 30.0,
                 sleep=time.sleep):
    """
    Call an endpoint and decode JSON, retrying on network errors, 429/5xx and
    non-JSON bodies (data.gov.in sometimes answers with a WAF HTML page).
    """
    last_error = None
    for attempt in range(retries + 1):
        try:
            response = session.request(method, url, params=params, json=json,
                                       headers=headers, timeout=timeout)
            if response.status_code in RETRYABLE_STATUS:
                last_error = SourceError(f"HTTP {response.status_code} from {url}")
                retry_after = response.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else backoff * (attempt + 1)
            elif response.status_code >= 400:
                raise SourceError(f"HTTP {response.status_code} from {url}: {response.text[:200]}")
            else:
                try:
                    return response.json()
                except ValueError:
                    last_error = SourceError(f"Non-JSON response from {url}")
                    wait = backoff * (attempt + 1)
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = SourceError(f"Network error calling {url}: {exc}")
            wait = backoff * (attempt + 1)

        if attempt < retries:
            sleep(wait)
    raise last_error


# ─── data.gov.in: current daily mandi prices ───────────────
class DataGovClient:
    def __init__(self, api_key: str = None, page_size: int = None, session=None, sleep=time.sleep):
        self.api_key = api_key or config.datagov_api_key()
        self.page_size = page_size or config.datagov_page_size()
        self.session = session or new_session()
        self.sleep = sleep

    def fetch_commodity(self, commodity_name: str) -> dict:
        """
        Fetch every record for one commodity name. Pages are advanced by the number
        of rows actually returned, so a key that caps pages at 10 rows still
        yields the complete set (the "10-row trap").
        """
        records, offset, total, pages = [], 0, None, 0
        while total is None or offset < total:
            payload = request_json(
                self.session, "GET", config.DATAGOV_URL,
                params={
                    "api-key": self.api_key,
                    "format": "json",
                    "offset": offset,
                    "limit": self.page_size,
                    "filters[commodity]": commodity_name,
                },
                sleep=self.sleep,
            )
            pages += 1
            total = int(payload.get("total") or 0)
            page = payload.get("records") or []
            if not page:
                break
            records.extend(page)
            offset += len(page)
        return {
            "commodity_name": commodity_name,
            "total": total or 0,
            "records": records,
            "pages": pages,
        }


# ─── Agmarknet 2.0: masters and national arrivals ──────────
class AgmarknetClient:
    def __init__(self, session=None, sleep=time.sleep):
        self.session = session or new_session()
        self.sleep = sleep

    def _get_paged(self, path: str, items_key: str, page_size: int) -> list:
        """Collect all pages, de-duplicated by id (pages can overlap)."""
        items, page = {}, 1
        while True:
            payload = request_json(
                self.session, "GET", f"{config.AGMARKNET_BASE}{path}",
                params={"page": page, "page_size": page_size},
                timeout=AGMARKNET_TIMEOUT, sleep=self.sleep,
            )
            new = [item for item in payload.get(items_key) or [] if item.get("id") not in items]
            for item in new:
                items[item.get("id")] = item
            if not new or not (payload.get("pagination") or {}).get("next_page"):
                return list(items.values())
            page += 1

    def commodities(self) -> list:
        return self._get_paged("/commodities", "data", 500)

    def states(self) -> list:
        return self._get_paged("/location/state", "states", 100)

    def national_price_arrivals(self, as_of: date, commodity_ids: list[int]) -> dict:
        """National average price (Rs/quintal) and arrivals (tonnes) for the last 3 reported days."""
        return request_json(
            self.session, "POST", f"{config.AGMARKNET_BASE}/dashboard-data/",
            json={
                "dashboard": "marketwise_price_arrival",
                "date": as_of.isoformat(),
                "commodities": commodity_ids,
                "downloadreport": "false",  # must be the string, not a boolean
                "page": 0,
            },
            timeout=AGMARKNET_TIMEOUT, sleep=self.sleep,
        )


def parse_dashboard_arrivals(payload: dict) -> list[dict]:
    """
    Turn a dashboard-data response into one row per (commodity, day).
    Column titles carry the real dates ("12 Oct, 2026"); arrivals are in tonnes.
    """
    data = payload.get("data") or {}
    titles = {}
    for group in data.get("columns") or []:
        for column in group.get("columns") or []:
            titles[column.get("key")] = column.get("title")

    def title_date(key):
        try:
            return datetime.strptime(titles.get(key, ""), "%d %b, %Y").date().isoformat()
        except ValueError:
            return None

    slots = [
        ("as_on_price", "as_on_arrival"),
        ("one_day_ago_price", "one_day_ago_arrival"),
        ("two_day_ago_price", "two_day_ago_arrival"),
    ]
    rows = []
    for record in data.get("records") or []:
        for price_key, arrival_key in slots:
            day = title_date(price_key) or title_date(arrival_key)
            if not day:
                continue
            rows.append({
                "date": day,
                "commodity_raw": record.get("cmdt_name"),
                "national_price": _to_float(record.get(price_key)),
                "arrival_tonnes": _to_float(record.get(arrival_key)),
            })
    return rows


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ─── CEDA (Ashoka University): historical Agmarknet mirror ─
class CedaClient:
    """
    Request/response shapes follow the public agmarket-mcp client; they could not
    be verified live without a key. Every call is wrapped so shape changes fail loudly.
    """

    def __init__(self, api_key: str = None, session=None, sleep=time.sleep):
        self.api_key = api_key or config.ceda_api_key()
        if not self.api_key:
            raise SourceError("CEDA_API_KEY is not set in backend/.env")
        self.session = session or new_session()
        self.sleep = sleep

    def _call(self, method: str, path: str, body: dict = None) -> list:
        payload = request_json(
            self.session, method, f"{config.CEDA_BASE}{path}", json=body,
            headers={"Authorization": f"Bearer {self.api_key}"}, sleep=self.sleep,
        )
        output = payload.get("output") or {}
        if output.get("type") != "success":
            raise SourceError(f"CEDA {path} failed: {output.get('message') or payload}")
        return output.get("data") or []

    def commodities(self) -> list:
        return self._call("GET", "/agmarknet/commodities")

    def geographies(self) -> list:
        return self._call("GET", "/agmarknet/geographies")

    def markets(self, commodity_id: int, state_id: int) -> list:
        return self._call("POST", "/agmarknet/markets", {
            "commodity_id": commodity_id, "state_id": state_id, "indicator": "price",
        })

    def prices(self, commodity_id: int, state_id: int, from_date: str, to_date: str) -> list:
        return self._call("POST", "/agmarknet/prices", {
            "commodity_id": commodity_id, "state_id": state_id,
            "from_date": from_date, "to_date": to_date,
        })
