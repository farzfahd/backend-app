import os
os.environ["KERAS_BACKEND"] = "numpy"
os.environ["KERAS_BACKEND"] = "jax"
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_, or_
from database import get_db
from schemas import TambahArticle, CardArticle
from models import Article, PenggunaModel
from keras.models import load_model
from keras.utils import pad_sequences
from merangkum import summarize
import json
import pickle



router = APIRouter(
    prefix="/article",
    tags=["article"]
)

model = load_model("phishingDetection/model_phishing_cnn.keras")
with open('phishingDetection/tokenizer_phishing.pickle', 'rb') as handle:
    tokenizer = pickle.load(handle)
def eksekusi_prediksi_phishing(url_clean: str):
    sequences = tokenizer.texts_to_sequences([url_clean])
    paddings = pad_sequences(sequences, maxlen=200, padding='post')
    prediksi_mentah = model.predict(paddings)
    return float(prediksi_mentah[0][0])

@router.post("/new-article")
async def newArticle(payload: TambahArticle, db: AsyncSession = Depends(get_db)):
    db_artikel = Article(
        userId= payload.userId,
        judul = payload.judul,
        kategori = payload.kategori,
        subKategori = payload.subKategori,
        dekripsiSingkat = payload.dekripsiSingkat,
        deskripsi = payload.deskripsi,
        mediaSosial = payload.mediaSosial,
        linkWebsite = payload.linkWebsite,
        contactPerson = payload.contactPerson
    )

    url_target = db_artikel.linkWebsite if db_artikel.linkWebsite is not None else ""
    skor_phishing = 0.0
    terindikasi_phishing = False

    if url_target.strip():
        url_clean = url_target.strip().lower()
        
        skor_phishing = await run_in_threadpool(eksekusi_prediksi_phishing, url_clean)
        terindikasi_phishing = True if skor_phishing >= 0.5 else False

    if terindikasi_phishing:
        queryCheck = select(PenggunaModel).where(PenggunaModel.id == payload.userId)
        resultQuery = await db.execute(queryCheck)
        userSelected = resultQuery.scalar_one_or_none()

        if userSelected.warn == 3:
            setattr(userSelected, "isBanned", True)
        else:
            setattr(userSelected, "warn", userSelected.warn + 1)

        await db.commit()
        await db.refresh(userSelected)

        setattr(db_artikel, "isVisible", False)

        return {
            "status": f"Link website anda terindikasi sebagai phising, ini adalah warning ke-{userSelected.warn}"
        }

    
    return {
        "status": "sukses"
    }

@router.get("/{subKategori}", response_model=list[CardArticle])
async def categoryForCard(subKategori: str, db: AsyncSession = Depends(get_db)):
    querySelect = select(Article).where(
        and_(
            Article.subKategori == subKategori,
            Article.isVisible == True
        )
     )
    resultQuery = await db.execute(querySelect)
    articles = resultQuery.scalars().all()

    if not articles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artikel dengan sub-kategori '{subKategori}' tidak ditemukan."
        )
    
    return articles

@router.get("/detail/{articleId}")
async def getFullArticle(articleId: int, db: AsyncSession = Depends(get_db)):
    querySelect = select(Article).where(Article.id == articleId)
    resultQuery = await db.execute(querySelect)
    article = resultQuery.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artikel dengan id '{id}' tidak ditemukan."
        )
    
    if article.summarize is None:
        rangkuman = summarize(article.dekripsi)
        setattr(article, "summarize", rangkuman)
    
    return article

@router.get("/rekomendasi", response_model=list[CardArticle])
async def getRekomendasi(
    subKategori: str = Query(...),
    bidang: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = (
            select(Article)
            .where(
                or_(
                    Article.subKategori == subKategori,      
                    # Article.bidang == bidang  #
                )
            )
            .order_by(func.random()) 
            .limit(7)                
        )
        
        result = await db.execute(stmt)
        daftar_konten = result.scalars().all()
        
        return daftar_konten

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")