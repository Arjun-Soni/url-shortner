from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
import aiosqlite, secrets, string, re, os
from urllib.parse import urlparse


# App context

class AppContext:
    def __init__(self):
        self.db: aiosqlite.Connection | None = None

    async def init(self):
        self.db = await aiosqlite.connect("urls.db")
        self.db.row_factory = aiosqlite.Row
        await self.db.execute("PRAGMA journal_mode=WAL")
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                code TEXT PRIMARY KEY,
                url  TEXT UNIQUE
            )
        """)
        await self.db.commit()

    async def close(self):
        if self.db:
            await self.db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx = AppContext()
    await ctx.init()
    app.state.ctx = ctx
    yield
    await ctx.close()


app = FastAPI(lifespan=lifespan)
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")


# Helpers

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
        if not result.netloc or "@" in result.netloc:
            return False
        domain = result.hostname
        return bool(domain and DOMAIN_REGEX.match(domain))
    except Exception:
        return False

def generate_random_code(length=6) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def get_ctx(request: Request) -> AppContext:
    return request.app.state.ctx


# Routes

@app.get("/")
async def hello():
    return {"message": "hello"}

@app.post("/shorten")
async def shorten_url(item: URLItem, ctx: AppContext = Depends(get_ctx)):
    url = item.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    if not is_valid_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")

    for _ in range(10):
        code = generate_random_code()
        await ctx.db.execute(
            "INSERT OR IGNORE INTO urls (code, url) VALUES (?, ?)", (code, url)
        )
        await ctx.db.commit()
        async with ctx.db.execute(
            "SELECT code FROM urls WHERE url = ?", (url,)
        ) as cur:
            row = await cur.fetchone()
        if row:
            return {"short_url": f"{BASE_URL}/{row['code']}"}

    raise HTTPException(status_code=500, detail="Couldn't generate unique code.")

@app.get("/{code}")
async def redirect_url(code: str, ctx: AppContext = Depends(get_ctx)):
    async with ctx.db.execute(
        "SELECT url FROM urls WHERE code = ?", (code,)
    ) as cur:
        row = await cur.fetchone()
    if row:
        return RedirectResponse(url=row["url"], status_code=302)
    raise HTTPException(status_code=404, detail="URL not found")