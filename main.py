import os, requests, json, uuid
from fastapi import FastAPI, Request, File, UploadFile, Form, Cookie, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.cloud import firestore
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

app = FastAPI()
APP_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

db = firestore.Client()

API_KEY = "AIzaSyBReq5-pUCBXTGSuvgrUp5KRqvzSpr7qyU"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
STATUS_MAP = {"nowe": "Oczekujące", "preparing": "W kuchni", "ready": "Gotowe!", "closed": "Wydane"}

@app.get("/api/get_joke")
async def get_joke(item: str = "jedzenie"):
    prompt = f"Jesteś Duchem Burgera. Klient wybrał: {item}. Rzuć 1 krótkim żartem. Max 60 znaków."
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 50, "temperature": 0.7}}
        res = requests.post(GEMINI_URL, json=payload, timeout=5).json()
        return {"joke": res['candidates'][0]['content']['parts'][0]['text'].strip()}
    except: return {"joke": "Smacznego! Ten burger to legenda."}
@app.get("/api/get_story")
async def get_story(item: str = "burger"):
    prompt = f"Jesteś historykiem kulinarnym. Napisz jedną, fascynującą anegdotę o: {item}. Max 300 znaków. Zakończ kropką."
    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 100, "temperature": 0.8}
        }
        res = requests.post(GEMINI_URL, json=payload, timeout=5).json()
        story = res['candidates'][0]['content']['parts'][0]['text'].strip()
        return {"story": story}
    except:
        return {"story": "Czy wiesz, że pierwszy burger powstał z potrzeby zjedzenia posiłku w biegu? To klasyka, która nigdy nie wyjdzie z mody."}
@app.get("/api/get_menu")
async def get_menu(): 
    menu_dict = {d.id: d.to_dict() for d in db.collection("menu").stream()}
    return dict(sorted(menu_dict.items(), key=lambda x: int(x[1].get('sort_order', 99))))

@app.post("/api/admin/save_product")
async def save_product(
    key: str=Form(...), name: str=Form(...), price: float=Form(...), description: str=Form(""),
    allergens: str=Form(""), kcal: str=Form(""), weight: str=Form(""),
    sort_order: int=Form(10), to_kitchen: bool=Form(True),
    image_name: Optional[str]=Form(None), file: Optional[UploadFile]=File(None)
):
    final_image = image_name
    if file and file.filename:
        img_dir = APP_DIR / "static" / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        with open(img_dir / file.filename, "wb+") as f: f.write(file.file.read())
        final_image = file.filename
    db.collection("menu").document(key).set({
        "name": name, "price": price, "description": description, "allergens": allergens,
        "kcal": kcal, "weight": weight, "image": final_image, "sort_order": sort_order, "to_kitchen": to_kitchen
    }, merge=True)
    return {"ok": True}

@app.get("/api/get_layout")
async def get_layout():
    doc = db.collection("config").document("floor_plan").get()
    return doc.to_dict() if doc.exists else {"width": 10, "height": 8, "tables": []}

@app.post("/api/admin/save_layout")
async def save_layout(payload: dict):
    db.collection("config").document("floor_plan").set(payload)
    return {"ok": True}

@app.get("/api/active_tables")
async def active_tables(): return {"tables": [d.to_dict() for d in db.collection("active_tables").stream()]}

@app.post("/api/call_waiter/{table_num}")
async def call_waiter(table_num: int):
    db.collection("active_tables").document(str(table_num)).set({"call_waiter": True}, merge=True)
    return {"ok": True}

@app.post("/api/pay_request/{table_num}")
async def pay_request(table_num: int):
    db.collection("active_tables").document(str(table_num)).set({"pay_request": True}, merge=True)
    return {"ok": True}

@app.post("/api/reset_call/{table_num}")
async def reset_call(table_num: int):
    db.collection("active_tables").document(str(table_num)).set({"call_waiter": False, "pay_request": False}, merge=True)
    return {"ok": True}

