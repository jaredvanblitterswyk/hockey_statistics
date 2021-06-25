from fastapi import FastAPI

app = FastAPI()

@app.get("/predict")
async def predict_complex_model(age: int,sex:str):
    # Test using a simple rule-based model
    if age>10 or sex=='F':
        return {'survived':0}
    else:
        return {'survived':1}