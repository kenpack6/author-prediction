from fastapi import FastAPI

app = FastAPI(title="Author Prediction API")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, World!"}


def main() -> None:
    import uvicorn

    uvicorn.run("author_prediction.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
