from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import random, string
from fastapi.responses import RedirectResponse
import sqlite3, re
from urllib.parse import urlparse
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = sqlite3.connect("urls.db", check_same_thread=False)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS urls (
        code TEXT PRIMARY KEY,
        url TEXT
    )
    """)
    conn.commit()
    conn.close()
    yield
app = FastAPI(lifespan=lifespan)

class URLItem(BaseModel):
    url: str

DOMAIN_REGEX = re.compile(
    r"^(localhost|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}|\d{1,3}(\.\d{1,3}){3})$"
)

def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        if result.scheme not in ("http", "https"):
            return False
        if not result.netloc:
            return False
        if "@" in result.netloc:
            return False
        domain = result.hostname
        if not domain:
            return False
        return bool(DOMAIN_REGEX.match(domain))
    except Exception:
        return False

def generate_random_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.get("/")
async def hello():
    return{"message":"hello"}

@app.post("/shorten")
async def shorten_url(item: URLItem):
    conn = sqlite3.connect("urls.db")
    cursor = conn.cursor()
    # Clean URL
    url = item.url.strip()
    if not url.startswith(("https://", "http://")):
        url = "http://" + url
    # Validate URL
    if not is_valid_url(url):
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid URL")
    #generating random code
    for _ in range(10):
        code = generate_random_code()
        cursor.execute("SELECT 1 FROM urls WHERE code =?",
                       (code,))
        if not cursor.fetchone():
            break
    else:
        conn.close()
        raise HTTPException(status_code=500, detail="Couldn't generate unique code.")
    #Storing values
    cursor.execute(
        "INSERT INTO urls (code, url) VALUES(?,?)",
        (code, url)
    )
    conn.commit()
    conn.close()
    return {"short_url": f"http://127.0.0.1:8000/{code}"}


@app.get("/{code}")
async def redirect_url(code: str, request: Request):
    conn = sqlite3.connect("urls.db")
    cursor = conn.cursor()
    cursor.execute(
    "SELECT url FROM urls WHERE code=?",
    (code,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return RedirectResponse(url=row[0], status_code=302)
    else:
        raise HTTPException(status_code=404, detail="URL not found")