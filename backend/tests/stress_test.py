"""
SpendSense stress test: AI parsing/answers, every API endpoint, auth, bad input,
fuzzing, rate limiting, concurrent load and month/year boundaries.

Run from backend/:
  venv/bin/python tests/stress_test.py

Uses a throwaway SQLite file; never touches spendsense.db. Exits non-zero on failure.
"""
import os, sys, random, string, tempfile, traceback, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from unittest import mock

TMP_DB = os.path.join(tempfile.mkdtemp(), "stress.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TMP_DB}"
os.environ.setdefault("SECRET_KEY", "stress-test-secret")
os.environ.pop("ANTHROPIC_API_KEY", None)  # rule-based path unless a test opts in
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
import mainmenu
from mainmenu import app
from database import models, crud
from database.database import SessionLocal
from ai.parser import parse_intent
from ai.processor import process_ai_query
from ai.schemas import IntentType
from ai import llm

FAILS, PASSES = [], 0

def check(name, cond, detail=""):
    global PASSES
    if cond:
        PASSES += 1
    else:
        FAILS.append(f"{name}: {detail}")

def case(name):
    def deco(fn):
        try:
            fn()
        except Exception as e:
            FAILS.append(f"{name}: EXCEPTION {type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
        return fn
    return deco

client = TestClient(app, raise_server_exceptions=False)
app.state.limiter.enabled = False

NOW = datetime.now()
def months_ago(n, day=10):
    d = NOW.replace(day=1)
    for _ in range(n):
        d = (d - timedelta(days=1)).replace(day=1)
    return d.replace(day=min(day, 28), hour=12)

# ---------------------------------------------------------------- seed
PW = "Str0ng!Pass"
def signup(email, name="Tester"):
    r = client.post("/users", json={"name": name, "email": email, "password": PW})
    assert r.status_code == 200, r.text
    return r.json()["user_id"]

def login(email):
    r = client.post("/users/login", data={"username": email, "password": PW})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

UA, UB, UC = signup("a@test.com"), signup("b@test.com"), signup("c@test.com")
HA, HB, HC = login("a@test.com"), login("b@test.com"), login("c@test.com")

CATS = {}
for n in ["Food", "Shopping", "Entertainment", "Utilities", "Transportation", "Health"]:
    CATS[n] = client.post("/categories", json={"name": n}, headers=HA).json()["category_id"]

db = SessionLocal()
def add(uid, cat, amt, when, desc="item"):
    crud.create_expense(db, uid, CATS[cat], amt, desc, expense_date=when)

# User A: 8 months of history, current month = Food 500 + Shopping 2500
this_month = NOW.replace(day=1, hour=9)
add(UA, "Food", 300, this_month, "groceries")
add(UA, "Food", 200, this_month + timedelta(days=1), "dinner")
add(UA, "Shopping", 2500, this_month + timedelta(days=2), "laptop")
for m in range(1, 8):
    for cat, amt in [("Food", 400 + m * 10), ("Utilities", 150), ("Transportation", 120), ("Entertainment", 80)]:
        for d in (3, 8, 13, 18, 23):
            add(UA, cat, amt / 5, months_ago(m, d), f"{cat.lower()} {d}")
add(UA, "Food", 900, months_ago(1, 27), "catering outlier")      # anomaly
gone = crud.create_expense(db, UA, CATS["Food"], 99999, "deleted", expense_date=this_month)
crud.soft_delete_expense(db, gone.expense_id)                     # must never be counted
# User C: one other user's expense in same month, must not leak into A's numbers
add(UC, "Food", 7777, this_month, "someone else")
db.close()

client.post("/budgets", json={"category_id": CATS["Food"], "amount": 400, "period": "monthly"}, headers=HA)
client.post("/budgets", json={"amount": 5000, "period": "monthly"}, headers=HA)

MONTH_NAME = NOW.strftime("%B").lower()
LAST = months_ago(1)
LAST_NAME = LAST.strftime("%B").lower()

def ask(q, uid=UA):
    s = SessionLocal()
    try:
        return parse_intent(q), process_ai_query(parse_intent(q), s, uid)
    finally:
        s.close()

# ---------------------------------------------------------------- 1. intent + value matrix
QUERIES = [
    # (query, expected intent, substrings expected in response)
    (f"How much did I spend on food in {MONTH_NAME} {NOW.year}", IntentType.monthly_total, ["$500.00", "food"]),
    (f"How much did I spend in {MONTH_NAME} {NOW.year}", IntentType.monthly_total, ["$3000.00"]),
    ("how much did I spend this month", IntentType.monthly_total, ["$3000.00"]),
    ("how much on shopping this month", IntentType.monthly_total, ["$2500.00"]),
    ("How much have I spent on food this month?", IntentType.monthly_total, ["$500.00"]),
    ("What did I spend on food this month", IntentType.monthly_total, ["$500.00"]),
    ("How much did I spend on Food this month", IntentType.monthly_total, ["$500.00"]),
    ("how much did i spend on groceries this month", IntentType.monthly_total, []),
    (f"how much did I spend on entertainment in {LAST_NAME}", IntentType.monthly_total, ["$80.00"]),
    ("total spending last month", IntentType.monthly_total, []),
    ("how much did I spend in 2019", IntentType.monthly_total, ["$0.00"]),
    ("show me a category breakdown for this month", IntentType.category_breakdown, ["Shopping"]),
    ("where does my money go", IntentType.category_breakdown, []),
    ("which category do I spend the most on this month", IntentType.highest_spend_category, ["Shopping"]),
    ("which category do I spend the most on", IntentType.highest_spend_category, ["Food"]),
    ("what's my biggest expense this month", IntentType.highest_expense, ["$2500.00", "laptop"]),
    ("show my spending trend over 6 months", IntentType.spending_trend, []),
    ("spending trend for the last 12 months", IntentType.spending_trend, []),
    ("compare this month vs last month", IntentType.compare_months, []),
    (f"compare {LAST_NAME} and {MONTH_NAME}", IntentType.compare_months, []),
    ("forecast my spending", IntentType.forecast, []),
    ("what will i spend next month", IntentType.forecast, []),
    ("any unusual transactions?", IntentType.detect_anomalies, ["catering outlier"]),
    ("am I over budget", IntentType.budget_check, []),
    ("check my budget", IntentType.budget_check, []),
    ("how much should i budget for food", IntentType.suggest_budget, []),
    ("how can I save money", IntentType.budget_suggestions, []),
    ("give me some tips", IntentType.advice, []),
    ("I spent $45 on groceries", IntentType.create_expense, ["$45.00", "food"]),
    ("I spent 45 on lunch today", IntentType.create_expense, ["$45.00"]),
    ("I paid $12.50 for uber", IntentType.create_expense, ["$12.50", "transportation"]),
    ("log an expense of $20 for netflix", IntentType.create_expense, ["$20.00"]),
]

for q, intent, subs in QUERIES:
    @case(f"query {q!r}")
    def _():
        p, r = ask(q)
        check(f"intent {q!r}", p.intent == intent, f"got {p.intent.value}, want {intent.value}")
        check(f"no error {q!r}", "error occurred" not in r.response, r.response)
        for s in subs:
            check(f"value {q!r}", s.lower() in r.response.lower(), f"missing {s!r} in {r.response!r}")
        check(f"no leak {q!r}", "7777" not in r.response and "99999" not in r.response, r.response)

@case("trend data shape")
def _():
    _, r = ask("spending trend over 6 months")
    t = r.data["trend"]
    check("trend 6 points", len(t) == 6, len(t))
    check("trend current month total", t[-1]["total_amount"] == 3000.0, t[-1])

@case("compare values")
def _():
    _, r = ask("compare this month vs last month")
    check("compare this month", r.data["month2_total"] == 3000.0, r.data)
    check("compare readable", "/" not in r.response.split("is")[0], r.response)

@case("compare explicit years")
def _():
    p, r = ask(f"compare {MONTH_NAME} {NOW.year - 1} and {MONTH_NAME} {NOW.year}")
    f = p.filters or {}
    check("compare honors years", (f.get("year1"), f.get("year2")) == (NOW.year - 1, NOW.year), f)

@case("budget check over")
def _():
    _, r = ask("am i over budget")
    check("food over budget flagged", "Food" in r.response and "over" in r.response.lower(), r.response)

@case("highest expense date is expense_date")
def _():
    _, r = ask("biggest expense this month")
    check("date field", r.data["date"].startswith((this_month + timedelta(days=2)).strftime("%Y-%m-%d")), r.data)

@case("forecast numbers")
def _():
    _, r = ask("forecast my spending")
    check("forecast ok", r.execution_status == "success", r.response)

# ---------------------------------------------------------------- 2. empty user: every intent must degrade cleanly
for q, intent, _ in QUERIES:
    @case(f"empty user {q!r}")
    def _():
        _, r = ask(q, UB)
        check(f"empty no crash {q!r}", "error occurred" not in r.response, r.response)

# ---------------------------------------------------------------- 3. fuzz the parser/processor
random.seed(7)
WORDS = ["spend", "food", "budget", "trend", "compare", "may", "march", "2026", "$", "vs", "last", "this", "month",
         "i spent", "forecast", "category", "biggest", "0", "99", "13 months", "999 months", "december", "%", "'", ";--",
         "😀", "\x00", "  ", "\n", "café", "year", "over budget", "per month"]
fuzz_errors = []
for i in range(1500):
    q = " ".join(random.choice(WORDS) for _ in range(random.randint(1, 12)))
    if random.random() < 0.2:
        q = "".join(random.choice(string.printable) for _ in range(random.randint(1, 200)))
    try:
        _, r = ask(q, random.choice([UA, UB]))
        if "error occurred" in r.response:
            fuzz_errors.append((q, r.response))
    except Exception as e:
        fuzz_errors.append((q, f"{type(e).__name__}: {e}"))
check("fuzz 1500 queries", not fuzz_errors, f"{len(fuzz_errors)} errors, e.g. {fuzz_errors[:3]}")

@case("huge query")
def _():
    _, r = ask("how much did i spend " * 20000)
    check("huge query ok", "error occurred" not in r.response, r.response[:200])

# ---------------------------------------------------------------- 4. LLM layer (mocked client)
@case("llm context builds")
def _():
    s = SessionLocal()
    try:
        ctx_a = llm.build_financial_context(s, UA)
        ctx_b = llm.build_financial_context(s, UB)
    finally:
        s.close()
    check("ctx has food", "Food" in ctx_a, ctx_a[:300])
    check("ctx no other user", "7777" not in ctx_a and "99999" not in ctx_a, "leak")
    check("ctx empty user", "none" in ctx_b, ctx_b[:300])

@case("history conversion")
def _():
    m = llm._history_to_messages(["AI: hi", "User: q1", "AI: a1", "User: q2", "garbage", "User: q3"])
    check("history starts with user", m[0]["role"] == "user", m)
    check("history alternates", all(m[i]["role"] != m[i + 1]["role"] for i in range(len(m) - 1)), m)

class FakeResp:
    def __init__(self, text, stop="end_turn"):
        self.content = [mock.Mock(type="text", text=text)]
        self.stop_reason = stop
        self._request_id = "req_x"

@case("llm endpoint wiring")
def _():
    fake = mock.Mock()
    fake.messages.create.return_value = FakeResp("You spent $500 on food.")
    with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "x"}), mock.patch.object(llm, "_get_client", return_value=fake):
        r = client.post("/ai/query", json={"query": "food this month", "context": ["User: hi", "AI: hello"]}, headers=HA)
        check("llm reply used", r.status_code == 200 and r.json()["response"] == "You spent $500 on food.", r.text)
        kwargs = fake.messages.create.call_args.kwargs
        roles = [m["role"] for m in kwargs["messages"]]
        check("llm msgs alternate", all(roles[i] != roles[i + 1] for i in range(len(roles) - 1)), roles)
        check("llm last is user", roles[-1] == "user", roles)
        # create_expense must bypass LLM
        fake.messages.create.reset_mock()
        r = client.post("/ai/query", json={"query": "I spent $5 on coffee"}, headers=HA)
        check("create_expense bypasses llm", not fake.messages.create.called and r.json()["data"]["action"] == "create_expense", r.text)

