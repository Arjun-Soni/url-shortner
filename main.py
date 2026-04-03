from fastapi import FastAPI
from pydantic import BaseModel
import random, string
from fastapi.responses import RedirectResponse
from fastapi import HTTPException
import sqlite3

conn = sqlite3.connect("urls.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS urls (
    code TEXT PRIMARY KEY,
    url TEXT           )
""")
conn.commit()

app = FastAPI()

class URLItem(BaseModel):
    url: str

def generate_random_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.get("/")
async def hello():
    return{"message":"hello"}

@app.post("/shorten")
async def shorten_url(item: URLItem):
    code = generate_random_code()
    if not item.url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL")
    while True:
        code = generate_random_code()
        cursor.execute("SELECT 1 FROM urls WHERE code =?",
                       (code,))
        if not cursor.fetchone():
            break
    cursor.execute(
        "INSERT INTO urls (code, url) VALUES(?,?)",
        (code, item.url)
    )
    conn.commit()
    return {"short_url": f"http://127.0.0.1:8000/{code}"}

@app.get("/{code}")
async def redirect_url(code: str):
    cursor.execute(
    "SELECT url FROM urls WHERE code=?",
    (code,)
    )
    row = cursor.fetchone()
    if row:
        return RedirectResponse(url=row[0], status_code=302)
    else:
        raise HTTPException(status_code=404, detail="URL not found")