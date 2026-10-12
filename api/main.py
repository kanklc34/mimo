from fastapi import FastAPI

app = FastAPI(title="Mimo Kurye")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "Mimo Kurye"}
