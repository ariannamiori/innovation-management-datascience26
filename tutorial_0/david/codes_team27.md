# Team 27 · Utility-scale energy storage: patent codes used

Client: Enel · Tutorial 0, Step 1 · Notebook `02_step1_general_description_team27.ipynb`

## What a CPC code is

Every patent gets one or more **CPC codes**: technology labels, like shelf numbers in a library. A code is read from general to specific:

| Part | Example | Meaning |
|---|---|---|
| Section | `H` | Electricity |
| Class | `H02` | Generating, converting or distributing electric power |
| Subclass | `H02J` | Supplying or distributing electric power |
| Group | `H02J3/28` | Balancing the grid load by storing energy |

Codes starting with **`Y02`** are special tags that the patent office adds to climate-related technologies, on top of the normal codes.

**Our rule:** an invention (patent family) belongs to our sector if **at least one** of its patents has a code **starting with** one of the codes below.

## The six codes we use now

| Code | What it covers | Status |
|---|---|---|
| `Y02E60/10` | Energy storage using batteries | ⚠️ **Check.** Covers *all* batteries (phones, laptops, cars), not only grid batteries. In the TEST results, battery chemistry (H01M) was only ~4% of the sector, so the effect looks small. Re-check on PROD. |
| `Y02E60/14` | Thermal energy storage (storing heat or cold) | ⚠️ **Check.** May include small heat storage in homes and buildings. |
| `Y02E60/16` | Mechanical energy storage, e.g. flywheels, compressed air | OK |
| `H02J3/28` | Balancing the load of the power grid by storing energy | OK, the core grid code |
| `H02J3/32` | Same, using batteries with power converters | OK. In the CPC tree it sits under `H02J3/28`, but "starts with" matching does not pick it up automatically, so it must be listed. |
| `H02J15/00` | Systems for storing electric energy | ⚠️ **Check.** Broad. Read its definition and any subgroups. |

Verify each code in the official scheme: <https://www.cooperativepatentclassification.org> (search the code, read its title and notes).

## Codes to discuss adding

These come from our earlier Step 0 work. They cover storage types the six codes may miss:

| Code | What it covers |
|---|---|
| `H02J3/30` | Grid balancing using flywheels |
| `Y02E60/13` | Energy storage using capacitors |
| `F03B13/06` | Pumped hydro (water pumped uphill, released through a turbine) |
| `F02C6/16` | Compressed air energy storage (CAES) in gas-turbine plants |
| `H01M8/18` | Redox flow batteries |
| `H01M10/39` | High-temperature batteries, e.g. sodium-sulfur |
| `Y02E70/30` | Storage combined with renewable generation |

## Keywords (not active yet)

Prepared in the notebook but switched off (commented out), so the first run uses codes only. To compare, switch them on and re-run. An invention then also counts if its title or abstract contains one of these phrases:

pumped storage · pumped hydro · compressed air energy storage · liquid air energy storage · redox flow · flow battery · grid-scale / utility-scale energy storage · battery energy storage system · long-duration energy storage

## Open decisions for the group

1. Keep the six codes, or add some from the list above?
2. Switch the keywords on?
3. Last year counted: 2021 (safer, since 2022 still looks incomplete) or 2022?
4. All results so far are from **TEST** (a small sample): use trends and shares, not exact numbers.
