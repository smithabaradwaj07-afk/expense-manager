from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import re

from app.database import SessionLocal, engine, Base
from app.models import User, Expense

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Password hashing
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# JWT config
SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"

# Security
security = HTTPBearer()

# ------------------ MODELS ------------------

class UserCreate(BaseModel):
    email: str
    password: str = Field(max_length=100)


class LoginRequest(BaseModel):
    email: str
    password: str


class ExpenseCreate(BaseModel):
    amount: float
    category: str
    description: str


class SMSInput(BaseModel):
    message: str


# ------------------ UTILS ------------------

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")


# ------------------ SMS LOGIC ------------------

def extract_amount(text: str):
    match = re.search(r'(?i)(rs\.?|inr)\s?(\d+)', text)
    return float(match.group(2)) if match else None


def extract_merchant(text: str):
    text_lower = text.lower()

    # Known merchants (expandable list)
    known_merchants = [
        "swiggy", "zomato", "uber", "ola",
        "amazon", "flipkart", "myntra",
        "netflix", "spotify", "paytm", "phonepe", "gpay"
    ]

    for merchant in known_merchants:
        if merchant in text_lower:
            return merchant.upper()

    # fallback: try to extract word after "to" or "for"
    match = re.search(r'(to|for)\s+([a-zA-Z]+)', text_lower)
    if match:
        return match.group(2).upper()

    return "UNKNOWN"


def categorize(merchant: str):
    merchant = merchant.lower()

    if any(x in merchant for x in ["swiggy", "zomato", "restaurant", "cafe"]):
        return "food"
    elif any(x in merchant for x in ["uber", "ola", "rapido"]):
        return "transport"
    elif any(x in merchant for x in ["amazon", "flipkart", "myntra"]):
        return "shopping"
    elif any(x in merchant for x in ["netflix", "spotify", "prime"]):
        return "subscription"
    else:
        return "other"


# ------------------ ROUTES ------------------

@app.get("/")
def home():
    return {"message": "Expense Manager API is running"}


@app.post("/signup")
def signup(user: UserCreate):
    db = SessionLocal()
    try:
        hashed_password = pwd_context.hash(user.password)

        new_user = User(email=user.email, password=hashed_password)

        db.add(new_user)
        db.commit()

        return {"message": "User created successfully"}

    except IntegrityError:
        db.rollback()
        return {"error": "Email already exists"}

    finally:
        db.close()


@app.post("/login")
def login(user: LoginRequest):
    db = SessionLocal()

    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user:
        return {"error": "User not found"}

    if not verify_password(user.password, db_user.password):
        return {"error": "Invalid password"}

    payload = {
        "sub": user.email,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": token}


@app.get("/profile")
def profile(user: str = Depends(get_current_user)):
    return {"message": f"Hello {user}, you are authenticated"}


# ------------------ EXPENSE APIs ------------------

@app.post("/expense")
def add_expense(expense: ExpenseCreate, user: str = Depends(get_current_user)):
    db = SessionLocal()

    try:
        new_expense = Expense(
            amount=expense.amount,
            category=expense.category.lower(),  # ✅ FIX
            description=expense.description,
            user_email=user
        )

        db.add(new_expense)
        db.commit()

        return {"message": "Expense added successfully"}

    finally:
        db.close()


# ✅ FIXED SMS API
@app.post("/parse-sms")
def parse_sms(data: SMSInput, user: str = Depends(get_current_user)):
    db = SessionLocal()

    try:
        text = data.message

        amount = extract_amount(text)
        merchant = extract_merchant(text)
        category = categorize(merchant)

        if not amount:
            raise HTTPException(status_code=400, detail="Could not extract amount")

        new_expense = Expense(
            amount=amount,
            category=category,   # ✅ ALWAYS clean category
            description=merchant,
            user_email=user
        )

        db.add(new_expense)
        db.commit()

        return {
            "message": "Expense auto-created",
            "amount": amount,
            "merchant": merchant,
            "category": category
        }

    finally:
        db.close()


@app.get("/expenses")
def get_expenses(user: str = Depends(get_current_user)):
    db = SessionLocal()

    try:
        return db.query(Expense).filter(Expense.user_email == user).all()
    finally:
        db.close()


@app.get("/total")
def total_spending(user: str = Depends(get_current_user)):
    db = SessionLocal()

    try:
        expenses = db.query(Expense).filter(Expense.user_email == user).all()
        return {"total_spent": sum(exp.amount for exp in expenses)}
    finally:
        db.close()


# ✅ FIXED CATEGORY FILTER
@app.get("/expenses/{category}")
def get_by_category(category: str, user: str = Depends(get_current_user)):
    db = SessionLocal()

    try:
        expenses = db.query(Expense).filter(
            Expense.user_email == user,
            func.lower(Expense.category) == category.lower()
        ).all()

        return expenses

    finally:
        db.close()


@app.get("/monthly")
def monthly_report(user: str = Depends(get_current_user)):
    db = SessionLocal()

    try:
        result = db.query(
            func.date_trunc('month', Expense.created_at).label("month"),
            func.sum(Expense.amount).label("total")
        ).filter(
            Expense.user_email == user
        ).group_by("month").all()

        return [
            {"month": str(row.month), "total": float(row.total)}
            for row in result
        ]

    finally:
        db.close()

@app.get("/insights")
def get_insights(user: str = Depends(get_current_user)):
    db = SessionLocal()

    try:
        expenses = db.query(Expense).filter(Expense.user_email == user).all()

        if not expenses:
            return {"message": "No data available"}

        total = sum(exp.amount for exp in expenses)

        # ---------------- CATEGORY BREAKDOWN ----------------
        category_totals = {}
        for exp in expenses:
            cat = exp.category
            category_totals[cat] = category_totals.get(cat, 0) + exp.amount

        category_percentages = {
            cat: round((amt / total) * 100, 2)
            for cat, amt in category_totals.items()
        }

        # ---------------- TOP CATEGORY ----------------
        top_category = max(category_totals, key=category_totals.get)

        # ---------------- WARNINGS ----------------
        warnings = []

        if category_percentages.get("food", 0) > 40:
            warnings.append("⚠️ High food spending")

        if category_percentages.get("shopping", 0) > 40:
            warnings.append("⚠️ High shopping spending")

        if category_percentages.get("transport", 0) > 30:
            warnings.append("⚠️ High transport spending")

        # ---------------- PREDICTION ----------------
        from datetime import datetime

        now = datetime.utcnow()
        current_day = now.day

        if current_day > 0:
            daily_avg = total / current_day
            projected_monthly = round(daily_avg * 30, 2)
        else:
            projected_monthly = total

        # ---------------- ANOMALY DETECTION ----------------
        amounts = [exp.amount for exp in expenses]
        avg = sum(amounts) / len(amounts)

        anomalies = []
        for exp in expenses:
            if exp.amount > 2 * avg:
                anomalies.append({
                    "amount": exp.amount,
                    "category": exp.category,
                    "description": exp.description,
                    "reason": "Unusually high compared to your average spending"
                })

        # ---------------- RESPONSE ----------------
        return {
            "total_spent": total,
            "avg_transaction": round(avg, 2),
            "category_breakdown": category_percentages,
            "top_category": top_category,
            "warnings": warnings,
            "projected_monthly_spend": projected_monthly,
            "anomalies": anomalies
        }

    finally:
        db.close()