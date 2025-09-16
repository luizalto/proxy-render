from fastapi import FastAPI, Request
import redis
import os

app = FastAPI()

# Conexão interna (funciona porque o proxy roda dentro do Render)
REDIS_URL = os.getenv("REDIS_URL", "redis://red-d26qhq6uk2gs73cb6720:6379")
r = redis.from_url(REDIS_URL)

@app.get("/")
def root():
    return {"ok": True, "msg": "Proxy Redis ativo"}

@app.post("/incr")
def incr_key(data: dict):
    key = data.get("key", "utm_counter")
    value = int(r.incr(key))
    return {"value": value}

@app.post("/set")
def set_key(data: dict):
    key = data["key"]
    val = data["value"]
    r.set(key, val)
    return {"ok": True}

@app.get("/get")
def get_key(key: str):
    val = r.get(key)
    return {"value": val.decode() if val else None}
