# main.py
import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import FastAPI

# Initialize Firebase app
cred = credentials.Certificate("service.json")
firebase_admin.initialize_app(cred)

db = firestore.client()
app = FastAPI()

@app.post("/add-user")
def add_user(name: str, email: str):
    doc_ref = db.collection("users").document()
    doc_ref.set({
        "name": name,
        "email": email
    })
    return {"message": "User added"}
