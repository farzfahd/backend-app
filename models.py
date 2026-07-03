from sqlalchemy import Column, Integer, String, Numeric, ARRAY, Date, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class BarangModel(Base):
  __tablename__ = "barang"

  id = Column(Integer, primary_key=True, index = True)
  nama = Column(String(100), nullable = False)
  harga = Column(Numeric, nullable = False)
  userId=Column(Numeric, nullable=False)
  jenisBarang = Column(ARRAY(String), default=list)

class Article(Base):
  __tablename__ = "artikel"

  id = Column(Integer, primary_key=True, index=True)
  userId = Column(Integer, nullable=False)
  judul = Column(String(30), nullable=False)
  summarize = Column(Text, nullable=True)
  dekripsiSingkat = Column(String(50), nullable=False)
  deskripsi = Column(Text, nullable=False)
  linkWebsite = Column(Text, nullable=True)
  tanggalMulai = Column(Date, nullable=True)
  tanggalAkhir = Column(Date, nullable=True)
  kategori = Column(String(50), nullable=False)
  subKategori = Column(String(50), nullable=False)
  isVisible = Column(Boolean, default=True)
    
  mediaSosial = Column(JSONB, nullable=True, default={})
  contactPerson = Column(JSONB, nullable=True, default={})

class PenggunaModel(Base):
  __tablename__ = "pengguna"

  id = Column(Integer, primary_key=True, index = True)
  username = Column(String(100))
  email = Column(String(100))
  nomor = Column(String(20))
  password = Column(String(100))
  tanggalLahir = Column(Date)
  kelas = Column(String(100))
  bidang = Column(ARRAY(String), default=list)
  kabupaten = Column(String(100))
  provinsi = Column(String(100))
  artikelTersimpan = Column(ARRAY(Integer), default=list)
  isBanned = Column(Boolean, default=False)
  warn = Column(Integer, default=0)
  