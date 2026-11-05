# Heat Shield - sample worker roster (fake data for testing)
import random
from datetime import date, timedelta
import pandas as pd
from faker import Faker

fake = Faker()
random.seed(1)
Faker.seed(1)

# The 5 Boston pilot sites and the jobs at each one
sites = {
    "Jean Brooks Landscapes": ["Landscaper", "Crew Lead"],
    "Duffy Roofing Co.": ["Roofer", "Roofing Helper"],
    "Olympia Moving & Storage": ["Mover", "Warehouse Worker"],
    "M&M BBQ": ["Line Cook", "Dishwasher"],
    "A C Hand Car Wash": ["Car Washer", "Detailer"],
}

# Languages workers might speak
languages = ["English", "Spanish", "Portuguese", "Haitian Creole", "Vietnamese"]

# Pretend "today" is a hot summer day
today = date(2026, 7, 15)

workers = []
for i in range(1, 26):                        # repeat 25 times
    site = random.choice(list(sites))         # pick a site
    job = random.choice(sites[site])          # pick a job at that site
    start = today - timedelta(days=random.randint(1, 60))  # started 1-60 days ago
    days_worked = (today - start).days

    workers.append({
        "worker_id": f"W{i:03d}",             # W001, W002, ...
        "name": fake.name(),
        "site": site,
        "job": job,
        "language": random.choice(languages),
        "phone": f"617-555-{random.randint(1000, 9999)}",  # fake 555 numbers
        "start_date": start,
        "days_worked": days_worked,
        "is_new": days_worked < 14,
        "acclimatized": days_worked >= 14,    # NIOSH: about 14 days to adjust to heat
    })


# Turn the list into a table and save it
roster = pd.DataFrame(workers)
roster.to_csv("sample_roster.csv", index=False)

# Check: load it back in pandas (your Friday benchmark)
check = pd.read_csv("sample_roster.csv")
print(check.head())
print("Workers:", len(check), "| Columns:", len(check.columns))
print("Acclimatized:", check["acclimatized"].sum(), "| Not yet:", (~check["acclimatized"]).sum())
