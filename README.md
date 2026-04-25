# Case: Macro Data Refinement

## Scenario
Welcome to Arturic Industries, Macro Data Refinement division.

Your task is to process the quarterly output files and calculate the final output metric for the quarter.

Your Welcome Packet contains orientation materials and instructions for accessing the Arturic Industries Employee Portal, where you will find the processing specifications.

## Objective
Calculate the **sum of all valid entry values** across all departments.

## Deliverable
- A git repository with your code.
- The final sum.
- A brief explanation (~400 words) of your methodology and any anomalies you encountered.

## Notes
Your facility photo serves as verification of your assigned location.

## Run

Use the project entry point:

```bash
python3 main.py
```

Useful options:

```bash
# Output raw stats as JSON
python3 main.py --json

# Run against a custom sessions directory
python3 main.py --sessions-root /path/to/sessions

# Disable strict key checking for entry payloads
python3 main.py --no-strict-entry-keys
```