@case("llm failure falls back")
def _():
    import anthropic, httpx
    fake = mock.Mock()
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    for err in [anthropic.APIConnectionError(request=req),
                anthropic.APITimeoutError(request=req),
                anthropic.RateLimitError("rate", response=httpx.Response(429, request=req), body=None),
                anthropic.InternalServerError("boom", response=httpx.Response(500, request=req), body=None),
                ValueError("unexpected")]:
        fake.messages.create.side_effect = err
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "x"}), mock.patch.object(llm, "_get_client", return_value=fake):
            r = client.post("/ai/query", json={"query": "how much did I spend this month"}, headers=HA)
        check(f"fallback on {type(err).__name__}", r.status_code == 200 and "$3000.00" in r.json().get("response", ""), f"{r.status_code} {r.text[:200]}")
    fake.messages.create.side_effect = None
    fake.messages.create.return_value = FakeResp("", stop="refusal")
    with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "x"}), mock.patch.object(llm, "_get_client", return_value=fake):
        r = client.post("/ai/query", json={"query": "how much did I spend this month"}, headers=HA)
    check("fallback on refusal", "$3000.00" in r.json()["response"], r.text)

# ---------------------------------------------------------------- 5. API: auth & permissions
@case("auth required")
def _():
    for method, path, body in [("get", "/expenses", None), ("post", "/ai/query", {"query": "x"}), ("get", "/budgets", None),
                               ("get", "/budgets/status", None), ("get", "/expenses/trend", None), ("get", "/users/me", None),
                               ("put", f"/expenses/1", {"category_id": CATS["Food"], "amount": 1, "description": "x"}),
                               ("post", f"/users/{UA}/chat", {"user_id": UA, "sender": "User", "message": "x"}),
                               ("get", f"/users/{UA}/expenses/summary?month=1&year=2026", None),
                               ("put", f"/users/{UA}", {"name": "x", "email": "hijack@test.com", "password": PW}),
                               ("delete", f"/users/{UA}", None)]:
        r = getattr(client, method)(path, **({"json": body} if body else {}))
        check(f"401 {method.upper()} {path}", r.status_code == 401, f"{r.status_code} {r.text[:120]}")
    r = client.get("/expenses", headers={"Authorization": "Bearer garbage"})
    check("bad token 401", r.status_code == 401, r.status_code)

