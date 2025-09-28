# HeraShift – AI Leave & Coverage Planner

HeraShift is a Streamlit + MongoDB app that helps teams manage shifts and PTO coverage.

## 🚀 Quick start

```bash
# Clone
git clone https://github.com/ReyanshBhootra/herashift.git
cd herashift

# Setup venv
python -m venv .venv
. .venv/Scripts/activate   # Windows
# source .venv/bin/activate  # Mac/Linux

# Install deps
pip install -r requirements.txt

# Copy env template
cp .env.example .env   # Windows: copy .env.example .env

# Seed demo data
python -m app.seed.seed_data

# Run app
streamlit run app/streamlit_app.py


PROJECT LAYOUT:
herashift/
│── app/
│   ├── db.py
│   ├── scheduler.py
│   ├── streamlit_app.py
│   ├── ...
│   └── seed/
│       └── seed_data.py
│
│── requirements.txt
│── .gitignore
│── README.md         <-- add this
│── .env.example      <-- add this

