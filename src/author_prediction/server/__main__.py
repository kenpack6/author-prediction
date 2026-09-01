import uvicorn
uvicorn.run("author_prediction.server:app", host="0.0.0.0", port=8000, reload=True)