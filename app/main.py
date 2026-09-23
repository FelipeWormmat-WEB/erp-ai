from fastapi import FastAPI

app = FastAPI(title="ERP Produtos e Estoque com IA")


@app.get("/health/live")
async def health():
    return {"status": "ok"}