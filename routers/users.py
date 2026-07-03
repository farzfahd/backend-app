import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database import get_db
from models import PenggunaModel
from schemas import PenggunaRegistrasi, PenggunaLogin, PenggunaRegistrasi2, PenggunaAuth, ResponseDataDiri, ResponseDataPenting, GantiPassword, UbahDataPenting, UbahDataDiri
from argon2 import PasswordHasher
from jwcrypto import jwt, jwk
from jwcrypto.jwt import JWTExpired
from jwcrypto.common import JWException
from dotenv import load_dotenv
import time
import os
from datetime import date, datetime

load_dotenv()
KEY = os.getenv("JWT_KEY")
ALG = os.getenv("ALGORITHM")
KEY_JWK = jwk.JWK(kty="oct", k=KEY)

router = APIRouter(
  prefix="/users",
  tags=['Users']
)
phash = PasswordHasher()

# ===================== Registration ===================== 

@router.post("/registration")
async def newUserRegistration(payload: PenggunaRegistrasi, db: AsyncSession = Depends(get_db)):
  """
  Mendaftarkan pengguna baru ke sistem.

    Args:
        payload (PenggunaRegistrasi): Data pengguna baru yang berisi
            username, email, nomor telepon, dan password.
        db (AsyncSession): Session database asynchronous yang digunakan
            untuk query dan penyimpanan data.

    Raises:
        HTTPException: 
            - 400 jika username, email, atau nomor telepon sudah digunakan.
            - 500 jika terjadi kesalahan saat menyimpan data.

    Returns:
        dict: Pesan konfirmasi pendaftaran berhasil.
  """
  query_check = select(PenggunaModel).where(
      (PenggunaModel.username == payload.username) | (PenggunaModel.email == payload.email) | (PenggunaModel.nomor == payload.nomor)
    )
  result_check = await db.execute(query_check)
  if result_check.scalar_one_or_none():
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Username atau email sudah digunakan"
    )
  hashedPassword = phash.hash(payload.password)

  newUser = PenggunaModel(
    username=payload.username, 
    nomor=payload.nomor, 
    email = payload.email, 
    password=hashedPassword
    )

  db.add(newUser)
  await db.commit()
  await db.refresh(newUser)

  token = jwtMaker(userId=newUser.id, username=newUser.username)

  return {
    "status": "Sukses",
    "token": token,
    "username": newUser.username,
    "userId": newUser.id
  }

@router.patch("/registration/{userId}")
async def nextUserRegistration(userId: int, payload: PenggunaRegistrasi2, db: AsyncSession = Depends(get_db)):
  queryCheck = select(PenggunaModel).where(PenggunaModel.id == userId)
  queryResult = await db.execute(queryCheck)
  user = queryResult.scalar_one_or_none()

  if not user:
    raise HTTPException(
      status_code=404,
      detail="User dengan ID tersebut tidak ditemukan"
    )
  
  updateData = payload.model_dump(exclude_unset=True)
  for key, value in updateData.items():
    setattr(user, key, value)

  await db.commit()
  await db.refresh(user)

  return {
    "status": "Sukses",
  }

# ===================== Login =====================
@router.post("/login")
async def loginUser(payload: PenggunaLogin, db: AsyncSession = Depends(get_db)):
  match payload.loginType:
    case "username":
      query = select(PenggunaModel).where(PenggunaModel.username == payload.value)
    case "email":
      query = select(PenggunaModel).where(PenggunaModel.email == payload.value)
    case "nomor handphone":
      query = select(PenggunaModel).where(PenggunaModel.nomor == payload.value)
    case _:
      raise HTTPException(
        status_code=401,
        detail=f"Tipe login tidak diketahui"
      ) 

  resultQuery = await db.execute(query)
  userSelected = resultQuery.scalar_one_or_none()

  if not userSelected:
    raise HTTPException(
      status_code=401,
      detail=f"{payload.loginType} atau Password salah"
    )
  
  isPasswordSame = phash.verify(hash=userSelected.password, password=payload.password)

  if not isPasswordSame:
    raise HTTPException(
      status_code=401,
      detail=f"{payload.loginType} atau Password salah"
    )
  
  token = jwtMaker(userId=userSelected.id, username=userSelected.username)
  
  return {
    "status": "Sukses",
    "token": token,
    "username": userSelected.username,
    "userId": userSelected.id
  }