@case("cross-user access")
def _():
    a_exp = client.get("/expenses", headers=HA).json()[0]
    r = client.put(f"/expenses/{a_exp['expense_id']}", json={"category_id": CATS["Food"], "amount": 1, "description": "pwned"}, headers=HB)
    check("B cannot edit A's expense", r.status_code in (403, 404), f"{r.status_code} {r.text[:120]}")
    r = client.delete(f"/expenses/{a_exp['expense_id']}", headers=HB)
    check("B cannot delete A's expense", r.status_code == 403, r.status_code)
    r = client.post(f"/users/{UA}/chat", json={"user_id": UA, "sender": "User", "message": "spoof"}, headers=HB)
    check("B cannot write A's chat", r.status_code == 403, f"{r.status_code}")
    r = client.get(f"/users/{UA}/chat", headers=HB)
    check("B cannot read A's chat", r.status_code == 403, r.status_code)
    r = client.get(f"/users/{UA}/expenses/summary?month={NOW.month}&year={NOW.year}", headers=HB)
    check("B cannot read A's summary", r.status_code == 403, f"{r.status_code}")
    r = client.put(f"/users/{UA}", json={"name": "x", "email": "a2@test.com", "password": PW}, headers=HB)
    check("B cannot edit A's account", r.status_code == 403, f"{r.status_code}")
    r = client.delete(f"/users/{UA}", headers=HB)
    check("B cannot delete A's account", r.status_code == 403, f"{r.status_code}")
    budgets = client.get("/budgets", headers=HA).json()
    r = client.delete(f"/budgets/{budgets[0]['budget_id']}", headers=HB)
    check("B cannot delete A's budget", r.status_code == 403, r.status_code)