@app.post("/api/clear_table/{table_id}")
async def clear_table(table_id: str):
    # Całkowite usunięcie dokumentu = stolik 100% ZIELONY
    db.collection("active_tables").document(table_id).delete()
    return {"ok": True}

@app.post("/api/orders")
async def create_order(payload: dict):
    db.collection("orders").add({
        "table_number": int(payload['table_number']), "burger_name": payload.get('burger_name'),
        "price": payload.get('price', 0), "note": payload.get('note', ''),
        "to_kitchen": payload.get('to_kitchen', True), 
        "status": "nowe" if payload.get('to_kitchen', True) else "ready",
        "time_ordered": firestore.SERVER_TIMESTAMP
    })
    db.collection("active_tables").document(str(payload['table_number'])).set({"call_waiter": False}, merge=True)
    return {"ok": True}

@app.post("/api/update_status/{id}")
async def update_status(id: str, payload: dict):
    db.collection("orders").document(id).update({"status": payload.get("status")})
    return {"ok": True}

@app.delete("/api/orders/{id}")
async def delete_order(id: str):
    db.collection("orders").document(id).delete()
    return {"ok": True}

@app.get("/api/all_orders")
async def all_orders():
    docs = db.collection("orders").order_by("time_ordered", direction=firestore.Query.DESCENDING).limit(150).stream()
    orders = []
    for d in docs:
        data = d.to_dict()
        if data.get("time_ordered"): data["time_ordered"] = data["time_ordered"].isoformat()
        data["id"] = d.id
        data["status_pl"] = STATUS_MAP.get(data.get("status"))
        data["paid"] = data.get("paid", False) # <--- DODAJ TĘ LINIJKĘ
        orders.append(data)
    return {"orders": orders}

@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request, table: Optional[str] = None, burger_session: Optional[str] = Cookie(None)):
    if not burger_session: burger_session = str(uuid.uuid4())
    menu_dict = {d.id: d.to_dict() for d in db.collection("menu").stream()}
    menu = dict(sorted(menu_dict.items(), key=lambda x: int(x[1].get('sort_order', 99))))

    if not table:
        resp = templates.TemplateResponse("index.html", {"request": request, "menu": menu, "session_table": None, "table_locked": False, "locked_num": None, "my_session_id": burger_session})
        resp.set_cookie(key="burger_session", value=burger_session, max_age=86400)
        return resp

    table_ref = db.collection("active_tables").document(table)
    table_doc = table_ref.get()
    
    if table_doc.exists and table_doc.to_dict().get("session_id") not in [None, burger_session]:
        resp = templates.TemplateResponse("index.html", {"request": request, "menu": menu, "session_table": None, "table_locked": True, "locked_num": table, "my_session_id": burger_session})
        resp.set_cookie(key="burger_session", value=burger_session, max_age=86400)
        return resp

    table_ref.set({"table_number": int(table), "session_id": burger_session}, merge=True)
    resp = templates.TemplateResponse("index.html", {"request": request, "menu": menu, "session_table": table, "table_locked": False, "locked_num": None, "my_session_id": burger_session})
    resp.set_cookie(key="burger_session", value=burger_session, max_age=86400)
    return resp
@app.post("/api/mark_paid/{table_num}")
async def mark_paid(table_num: int):
    # Pobieramy wszystkie zamówienia dla tego stolika
    docs = db.collection("orders").where("table_number", "==", table_num).stream()
    for d in docs:
        # Zaznaczamy je jako opłacone
        db.collection("orders").document(d.id).update({"paid": True})
    
    # Wyłączamy wezwanie "zapłać" na stoliku
    db.collection("active_tables").document(str(table_num)).set({"pay_request": False}, merge=True)
    return {"ok": True}
@app.get("/kds")
async def kds(request: Request): return templates.TemplateResponse("kds.html", {"request": request})
@app.get("/waiter")
async def waiter(request: Request): return templates.TemplateResponse("waiter.html", {"request": request})
@app.get("/admin")
async def admin(request: Request): return templates.TemplateResponse("admin.html", {"request": request})