from fastapi import FastAPI
from pydantic import BaseModel
import random, string
app = FastAPI()
url_map = {}

class URLItem(BaseModel):
    url:str

def generate_random_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.get("/")
async def hello():
    return{"message":"hello"}
@app.post("/shorten")
async def shorten_url(item: URLItem):
    code = generate_random_code()
    while code in url_map:
        code = generate_random_code()
    url_map[code] = item.url
    return {"short_url": f"http://127.0.0.1:8000/{code}"}
    