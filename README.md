#Expense Intelligence System

An intelligent backend system that automatically tracks, categorizes, and analyzes user expenses using SMS parsing and financial insights.

 Features

- JWT-based Authentication
-  SMS Parsing Engine (auto expense detection)
-  Smart Categorization (Swiggy → Food, Amazon → Shopping)
-  Expense Analytics Dashboard (API-based)
- Behavioral Insights (high spending alerts)
-  Monthly Spending Prediction
- Anomaly Detection (unusual transactions)

## Tech Stack

- FastAPI (Backend)
- PostgreSQL (Database)
- SQLAlchemy (ORM)
- JWT Authentication
- Python (Core Logic)

##  API Endpoints

| Endpoint | Description |
|--------|------------|
| `/signup` | Register user |
| `/login` | Get JWT token |
| `/expense` | Add manual expense |
| `/parse-sms` | Auto-create expense from SMS |
| `/expenses` | Get all expenses |
| `/insights` | Get analytics & predictions |

##  Sample Insight Output

json
{
  "total_spent": 10800,
  "category_breakdown": {
    "food": 18.52,
    "shopping": 74.07
  },
  "warnings": ["⚠️ High shopping spending"],
  "projected_monthly_spend": 40500,
  "anomalies": [
    {
      "amount": 6000,
      "category": "shopping",
      "description": "AMAZON"
    }
  ]
}
