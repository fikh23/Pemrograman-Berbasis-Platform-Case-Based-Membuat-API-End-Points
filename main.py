from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict
from uuid import uuid4

app = FastAPI(title="Katalog Buku API")

# ---- "Database" in-memory ----
books: Dict[str, dict] = {}
orders: Dict[str, dict] = {}

# ---- Models ----
class BookCreate(BaseModel):
    title: str = Field(min_length=1)
    author: str = Field(min_length=1)
    stock: int = Field(ge=0)

class BookStockUpdate(BaseModel):
    # pilih salah satu: set_stock (set nilai), atau delta (tambah/kurang)
    set_stock: Optional[int] = Field(default=None, ge=0)
    delta: Optional[int] = None

class OrderCreate(BaseModel):
    book_id: str
    qty: int = Field(gt=0, description="Jumlah tiket/qty harus > 0")  # aturan soal
    customer_name: str = Field(min_length=1)

# ---- Books ----
@app.post("/books")
def create_book(payload: BookCreate):
    book_id = str(uuid4())
    books[book_id] = {
        "id": book_id,
        "title": payload.title,
        "author": payload.author,
        "stock": payload.stock,
    }
    return books[book_id]

@app.get("/books")
def list_books(q: Optional[str] = None):
    data = list(books.values())
    if q:
        q_lower = q.lower()
        data = [
            b for b in data
            if q_lower in b["title"].lower() or q_lower in b["author"].lower()
        ]
    return {"items": data, "count": len(data)}

@app.get("/books/{book_id}")
def get_book(book_id: str):
    book = books.get(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan")
    return book

@app.patch("/books/{book_id}/stock")
def update_stock(book_id: str, payload: BookStockUpdate):
    book = books.get(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan")

    if payload.set_stock is None and payload.delta is None:
        raise HTTPException(status_code=400, detail="Isi set_stock atau delta")

    if payload.set_stock is not None and payload.delta is not None:
        raise HTTPException(status_code=400, detail="Pilih salah satu: set_stock atau delta")

    if payload.set_stock is not None:
        book["stock"] = payload.set_stock
    else:
        new_stock = book["stock"] + payload.delta
        if new_stock < 0:
            raise HTTPException(status_code=400, detail="Stok tidak boleh negatif")
        book["stock"] = new_stock

    return book

# ---- Orders ----
@app.post("/orders")
def create_order(payload: OrderCreate):
    book = books.get(payload.book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan")

    order_id = str(uuid4())
    orders[order_id] = {
        "id": order_id,
        "book_id": payload.book_id,
        "qty": payload.qty,                  # qty sudah divalidasi > 0
        "customer_name": payload.customer_name,
        "status": "pending",                 # aturan soal: default pending
    }
    return orders[order_id]

@app.get("/orders/{order_id}")
def get_order(order_id: str):
    order = orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Pesanan tidak ditemukan")
    return order

@app.post("/orders/{order_id}/confirm")
def confirm_order(order_id: str):
    order = orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Pesanan tidak ditemukan")

    if order["status"] != "pending":
        raise HTTPException(status_code=400, detail="Pesanan sudah diproses / bukan pending")

    book = books.get(order["book_id"])
    if not book:
        raise HTTPException(status_code=404, detail="Buku pada pesanan tidak ditemukan")

    if book["stock"] < order["qty"]:
        raise HTTPException(status_code=400, detail="Stok tidak mencukupi untuk konfirmasi")

    # kurangi stok + update status
    book["stock"] -= order["qty"]
    order["status"] = "confirmed"

    return {
        "message": "Pesanan berhasil dikonfirmasi",
        "order": order,
        "book": book,
    }
