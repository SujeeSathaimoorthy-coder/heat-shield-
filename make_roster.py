# Heat Shield - sample worker roster (fake data for testing)
#
# PRIVACY: no names, no phone numbers. Each worker is only a worker_id
# like W001. (ChiEAC rule 4: nothing that identifies a worker.)
import random
from datetime import date, timedelta

import pandas as pd

random.seed(1)

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

# The sample weather is the real Boston heat wave of June 21-27, 2025,
# so the roster pretends "today" is the first day of that week.
plan_start = date(2025, 6, 21)

workers = []
for i in range(1, 26):                        # repeat 25 times
    site = random.choice(list(sites))         # pick a site
    job = random.choice(sites[site])          # pick a job at that site

    # About 1 in 3 workers start during the heat wave week (new workers),
    # the rest started 3 weeks to 2 months earlier.
    if random.random() < 0.35:
        start = plan_start + timedelta(days=random.randint(-2, 4))
    else:
        start = plan_start - timedelta(days=random.randint(21, 60))

    # About 1 in 5 of the earlier workers was away for over a week and
    # comes back during the heat wave (returning workers).
    return_date = ""
    if start < plan_start - timedelta(days=14) and random.random() < 0.25:
        return_date = plan_start + timedelta(days=random.randint(0, 3))

    workers.append({
        "worker_id": f"W{i:03d}",             # W001, W002, ...
        "site": site,
        "job": job,
        "language": random.choice(languages),
        "start_date": start,                  # hire date
        "return_date": return_date,           # blank = not away
    })


# Turn the list into a table and save it
roster = pd.DataFrame(workers)
roster.to_csv("sample_roster.csv", index=False)

# Check: load it back in pandas
check = pd.read_csv("sample_roster.csv")
print(check.head())
print("Workers:", len(check), "| Columns:", len(check.columns))
print("Returning workers:", check["return_date"].notna().sum())
