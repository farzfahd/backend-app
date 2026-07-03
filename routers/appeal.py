import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from database import get_db
from models import PenggunaModel, Article
from schemas import AjukanBanding, KeputusanGemini
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    prefix="/appeal",
    tags=["Appeal & Safety"]
)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@router.post("/submit")
async def submitUserAppeal(payload: AjukanBanding, db: AsyncSession = Depends(get_db)):
    query_user = select(PenggunaModel).where(PenggunaModel.id == payload.userId)
    res_user = await db.execute(query_user)
    user = res_user.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
    if not user.isBanned:
        raise HTTPException(status_code=400, detail="User ini tidak dalam status banned.")

    query_artikel = (
        select(Article)
        .where(
            and_(
                Article.userId == payload.userId,
                Article.isVisible == False
            )
        )
        .order_by(desc(Article.id))
        .limit(3)
    )
    res_artikel = await db.execute(query_artikel)
    daftar_artikel = res_artikel.scalars().all()

    # Susun konten 3 artikel ke dalam teks untuk dibaca Gemini
    konten_pelanggaran = ""
    for i, art in enumerate(daftar_artikel, start=1):
        konten_pelanggaran += f"\n--- ARTIKEL PELANGGARAN ke-{i} ---\n"
        konten_pelanggaran += f"Judul: {art.judul}\n"
        konten_pelanggaran += f"Deskripsi: {art.deskripsi}\n"
        konten_pelanggaran += f"Link Website: {art.linkWebsite}\n"

    # 3. Susun Prompt Komprehensif untuk Gemini
    system_instruction = (
        "Anda adalah sistem AI peradilan otomatis untuk platform artikel sains dan teknologi. "
        "Tugas Anda adalah meninjau permohonan banding dari pengguna yang diblokir karena "
        "mengunggah link yang terindikasi phishing sebanyak 3 kali. Evaluasi alasan mereka "
        "secara objektif. Jika tautan tersebut ternyata adalah salah deteksi (false positive) "
        "atau pengguna memiliki argumen kuat yang valid secara teknis, berikan keputusan TERIMA. "
        "Jika alasan mereka tidak masuk akal atau terbukti sengaja menyebarkan phishing, berikan keputusan TOLAK."
    )

    prompt_user = (
        f"Alasan Banding Pengguna: \"{payload.alasanBanding}\"\n\n"
        f"Berikut adalah data 3 artikel terakhir yang menyebabkan pengguna ini dibanned:\n"
        f"{konten_pelanggaran}\n"
        f"Berikan analisis Anda maksimal 10 kata 2 kalimat dan tentukan keputusan akhir."
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt_user,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=KeputusanGemini, 
                temperature=0.2 
            ),
        )

        hasil_analisis = KeputusanGemini.model_validate_json(response.text)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memproses analisis AI Gemini: {str(e)}"
        )


    if hasil_analisis.keputusan == "TERIMA":
        setattr(user, "isBanned", False)
        setattr(user, "warn", 0) 
        await db.commit()
        await db.refresh(user)
        
        return {
            "status": "Sukses",
            "keputusan": "TERIMA",
            "pesan": "Banding Anda diterima oleh AI. Akun Anda telah dipulihkan.",
            "analisis_ai": hasil_analisis.alasan_analisis
        }
    
    else:
        return {
            "status": "Gagal",
            "keputusan": "TOLAK",
            "pesan": "Banding Anda ditolak. Akun Anda tetap diblokir demi keamanan platform.",
            "analisis_ai": hasil_analisis.alasan_analisis
        }