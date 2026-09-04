"""NIFTY 50 constituents, sector mapping, and point-in-time membership seed.

Sector mapping is stored explicitly (documented data source). Historical
membership uses a documented import mechanism — here we seed a validity window
with a labelled source rather than inventing precise historical constituents.
See docs/API_INTEGRATIONS.md and docs/DATABASE_SCHEMA.md.
"""

# (symbol, company name, sector). Source: NSE NIFTY 50 index (labelled seed).
NIFTY50 = [
    ("RELIANCE", "Reliance Industries", "Energy"),
    ("TCS", "Tata Consultancy Services", "IT"),
    ("HDFCBANK", "HDFC Bank", "Financials"),
    ("ICICIBANK", "ICICI Bank", "Financials"),
    ("INFY", "Infosys", "IT"),
    ("HINDUNILVR", "Hindustan Unilever", "FMCG"),
    ("ITC", "ITC", "FMCG"),
    ("SBIN", "State Bank of India", "Financials"),
    ("BHARTIARTL", "Bharti Airtel", "Telecom"),
    ("LT", "Larsen & Toubro", "Infrastructure"),
    ("KOTAKBANK", "Kotak Mahindra Bank", "Financials"),
    ("AXISBANK", "Axis Bank", "Financials"),
    ("BAJFINANCE", "Bajaj Finance", "Financials"),
    ("ASIANPAINT", "Asian Paints", "Consumer"),
    ("MARUTI", "Maruti Suzuki", "Auto"),
    ("HCLTECH", "HCL Technologies", "IT"),
    ("SUNPHARMA", "Sun Pharma", "Pharma"),
    ("TITAN", "Titan Company", "Consumer"),
    ("ULTRACEMCO", "UltraTech Cement", "Cement"),
    ("WIPRO", "Wipro", "IT"),
    ("NESTLEIND", "Nestle India", "FMCG"),
    ("ONGC", "Oil & Natural Gas Corp", "Energy"),
    ("NTPC", "NTPC", "Power"),
    ("POWERGRID", "Power Grid Corp", "Power"),
    ("TATAMOTORS", "Tata Motors", "Auto"),
    ("TATASTEEL", "Tata Steel", "Metals"),
    ("JSWSTEEL", "JSW Steel", "Metals"),
    ("ADANIENT", "Adani Enterprises", "Diversified"),
    ("ADANIPORTS", "Adani Ports", "Infrastructure"),
    ("COALINDIA", "Coal India", "Energy"),
    ("BAJAJFINSV", "Bajaj Finserv", "Financials"),
    ("HDFCLIFE", "HDFC Life Insurance", "Financials"),
    ("SBILIFE", "SBI Life Insurance", "Financials"),
    ("GRASIM", "Grasim Industries", "Cement"),
    ("BRITANNIA", "Britannia Industries", "FMCG"),
    ("EICHERMOT", "Eicher Motors", "Auto"),
    ("HEROMOTOCO", "Hero MotoCorp", "Auto"),
    ("BAJAJ-AUTO", "Bajaj Auto", "Auto"),
    ("CIPLA", "Cipla", "Pharma"),
    ("DRREDDY", "Dr Reddy's Labs", "Pharma"),
    ("DIVISLAB", "Divi's Laboratories", "Pharma"),
    ("APOLLOHOSP", "Apollo Hospitals", "Healthcare"),
    ("TATACONSUM", "Tata Consumer Products", "FMCG"),
    ("BPCL", "Bharat Petroleum", "Energy"),
    ("INDUSINDBK", "IndusInd Bank", "Financials"),
    ("TECHM", "Tech Mahindra", "IT"),
    ("HINDALCO", "Hindalco Industries", "Metals"),
    ("SHRIRAMFIN", "Shriram Finance", "Financials"),
    ("LTIM", "LTIMindtree", "IT"),
    ("M&M", "Mahindra & Mahindra", "Auto"),
]

SECTOR_INDEX = {
    "IT": "NIFTYIT", "Financials": "BANKNIFTY", "Auto": "NIFTYAUTO",
    "Pharma": "NIFTYPHARMA", "FMCG": "NIFTYFMCG", "Metals": "NIFTYMETAL",
    "Energy": "NIFTYENERGY",
}

SYMBOLS = [s[0] for s in NIFTY50]
SECTOR_OF = {s[0]: s[2] for s in NIFTY50}
NAME_OF = {s[0]: s[1] for s in NIFTY50}
