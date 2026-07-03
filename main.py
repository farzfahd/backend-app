from fastapi import FastAPI
from routers import products, users, article

app = FastAPI(
  title="Aplikasi Gudang",
  version="1.0.0"
)

app.include_router(products.router)
app.include_router(users.router)
app.include_router(article.router)

@app.get("/", tags=['Root'])
async def root():
  return {"status": "online",
          "message": "dih"}

@app.get("/ping", tags=['Ping'])
async def ping():
  return {"status": "online",
          "message": "dih"}