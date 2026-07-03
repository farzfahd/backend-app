from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import date, datetime

class BarangCreate(BaseModel):
  nama: str = Field(..., min_length = 1, max_length=50)
  harga: float = Field(..., gt = 0)
  userId: int = Field(..., gt=0)
  deksripsi: str = Field(..., min_length=10)
  jenisBarang: list[str] 

class BarangResponse(BaseModel):
  id:int
  nama:str
  harga:float
  userId:int

  class Config:
    from_attributes = True

class BarangResponseLengkap(BaseModel):
  id:int
  nama:str
  harga:float
  userId:int
  deskripsi:str

  class Config:
    from_attributes = True

# ===================== Schema untuk Users.py ===================== 

class PenggunaRegistrasi(BaseModel):
  username: str = Field(..., min_length=3, max_length=100)
  email: EmailStr = Field(..., min_length=5)
  nomor: str = Field(..., min_length=5)
  password: str = Field(..., min_length=8)

class PenggunaRegistrasi2(BaseModel): 
  tanggalLahir: str
  kelas: str = Field(..., min_length=3)
  bidang: list[str]
  kabupaten: str = Field(..., min_length=3)
  provinsi: str = Field(..., min_length=8)

  @field_validator('tanggalLahir', mode='before')
  @classmethod
  def ubah_format_tanggal(cls, nilai):
    if isinstance(nilai, str):
      try:
        return datetime.strptime(nilai, "%d/%m/%Y").date()
      except ValueError:
        raise ValueError("Format tanggal harus dd-MM-yyyy (Contoh: 25-12-1995)")
    return nilai

class ResponseDataPenting(BaseModel):
  id:int
  username: str
  email: str
  nomor: str 

  class Config:
    from_attributes = True

class ResponseDataDiri(BaseModel):
  tanggalLahir: date
  kelas: str 
  bidang: list[str]
  kabupaten: str 
  provinsi: str 
  
  class Config:
    from_attributes = True

class PenggunaLogin(BaseModel):
  value:str
  loginType:str
  password:str

class PenggunaAuth(BaseModel):
  token:str

class GantiPassword(BaseModel):
  passwordLama: str
  passwordBaru: str

class UbahDataPenting(BaseModel):
  username: str | None = Field(None, min_length=3, max_length=100)
  email: EmailStr | None = Field(None)
  nomor: str | None = Field(None, min_length=5) 

class UbahDataDiri(BaseModel):
  tanggalLahir: date | None = Field(None)
  kelas: str | None = Field(None, min_length=3)
  bidang: list[str] | None = Field(None)  
  kabupaten: str | None = Field(None, min_length=3)
  provinsi: str | None = Field(None, min_length=8)

  @field_validator('tanggalLahir', mode='before')
  @classmethod
  def ubah_format_tanggal_patch(cls, nilai):
    if nilai is None:
        return nilai
    if isinstance(nilai, str):
      try:
        return datetime.strptime(nilai, "%d/%m/%Y").date()
      except ValueError:
        pass
    return nilai


# ===================== Schema untuk Article.py ===================== 
class TambahArticle(BaseModel):
  userId: int
  judul: str = Field(..., min_length=1, max_length=30)  
  dekripsiSingkat: str = Field(..., max_length=50)      
  deskripsi: str
  mediaSosial: dict[str, str] | None = None
  linkWebsite: str | None = None
  contactPerson: dict[str, str] | None = None
  tanggalMulai: date | None = None                      
  tanggalAkhir: date | None = None
  kategori: str = Field(..., max_length=50)
  subKategori: str = Field(..., max_length=50)
  
class CardArticle(BaseModel):
  id: int
  judul: str
  deskripsiSingkat: str

  class Config:
    from_attributes = True

class AjukanBanding(BaseModel):
    userId: int
    alasanBanding: str

class KeputusanGemini(BaseModel):
    keputusan: str = Field(description="Hanya boleh diisi 'TERIMA' atau 'TOLAK'")
    alasan_analisis: str = Field(description="Alasan logis mengapa banding diterima atau ditolak berdasarkan bukti artikel")