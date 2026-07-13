import csv, os, re, time, requests, hashlib
from datetime import date, datetime
from bs4 import BeautifulSoup

BASE = "http://ufcstats.com"
EVENTS_URL = f"{BASE}/statistics/events/completed?page=all"
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "fights.csv")
YEARS = 12
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
FIELDS = ["fight_id", "date", "event", "fighter_a", "fighter_b", "winner",
          "weight_class", "method", "round", "time",
          "kd_a", "kd_b", "str_a", "str_b", "td_a", "td_b", "sub_a", "sub_b"]
STAT_COLS = {"kd": 2, "str": 3, "td": 4, "sub": 5}

def to_int(val):
    match = re.search(r"-?\d+", val or "")
    return int(match.group()) if match else 0

def clean_text(val):
    return re.sub(r"\s+", " ", (val or "").strip())

def col_val(cols, i, j=0):
    if i < len(cols) and j < len(cols[i]):
        return cols[i][j]
    return ""

def fetch(session, url):
    html = session.get(url, headers=HEADERS, timeout=30).text
    if "Checking your browser" in html:
        nonce = re.search(r'nonce="([a-f0-9]+)"', html).group(1)
        zeros = int(re.search(r"Array\((\d+)\+1\)\.join\('0'\)", html).group(1))
        target = "0" * zeros
        n = 0
        while not hashlib.sha256(f"{nonce}:{n}".encode()).hexdigest().startswith(target):
            n += 1
        session.post(f"{BASE}/__c", data={"nonce": nonce, "n": n}, headers=HEADERS, timeout=30)
        html = session.get(url, headers=HEADERS, timeout=30).text
    return html

def parse_events(html):
    """Return [(event_url, date)] for events within the last YEARS years."""
    soup = BeautifulSoup(html, "html.parser")
    cutoff = date(date.today().year - YEARS, date.today().month, date.today().day)
    events = []
    for row in soup.select("tr.b-statistics__table-row"):
        link = row.select_one("a.b-link[href*='event-details']")
        date_el = row.select_one("span.b-statistics__date")
        if not link or not date_el:
            continue
        try:
            when = datetime.strptime(date_el.get_text(strip=True), "%B %d, %Y").date()
        except ValueError:
            continue
        if cutoff <= when <= date.today():
            events.append((link["href"], when))
    return events

def parse_event(html, event_date):
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.select_one("h2")
    event_name = clean_text(heading.get_text()) if heading else ""
    fights = []
    for row in soup.select("tr.b-fight-details__table-row[data-link]"):
        cols = [[p.get_text(strip=True) for p in c.select("p")]
                for c in row.select("td.b-fight-details__table-col")]

        fighter_a = clean_text(col_val(cols, 1, 0))
        fighter_b = clean_text(col_val(cols, 1, 1))
        if not fighter_a or not fighter_b:
            continue

        flags = [f.get_text(strip=True).lower() for f in row.select("i.b-flag__text")]
        winner = "draw" if "draw" in flags else "nc" if "nc" in flags else fighter_a

        fight = {
            "fight_id": row["data-link"].rsplit("/", 1)[-1],
            "date": event_date.isoformat(),
            "event": event_name,
            "fighter_a": fighter_a,
            "fighter_b": fighter_b,
            "winner": winner,
            "weight_class": clean_text(col_val(cols, 6, 0)),
            "method": clean_text(col_val(cols, 7, 0)),
            "round": to_int(col_val(cols, 8, 0)),
            "time": clean_text(col_val(cols, 9, 0)),
        }
        for name, i in STAT_COLS.items():
            fight[f"{name}_a"] = to_int(col_val(cols, i, 0))
            fight[f"{name}_b"] = to_int(col_val(cols, i, 1))
        fights.append(fight)
    return fights

def load_existing():
    if not os.path.exists(CSV_PATH):
        return [], set()
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows, {r["fight_id"] for r in rows}

def main():
    session = requests.Session()
    rows, seen = load_existing()
    print(f"{len(rows)} fights already stored. Fetching event list...")

    events = parse_events(fetch(session, EVENTS_URL))
    print(f"{len(events)} events in the last {YEARS} years.")

    stored_dates = {r["date"] for r in rows}
    oldest_stored = min(stored_dates) if stored_dates else None
    newest_stored = max(stored_dates) if stored_dates else None

    new_rows = []
    for i, (url, when) in enumerate(events, 1):
        if oldest_stored and oldest_stored < when.isoformat() < newest_stored:
            continue
        fights = parse_event(fetch(session, url), when)
        fresh = [fight for fight in fights if fight["fight_id"] not in seen]
        for fight in fresh:
            seen.add(fight["fight_id"])
            new_rows.append(fight)
        print(f"[{i}/{len(events)}] {when}: +{len(fresh)} fights")
        time.sleep(0.3)

    all_rows = rows + new_rows
    all_rows.sort(key=lambda r: r["date"])

    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Added {len(new_rows)} new fights. Total {len(all_rows)} -> {CSV_PATH}")

if __name__ == "__main__":
    main()