# ---------------------------------------------------------------- 6. API: validation / bad input
@case("input validation")
def _():
    bad = [
        ("post", "/expenses", {"category_id": CATS["Food"], "amount": -50, "description": "neg"}, "negative amount"),
        ("post", "/expenses", {"category_id": CATS["Food"], "amount": 0, "description": "zero"}, "zero amount"),
        ("post", "/expenses", {"category_id": 999999, "amount": 5, "description": "x"}, "missing category"),
        ("post", "/expenses", {"category_id": CATS["Food"], "amount": 5, "description": "x", "created_at": "2026-13-45"}, "bad date"),
        ("post", "/expenses", {"category_id": CATS["Food"], "amount": "abc", "description": "x"}, "string amount"),
        ("post", "/budgets", {"amount": -1}, "negative budget"),
        ("post", "/budgets", {"amount": 10, "period": "hourly"}, "bad period"),
        ("post", "/budgets", {"amount": 10, "alert_threshold": 5}, "bad threshold"),
        ("post", "/ai/query", {"query": "   "}, "blank query"),
        ("post", "/categories", {"name": "  "}, "blank category"),
        ("get", "/expenses/summary?month=13&year=2026", None, "month 13"),
        ("get", "/expenses/trend?months=0", None, "trend 0"),
        ("get", "/expenses/trend?months=1000", None, "trend 1000"),
    ]
    for method, path, body, label in bad:
        r = getattr(client, method)(path, headers=HA, **({"json": body} if body is not None else {}))
        check(f"reject {label}", 400 <= r.status_code < 500, f"{r.status_code} {r.text[:150]}")
    for label, email, pw in [("weak pw", "w@test.com", "short"), ("bad email", "nope", PW), ("dup", "a@test.com", PW)]:
        r = client.post("/users", json={"name": "x", "email": email, "password": pw})
        check(f"signup reject {label}", 400 <= r.status_code < 500, r.status_code)
    r = client.post("/users/login", data={"username": "a@test.com", "password": "Wrong!Pass1"})
    check("bad login 401", r.status_code == 401, r.status_code)