@router.post("/auth-jwt")
async def authJWTUser(payload: PenggunaAuth):
  try:
    token = jwt.JWT(key=KEY_JWK, jwt=payload.token)
    resultToken = json.loads(token.claims)

    userId = resultToken.get("userId")
    username = resultToken.get("username")

    return {
      "status": "Sukses",
      "username": username,
      "userId": userId
    }
  except JWTExpired:
    raise HTTPException(
      status_code=401,
      detail={
        "code": "TOKEN_EXPIRED",
        "message": "Sesi Anda telah habis"
      }
    )
  except JWException as e:
    raise HTTPException(
      status_code=401,
      detail={
        "code": "TOKEN_FAILED",
        "message": str(e)
      }
    )


# ===================== By Id =====================
@router.get("/data-penting/{userId}", response_model=ResponseDataPenting)
async def userInformationImportant(userId: int, db: AsyncSession= Depends(get_db)):
  resultQuery = await db.execute(select(PenggunaModel).where(PenggunaModel.id == userId))
  user = resultQuery.scalar_one_or_none()

  if user is None:
    raise HTTPException(
      status_code=404,
      detail = f"Tidak ada user dengan ID {userId}"
    )
  
  return user

@router.get("/data-diri/{userId}", response_model=ResponseDataDiri)
async def userInformationPersonal(userId: int, db: AsyncSession= Depends(get_db)):
  resultQuery = await db.execute(select(PenggunaModel).where(PenggunaModel.id == userId))
  user = resultQuery.scalar_one_or_none()

  if user is None:
    raise HTTPException(
      status_code=404,
      detail = f"Tidak ada user dengan ID {userId}"
    )
  
  return user

@router.post("/ganti-password/{userId}")
async def changePassword(userId:int, payload: GantiPassword, db: AsyncSession= Depends(get_db)):
  resultQuery = await db.execute(select(PenggunaModel).where(PenggunaModel.id == userId))
  user = resultQuery.scalar_one_or_none()

  if user is None:
    raise HTTPException(
      status_code=404,
      detail = f"Tidak ada user dengan ID {userId}"
    )
  
  isPasswordSame = phash.verify(hash=user.password, password=payload.passwordLama)

  if not isPasswordSame:
    raise HTTPException(
      status_code=401,
      detail=f"Password salah"
    )
  
  hashedPassword = phash.hash(payload.passwordBaru)

  setattr(user, "password", hashedPassword)

  await db.commit()
  await db.refresh(user)

  return {
    "status": "Sukses",
  }

@router.patch("/data-diri/{userId}")
async def changePersonalData(userId: int, payload: UbahDataDiri, db: AsyncSession = Depends(get_db)):
  queryCheck = select(PenggunaModel).where(PenggunaModel.id == userId)
  queryResult = await db.execute(queryCheck)
  user = queryResult.scalar_one_or_none()

  if not user:
    raise HTTPException(
      status_code=404,
      detail="User dengan ID tersebut tidak ditemukan"
    )
  
  result = {
    "status": "Sukses",
  }

  updateData = payload.model_dump(exclude_unset=True)
  for key, value in updateData.items():
    if key == "username":
      result['token'] = jwtMaker(userId, value)
      result['username'] = value
    setattr(user, key, value)

  await db.commit()
  await db.refresh(user)

  return result

@router.patch("/data-penting/{userId}")
async def changeImportantData(userId: int, payload: UbahDataPenting, db: AsyncSession = Depends(get_db)):
  queryCheck = select(PenggunaModel).where(PenggunaModel.id == userId)
  queryResult = await db.execute(queryCheck)
  user = queryResult.scalar_one_or_none()

  if not user:
    raise HTTPException(
      status_code=404,
      detail="User dengan ID tersebut tidak ditemukan"
    )
  
  result = {
    "status": "Sukses",
  }
  
  updateData = payload.model_dump(exclude_unset=True)
  for key, value in updateData.items():
    query_cek = select(PenggunaModel).where(
      and_(
          getattr(PenggunaModel, key) == value,
          PenggunaModel.id != userId
        )
      )
    res_cek = await db.execute(query_cek)
    if res_cek.scalar_one_or_none():
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"{key.upper()}_ALREADY_TAKEN"
        )
    setattr(user, key, value)

  await db.commit()
  await db.refresh(user)

  return result

# ===================== Other Handler =====================

def jwtMaker(userId: int, username: str):
  timeNow = int(time.time())
  timeExp = timeNow + (30*24*60*60)

  payload = {
    "userId": userId,
    "username": username,
    "exp": timeExp
  }

  token = jwt.JWT(header={"alg": ALG}, claims=payload)
  token.make_signed_token(KEY_JWK)

  return token.serialize()


