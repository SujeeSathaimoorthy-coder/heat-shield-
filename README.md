# heat-shield
Heat safety plans made simple for small employers and outdoor workers
## The problem
New workers are put on full shifts in the heat with no slow start ,which is gap most linked to heat deaths .Small employers rarely fix it , because most states have no heat rule and writing a plan means reading a regulation , a NIOSH document and a weather forecast at the same time(NIOSH ,p,12. Brief section 1.1)
## What Heat Shield will do 
It helps small employers make a simple heat plan – water, rest, shade, and a slow start for new workers
## Who it is for
Small employers and outdoor workers in Boston, Massachusetts


## What's built so far (Week 2)
| File | What it does |
|------|--------------|
| `heat_rules.yaml` | Heat rules for 8 jurisdictions (NIOSH, Massachusetts, Boston, federal OSHA, California, Washington, Oregon, Maryland), each checked against the official text |
| `heat_index.py` | Heat index ("feels like" temperature) using the National Weather Service formula |
| `loaders.py` | Loads a worker roster from CSV or Excel and gives clear error messages |
| `weather.py` | Hourly forecast by ZIP code (Open-Meteo) and a reader for weather station CSVs |
| `tests/` | 39 automatic tests, including values from the NWS heat index chart |

**Key finding:** Massachusetts has no heat standard for private employers, and Boston's ordinance covers only city contractors. Heat Shield uses NIOSH guidance as its default.

## How to run it
```
pip install pandas pyyaml requests pytest openpyxl
python weather.py 02125
python -m pytest tests
```
