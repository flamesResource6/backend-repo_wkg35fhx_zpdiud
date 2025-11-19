import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Chapter, QuizQuestion

app = FastAPI(title="Biology Learning API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Biology Learning API running"}

# Utility to serialize Mongo docs

def serialize(doc):
    if not doc:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc

# Seed minimal sample content if empty (one chapter + 3 questions)
@app.post("/seed")
def seed_data():
    try:
        existing = list(db["chapter"].find({}).limit(1)) if db else []
        if existing:
            return {"status": "ok", "message": "Already seeded"}
        # Insert one example chapter (generic, non-copyright text)
        ch = Chapter(
            slug="cell-structure",
            title="Struktur dan Fungsi Sel",
            summary=(
                "Ikhtisar mandiri tentang struktur dasar sel prokariot dan eukariot, membran, organel, dan aliran energi."
            ),
            objectives=[
                "Membedakan sel prokariot dan eukariot",
                "Menjelaskan fungsi organel utama",
                "Mengaitkan struktur membran dengan transport",
            ],
            sections=[
                {"heading": "Gambaran Umum Sel", "body": "Sel adalah unit dasar kehidupan."},
                {"heading": "Organel Utama", "body": "Nukleus, mitokondria, ribosom, retikulum endoplasma, dan lain-lain."},
            ],
        )
        create_document("chapter", ch)
        sample_questions = [
            QuizQuestion(
                chapter_slug="cell-structure",
                question="Komponen apakah yang paling berperan langsung dalam fosforilasi oksidatif pada sel eukariot?",
                options=[
                    "Ribosom",
                    "Mitokondria membran dalam",
                    "Aparatus Golgi",
                    "Peroksisom",
                ],
                correct_index=1,
                explanation="Rantai transpor elektron dan ATP sintase terletak pada membran dalam mitokondria.",
            ),
            QuizQuestion(
                chapter_slug="cell-structure",
                question="Pada model mosaik fluida, fungsi utama kolesterol dalam membran adalah...",
                options=[
                    "Meningkatkan permeabilitas air",
                    "Menstabilkan fluiditas pada rentang suhu",
                    "Mengaktifkan pompa ion",
                    "Mengikat glikoprotein",
                ],
                correct_index=1,
                explanation="Kolesterol membantu menjaga fluiditas membran tetap stabil terhadap perubahan suhu.",
            ),
            QuizQuestion(
                chapter_slug="cell-structure",
                question="Manakah mekanisme transport yang memerlukan energi langsung dari ATP?",
                options=[
                    "Difusi sederhana",
                    "Osmosis",
                    "Difusi terfasilitasi",
                    "Transpor aktif primer",
                ],
                correct_index=3,
                explanation="Transpor aktif primer menggunakan energi ATP untuk memompa molekul melawan gradien.",
            ),
        ]
        for q in sample_questions:
            create_document("quizquestion", q)
        return {"status": "ok", "message": "Seeded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Chapters endpoints

@app.get("/chapters")
def list_chapters():
    try:
        docs = get_documents("chapter")
        return [serialize(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chapters/{slug}")
def get_chapter(slug: str):
    try:
        doc = db["chapter"].find_one({"slug": slug})
        if not doc:
            raise HTTPException(status_code=404, detail="Chapter not found")
        return serialize(doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ChapterIn(BaseModel):
    slug: str
    title: str
    summary: str
    objectives: List[str] = []
    sections: List[dict] = []

@app.post("/chapters")
def create_chapter(payload: ChapterIn):
    try:
        # Ensure unique slug
        exists = db["chapter"].find_one({"slug": payload.slug})
        if exists:
            raise HTTPException(status_code=400, detail="Slug already exists")
        create_document("chapter", payload.model_dump())
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Quiz endpoints

@app.get("/chapters/{slug}/quiz")
def get_quiz_for_chapter(slug: str, limit: int = 20):
    try:
        cursor = db["quizquestion"].find({"chapter_slug": slug}).limit(limit)
        docs = list(cursor)
        return [serialize(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class QuizIn(BaseModel):
    chapter_slug: str
    question: str
    options: List[str]
    correct_index: int
    explanation: str
    difficulty: Optional[str] = "OSN-N"

@app.post("/quiz")
def create_quiz_item(item: QuizIn):
    try:
        if item.correct_index < 0 or item.correct_index >= len(item.options):
            raise HTTPException(status_code=400, detail="correct_index out of range")
        create_document("quizquestion", item.model_dump())
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health/test endpoint remains
@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db as _db
        if _db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = _db.name if hasattr(_db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = _db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
