from fastapi import FastAPI

app = FastAPI(title="Author Prediction API")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, World!"}
