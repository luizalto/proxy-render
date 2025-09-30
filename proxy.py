from fastapi import FastAPI, Request, HTTPException
import redis
import os
import httpx
import time

app = FastAPI()

# Conexão interna (funciona porque o proxy roda dentro do Render)
REDIS_URL = os.getenv("REDIS_URL", "redis://red-d26qhq6uk2gs73cb6720:6379")
r = redis.from_url(REDIS_URL)

# URL do worker local (exposto via ngrok, Cloudflare Tunnel etc.)
# exemplo: https://meu-worker.ngrok.app  (NÃO coloque barra final)
LOCAL_WORKER_URL = (os.getenv("LOCAL_WORKER_URL") or "").rstrip("/")

# Cliente HTTP para repassar requests
client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=6.0, read=25.0))

@app.get("/")
def root():
    return {"ok": True, "msg": "Proxy Redis + Predict ativo", "local_worker_url": LOCAL_WORKER_URL}

# ─────────── Redis passthrough ───────────
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

# ─────────── Predict passthrough ───────────
@app.post("/predict")
async def predict(req: Request):
    """
    Recebe payload JSON do servidor principal e repassa para o worker local.
    Espera resposta do worker no formato:
      {"ok": true, "probas": {"p_stack": 0.73}, "thresholds": {...}}
    """
    if not LOCAL_WORKER_URL:
        raise HTTPException(status_code=502, detail="LOCAL_WORKER_URL não configurado")

    try:
        payload = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_json")

    try:
        url = f"{LOCAL_WORKER_URL}/predict"
        resp = await client.post(url, json=payload)
        if resp.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"worker_http_{resp.status_code}")
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"worker_error:{e}")