@case("valid edge inputs")
def _():
    r = client.post("/expenses", json={"category_id": CATS["Food"], "amount": 0.01, "description": "penny", "created_at": "01/31/2026"}, headers=HA)
    check("penny expense", r.status_code == 200, r.text)
    eid = r.json()["expense_id"]
    r = client.put(f"/expenses/{eid}", json={"category_id": CATS["Food"], "amount": 0.02, "description": "penny2"}, headers=HA)
    check("owner can update", r.status_code == 200, r.text)
    r = client.delete(f"/expenses/{eid}", headers=HA)
    check("owner can delete", r.status_code == 200, r.text)
    r = client.delete(f"/expenses/{eid}", headers=HA)
    check("double delete 404", r.status_code == 404, f"{r.status_code}")
    r = client.put(f"/expenses/{eid}", json={"category_id": CATS["Food"], "amount": 5, "description": "zombie"}, headers=HA)
    check("update deleted 404", r.status_code == 404, f"{r.status_code}")
    r = client.post("/expenses", json={"category_id": CATS["Food"], "amount": 5, "description": "émoji 🍕 ' \"; DROP TABLE"}, headers=HA)
    check("unicode/sql description", r.status_code == 200 and "🍕" in r.json()["description"], r.text)
    client.delete(f"/expenses/{r.json()['expense_id']}", headers=HA)
    r = client.get(f"/expenses/summary?month={NOW.month}&year={NOW.year}", headers=HA)
    check("summary total", r.status_code == 200 and r.json()["total_expense"] == 3000.0, r.text)
    r = client.get("/expenses/trend?months=24", headers=HA)
    check("trend 24", r.status_code == 200 and len(r.json()["trend"]) == 24, r.status_code)
    r = client.get(f"/users/{UA}/chat", headers=HA)
    check("own chat", r.status_code == 200, r.status_code)
    r = client.post(f"/users/{UA}/chat", json={"user_id": UA, "sender": "User", "message": "hi"}, headers=HA)
    check("own chat write", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
    r = client.get("/budgets/status", headers=HA)
    check("budget status", r.status_code == 200 and len(r.json()) == 2, r.text[:200])
    r = client.get("/budgets/999999", headers=HA)
    check("missing budget 404", r.status_code == 404, r.status_code)

@case("category in use")
def _():
    cid = client.post("/categories", json={"name": "TempCat"}, headers=HA).json()["category_id"]
    client.post("/expenses", json={"category_id": cid, "amount": 3, "description": "x"}, headers=HA)
    r = client.delete(f"/categories/{cid}", headers=HA)
    check("delete used category is 4xx not 500", r.status_code != 500, f"{r.status_code}")
    r = client.get("/expenses", headers=HA)
    check("expenses still listable", r.status_code == 200, f"{r.status_code} {r.text[:150]}")
    _, ai = ask("category breakdown")
    check("breakdown after cat delete", "error occurred" not in ai.response, ai.response)

# ---------------------------------------------------------------- 7. rate limiting
@case("rate limit")
def _():
    app.state.limiter.enabled = True
    try:
        codes = [client.post("/ai/query", json={"query": "this month"}, headers=HC).status_code for _ in range(25)]
        check("ai rate limited at 20/min", codes.count(429) == 5 and codes[:20].count(200) == 20, codes)
    finally:
        app.state.limiter.enabled = False
        app.state.limiter.reset()

# ---------------------------------------------------------------- 8. concurrency / load
@case("concurrent load")
def _():
    qs = [q for q, _, _ in QUERIES if not q.lower().startswith(("i spent", "i paid", "log"))]
    def hit(i):
        kind = i % 5
        if kind == 0:
            return client.post("/ai/query", json={"query": random.choice(qs)}, headers=HA).status_code
        if kind == 1:
            r = client.post("/expenses", json={"category_id": CATS["Health"], "amount": 1, "description": f"load {i}"}, headers=HB)
            return r.status_code
        if kind == 2:
            return client.get("/expenses", headers=HA).status_code
        if kind == 3:
            return client.get("/budgets/status", headers=HA).status_code
        return client.get("/expenses/trend?months=12", headers=HB).status_code
    t = time.time()
    with ThreadPoolExecutor(max_workers=16) as ex:
        codes = list(ex.map(hit, range(800)))
    elapsed = time.time() - t
    bad = [c for c in codes if c != 200]
    check("800 concurrent requests all 200", not bad, f"{len(bad)} failures: {sorted(set(bad))}")
    n = len(client.get("/expenses", headers=HB).json())
    check("no lost writes", n == 160, f"B has {n} expenses, expected 160")
    print(f"  load: 800 requests in {elapsed:.1f}s ({800 / elapsed:.0f} req/s)")

@case("account deletion")
def _():
    e = "del@test.com"
    uid = signup(e)
    h = login(e)
    check("anon category write 401", client.post("/categories", json={"name": "Anon"}).status_code == 401, "")
    r = client.delete(f"/users/{uid}", headers=h)
    check("self delete", r.status_code == 200, r.status_code)
    check("deleted token rejected", client.get("/users/me", headers=h).status_code == 401, "")
    r = client.post("/users", json={"name": "x", "email": e, "password": PW})
    check("re-signup deleted email not 500", r.status_code != 500, f"{r.status_code} {r.text[:100]}")
    r = client.put(f"/users/{UA}", json={"name": "A", "email": "b@test.com", "password": PW}, headers=HA)
    check("email collision on update is 400", r.status_code == 400, f"{r.status_code} {r.text[:100]}")

# ---------------------------------------------------------------- 9. budgets, edge dates, misc endpoints
@case("budget lifecycle")
def _():
    for period in ["daily", "weekly", "monthly", "yearly"]:
        r = client.post("/budgets", json={"category_id": CATS["Health"], "amount": 50, "period": period}, headers=HC)
        check(f"budget {period}", r.status_code == 200, r.text[:150])
    st = client.get("/budgets/status", headers=HC)
    check("status 4 periods", st.status_code == 200 and len(st.json()) == 4, st.text[:200])
    bid = client.get("/budgets", headers=HC).json()[0]["budget_id"]
    for body, label in [({"period": "hourly"}, "bad period"), ({"alert_threshold": 5}, "bad threshold"),
                        ({"amount": -3}, "negative amount")]:
        r = client.put(f"/budgets/{bid}", json=body, headers=HC)
        check(f"budget update rejects {label}", 400 <= r.status_code < 500, f"{r.status_code} {r.text[:120]}")
    r = client.put(f"/budgets/{bid}", json={"amount": 75, "is_active": False}, headers=HC)
    check("budget update ok", r.status_code == 200 and r.json()["amount"] == 75 and r.json()["is_active"] is False, r.text[:200])
    r = client.put(f"/budgets/{bid}", json={"amount": 1}, headers=HB)
    check("B cannot update C's budget", r.status_code == 403, r.status_code)
    r = client.get(f"/budgets/{bid}", headers=HB)
    check("B cannot read C's budget", r.status_code == 403, r.status_code)
    r = client.post("/budgets", json={"category_id": 999999, "amount": 5}, headers=HC)
    check("budget missing category 404", r.status_code == 404, r.status_code)
    r = client.post("/budgets", json={"category_id": 0, "amount": 5}, headers=HC)
    check("budget category 0 rejected", r.status_code in (400, 404, 422), f"{r.status_code} {r.text[:120]}")
    r = client.delete(f"/budgets/{bid}", headers=HC)
    check("budget delete", r.status_code == 200, r.status_code)
    check("deleted budget 404", client.get(f"/budgets/{bid}", headers=HC).status_code == 404, "")

@case("modal 'may' is not the month")
def _():
    for q in ["how much may I spend on food this month", "where may i cut back"]:
        p, _ = ask(q)
        check(f"may modal {q!r}", not (p.time and p.time.month == 5), p.time)
    p, _ = ask("how much did i spend in may")
    check("may as month", p.time and p.time.month == 5, p.time)
    p, _ = ask("compare may and june")
    check("compare may/june", (p.filters or {}).get("month1") == 5, p.filters)

@case("future-dated expense this month")
def _():
    if NOW.day >= 27:
        return
    s = SessionLocal()
    crud.create_expense(s, UC, CATS["Utilities"], 120, "rent due", expense_date=NOW.replace(day=28, hour=0))
    s.close()
    _, total = ask("how much did i spend this month", UC)
    _, trend = ask("spending trend over 3 months", UC)
    check("trend matches monthly total", f"${trend.data['trend'][-1]['total_amount']:.2f}" in total.response,
          f"{total.response} vs {trend.data['trend'][-1]}")

@case("forecast thin history")
def _():
    _, r = ask("forecast my spending", UC)
    check("forecast thin ok", "error occurred" not in r.response, r.response)

@case("misc endpoints")
def _():
    r = client.post("/categories", json={"name": "Dupe1"}, headers=HA)
    r2 = client.post("/categories", json={"name": "Dupe2"}, headers=HA)
    r = client.put(f"/categories/{r2.json()['category_id']}", json={"name": "Dupe1"}, headers=HA)
    check("rename to existing category 400", r.status_code == 400, f"{r.status_code}")
    r = client.post("/categories", json={"name": "food"}, headers=HA)
    check("case-dup category rejected", r.status_code == 400, f"{r.status_code} {r.text[:100]}")
    r = client.post(f"/users/{UA}/chat", json={"user_id": UA, "sender": "User", "message": ""}, headers=HA)
    check("empty chat message rejected", 400 <= r.status_code < 500, f"{r.status_code}")
    r = client.post(f"/users/{UA}/chat", json={"user_id": UA, "sender": "Hacker", "message": "x"}, headers=HA)
    check("bad chat sender rejected", 400 <= r.status_code < 500, f"{r.status_code}")
    r = client.get("/expenses/summary?month=12&year=2025", headers=HA)
    check("december summary", r.status_code == 200 and r.json()["total_days"] == 31, r.text[:120])
    r = client.get("/expenses/summary?month=2&year=2028", headers=HA)
    check("leap feb", r.status_code == 200 and r.json()["total_days"] == 29, r.text[:120])
    r = client.post("/users/login", data={"username": "del@test.com", "password": PW})
    check("deleted user cannot log in", r.status_code == 401, r.status_code)

# ---------------------------------------------------------------- 10. time travel: January and December
class _FrozenDT(datetime):
    FROZEN = None
    @classmethod
    def now(cls, tz=None):
        return cls.FROZEN
import ai.parser as _parser, ai.processor as _proc

def frozen(when):
    """Pretend it's `when` inside the app (parser, processor, LLM snapshot, endpoints)."""
    _FrozenDT.FROZEN = when
    from contextlib import ExitStack
    st = ExitStack()
    for m in (_parser, _proc, llm, mainmenu):
        st.enter_context(mock.patch.object(m, "datetime", _FrozenDT))
    return st

TT = signup("tt@test.com"); HT = login("tt@test.com")
s = SessionLocal()
for y, m, amt in [(2026, 11, 100), (2026, 12, 200), (2027, 1, 300)]:
    crud.create_expense(s, TT, CATS["Food"], amt, f"{y}-{m}", expense_date=datetime(y, m, 5, 12))
s.close()

@case("time travel january")
def _():
    with frozen(datetime(2027, 1, 15, 12)):
        _, r = ask("how much did i spend last month", TT)
        check("jan: last month = dec 2026", "$200.00" in r.response and "December 2026" in r.response, r.response)
        p, r = ask("compare this month vs last month", TT)
        check("jan: compare", r.data and r.data["month1_total"] == 200 and r.data["month2_total"] == 300, r.response)
        p, r = ask("how much did i spend in december", TT)
        check("jan: 'december' = dec 2026", "$200.00" in r.response, r.response)
        _, r = ask("spending trend over 3 months", TT)
        labels = [t["label"] for t in r.data["trend"]] if r.data else []
        check("jan: trend crosses year", labels == ["Nov 2026", "Dec 2026", "Jan 2027"], labels)
        r = client.get("/expenses/trend?months=3", headers=HT)
        check("jan: api trend", [t["total"] for t in r.json()["trend"]] == [100, 200, 300], r.text[:200])
        _, r = ask("compare december and january", TT)
        check("jan: compare dec/jan", r.data and r.data["month1_total"] == 200 and r.data["month2_total"] == 300, r.response)

@case("time travel december 31")
def _():
    with frozen(datetime(2026, 12, 31, 23, 30)):
        _, r = ask("how much did i spend this month", TT)
        check("dec31: this month", "$200.00" in r.response, r.response)
        _, r = ask("spending trend over 2 months", TT)
        check("dec31: trend", r.data and [t["total_amount"] for t in r.data["trend"]] == [100, 200], r.data)
        s2 = SessionLocal()
        try:
            ctx = llm.build_financial_context(s2, TT)
        finally:
            s2.close()
        check("dec31: llm ctx", "Dec 2026: $200.00" in ctx, ctx[:400])

# ---------------------------------------------------------------- 11. date range boundaries
BD = signup("bd@test.com"); HBD = login("bd@test.com")
s = SessionLocal()
for when, amt in [(datetime(2026, 10, 31, 23, 59, 59), 1), (datetime(2026, 11, 1, 0, 0, 0), 10),
                  (datetime(2026, 11, 30, 23, 59, 59), 100), (datetime(2026, 12, 1, 0, 0, 0), 1000),
                  (datetime(2026, 12, 31, 23, 59, 59), 10000), (datetime(2027, 1, 1, 0, 0, 0), 100000),
                  (datetime(2025, 11, 15, 12), 1000000)]:
    crud.create_expense(s, BD, CATS["Food"], amt, f"edge {amt}", expense_date=when)
s.close()

@case("month boundaries")
def _():
    with frozen(datetime(2027, 1, 15, 12)):
        for q, want in [("how much did i spend in november 2026", "$110.00"), ("how much did i spend in december 2026", "$11000.00"),
                        ("how much did i spend in 2026", "$11111.00"), ("how much did i spend in january 2027", "$100000.00")]:
            _, r = ask(q, BD)
            check(f"boundary {q}", want in r.response, r.response)
        _, r = ask("compare november 2026 and december 2026", BD)
        check("boundary compare", r.data["month1_total"] == 110 and r.data["month2_total"] == 11000, r.data)
        _, r = ask("category breakdown for november 2026", BD)
        check("boundary breakdown", r.data["by_category"].get("Food") == 110, r.data)
        _, r = ask("biggest expense in november 2026", BD)
        check("boundary highest", r.data["amount"] == 100, r.data)
        _, r = ask("spending trend over 3 months", BD)
        check("trend keeps start of first month", [t["total_amount"] for t in r.data["trend"]] == [110, 11000, 100000], r.data)
        r = client.get("/expenses/trend?months=3", headers=HBD)
        check("api trend boundaries", [t["total"] for t in r.json()["trend"]] == [110, 11000, 100000], r.text[:200])

@case("forecast window starts at midnight")
def _():
    with frozen(datetime(2027, 1, 15, 12)):
        _, r = ask("forecast over 3 months", BD)
        check("forecast keeps start of first month", r.data and r.data["historical_spending"][0] == 1 or r.data["historical_spending"][1] == 110, r.data)

# ---------------------------------------------------------------- report
print(f"\n{PASSES} checks passed, {len(FAILS)} failed\n")
for f in FAILS:
    print(" FAIL", f)
sys.exit(1 if FAILS else 0)
