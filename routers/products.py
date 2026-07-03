from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import BarangModel
from schemas import BarangCreate, BarangResponse, BarangResponseLengkap

router = APIRouter(
  prefix="/products",
  tags=['Products']
)

@router.get("/", response_model=list[BarangResponse])
async def get_product(db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(BarangModel))
  daftar_barang = result.scalars().all()
  return daftar_barang

@router.post("/", response_model=BarangResponse, status_code=201)
async def post_product(barang_input: BarangCreate, db: AsyncSession = Depends(get_db)):
  db_barang = BarangModel(
    nama=barang_input.nama, 
    harga=barang_input.harga, 
    userId=barang_input.userId,
    deskripsi = barang_input.deskripsi,
    jenisBarang = barang_input.jenisBarang
  )
  db.add(db_barang)
  await db.commit()
  await db.refresh(db_barang)
  return db_barang

@router.get("/{productId}", response_model=list[BarangResponseLengkap])
async def getFullInfoProduct(productId: int, db: AsyncSession = Depends(get_db)):
  user = await db.execute(select(BarangModel).where(BarangModel.id == productId))

  if user is None:
    raise HTTPException(
      status_code=404,
      detail = f"Tidak ada barang dengan ID {productId}"
    )
  
  return user.scalar_one_or_none()