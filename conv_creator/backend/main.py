from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI()

# Allow frontend (Vue) to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # default Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/items")
def get_items():
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT)")
    items = cur.execute("SELECT * FROM items").fetchall()
    conn.close()
    return [{"id": i[0], "name": i[1]} for i in items]

@app.post("/items")
def add_item(name: str):
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("INSERT INTO items (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    return {"message": "Item added!"}