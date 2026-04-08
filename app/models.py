from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.database import Base


# 👤 USER MODEL
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)


# 💸 EXPENSE MODEL
class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    category = Column(String)
    description = Column(String)
    user_email = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)