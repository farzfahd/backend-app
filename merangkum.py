import os
import asyncio
import json
import time
import dotenv
from typing import List
from google import genai
from google.genai import types

# Mengambil kedua API Key (Pastikan key ini valid di sistem Anda)
KEY_1 = os.getenv("GEMINI_API_KEY1")
KEY_2 = os.getenv("GEMINI_API_KEY2")

# Membuat DUA client yang berbeda untuk masing-masing API Key
client1 = genai.Client(api_key=KEY_1)
client2 = genai.Client(api_key=KEY_2)


def split_text(text: str, max_chars: int = 12000) -> List[str]:
    """Membagi teks berdasarkan paragraf agar rapi dan tidak memotong kalimat."""
    paragraphs = text.split("\n")
    chunks = []
    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para: continue
        candidate = current + ("\n\n" if current else "") + para
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current: chunks.append(current)
            if len(para) <= max_chars: current = para
            else:
                for i in range(0, len(para), max_chars):
                    chunks.append(para[i:i + max_chars])
                current = ""
    if current: chunks.append(current)
    return chunks

async def summarize_chunk_with_client(client: genai.Client, chunk: str, client_id: int, model: str = "gemini-2.5-flash") -> str:
    """Merangkum teks potongan secara asinkron dengan fitur coba ulang (Retry)."""
    
    user_prompt = (
        "Ekstrak informasi penting dari teks di bawah ini dalam Bahasa Indonesia.\n"
        "Fokuslah pada:\n"
        "1. Gagasan atau fenomena utama.\n"
        "2. Dampak, tantangan, atau konsekuensi.\n"
        "Buatlah dalam bentuk poin-poin padat agar mudah digabungkan nantinya.\n\n"
        f"Teks:\n{chunk}"
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=1500
                )
            )
            
            if response.text:
                return response.text.strip()
            return response.candidates[0].content.parts[0].text.strip()
            
        except Exception as e:
            if "503" in str(e) or "429" in str(e):
                if attempt < max_retries - 1:
                    waktu_tunggu = (attempt + 1) * 2
                    print(f"[Warning] API Key {client_id} sibuk (503/429). Mencoba ulang dalam {waktu_tunggu} detik...")
                    await asyncio.sleep(waktu_tunggu)
                    continue
            return f"[API Key {client_id} Gagal]: {str(e)}"


async def summarize_article_dual_api(article_text: str, model: str = "gemini-2.5-flash") -> str:
    """Menggabungkan draf potongan menjadi satu output JSON murni yang terstruktur."""
    article_text = article_text.strip()
    if not article_text:
        return '{"error": "Teks input kosong."}'

    # 1. Potong teks menjadi beberapa bagian
    chunks = split_text(article_text)
    print(f"[Info] Memproses {len(chunks)} bagian secara paralel...")
    
    # 2. Distribusikan beban ke dua API Key
    tasks = []
    for i, chunk in enumerate(chunks):
        selected_client = client1 if i % 2 == 0 else client2
        tasks.append(summarize_chunk_with_client(selected_client, chunk, i % 2 + 1, model=model))

    try:
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=45.0)
    except Exception as e:
        return f'{{"error": "Gagal saat proses paralel: {e}"}}'

    # 3. Gabungkan hasil draf
    combined_draft = "\n\n".join([f"Draf Bagian {i+1}:\n{res}" for i, res in enumerate(results)])

    # 4. Prompt Final Khusus JSON
    final_prompt = (
        "Buatlah ringkasan eksekutif yang jelas, mendalam, dan selesai sepenuhnya dari data draf di bawah ini.\n"
        "Anda bebas menentukan berapa banyak poin yang dibutuhkan (antara 3 hingga 5 poin) sesuai dengan urgensi informasi.\n\n"
        "Output WAJIB mengikuti skema JSON berikut:\n"
        "{\n"
        "  \"judul_ringkasan\": \"Judul eksekutif yang relevan\",\n"
        "  \"poin_ringkasan\": [\n"
        "    \"Poin pertama (maksimal 2 kalimat, langsung ke inti).\",\n"
        "    \"Poin kedua (maksimal 2 kalimat, langsung ke inti).\"\n"
        "  ]\n"
        "}\n\n"
        "PERATURAN KETAT:\n"
        "- Setiap elemen di dalam array 'poin_ringkasan' maksimal hanya terdiri dari 2 kalimat.\n"
        "- Pastikan kalimat terakhir pada setiap poin selesai sempurna dan tidak menggantung.\n\n"
        f"Data draf:\n{combined_draft}"
    )

    # 5. Panggil API penutup dengan konfigurasi JSON
    try:
        response = await client1.aio.models.generate_content(
            model=model,
            contents=final_prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=3000,
                response_mime_type="application/json" # KUNCI UTAMA OUTPUT JSON
            )
        )
        
        if response.text:
            return response.text.strip()
        return response.candidates[0].content.parts[0].text.strip()
        
    except Exception as e:
        return f'{{"error": "Gagal pada penggabungan akhir: {e}"}}'


def summarize(article: str):
    article_text = article

    start_time = time.time()
    
    summary_json_str = asyncio.run(summarize_article_dual_api(article_text))
    
    nama_file = "hasil_ringkasan.json"
    
    try:
        parsed_data = json.loads(summary_json_str)

        return parsed_data
        
    except json.JSONDecodeError:
        return summary_json_str