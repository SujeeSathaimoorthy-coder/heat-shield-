"""Heat index ("feels like" temperature) for Heat Shield.

Uses the National Weather Service (NWS) method:
https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml
"""

import math


def heat_index(temp_f, rh):
    """Return the heat index in degrees F.

    temp_f: air temperature in Fahrenheit
    rh:     relative humidity in percent (0-100)
    """
    if not 0 <= rh <= 100:
        raise ValueError(f"Humidity must be between 0 and 100, got {rh}.")

    T = temp_f
    RH = rh

    # Step 1: simple formula. NWS says: average it with the temperature,
    # and if that is under 80F, the simple result is good enough.
    simple = 0.5 * (T + 61.0 + (T - 68.0) * 1.2 + RH * 0.094)
    if (simple + T) / 2 < 80:
        return simple

    # Step 2: full NWS formula (Rothfusz regression)
    hi = (-42.379
          + 2.04901523 * T
          + 10.14333127 * RH
          - 0.22475541 * T * RH
          - 0.00683783 * T * T
          - 0.05481717 * RH * RH
          + 0.00122874 * T * T * RH
          + 0.00085282 * T * RH * RH
          - 0.00000199 * T * T * RH * RH)

    # Step 3: NWS adjustments
    if RH < 13 and 80 <= T <= 112:          # very dry air
        hi -= ((13 - RH) / 4) * math.sqrt((17 - abs(T - 95)) / 17)
    elif RH > 85 and 80 <= T <= 87:         # very humid air
        hi += ((RH - 85) / 10) * ((87 - T) / 5)

    return hi


def risk_level(hi):
    """NWS risk bands for a heat index value."""
    if hi >= 125:
        return "Extreme Danger"
    if hi >= 103:
        return "Danger"
    if hi >= 90:
        return "Extreme Caution"
    if hi >= 80:
        return "Caution"
    return "Lower risk"
