import pandas as pd
import numpy as np
import re
import os

# ------------------------------------------------------------------ #
# CONFIGURE THESE TO MATCH YOUR PATHS                                 #
# ------------------------------------------------------------------ #
min_plants = 3
max_plants = 9
plant_projections = np.arange(min_plants, max_plants + 1, 1) 
base_path         = "Results/Sensitivity_all_coordination_PlantNumb_S/"   

# ------------------------------------------------------------------ #
# PATCH EACH CSV WITH WORK UNITS FROM THE CORRESPONDING LOG           #
# ------------------------------------------------------------------ #
for constraint_tag in ["No_coordination", "Partial_coordination", "Full_coordination"]:
    for i, mult in enumerate(plant_projections):
        log_path = base_path + f"{constraint_tag}_{mult}_solver_log.txt"
        csv_path = base_path + f"{constraint_tag}_{mult}_computational_cost.csv"

        # --- Check files exist ---------------------------------------- #
        if not os.path.exists(log_path):
            print(f"[{mult}] WARNING: Log file not found at {log_path}, skipping.")
            continue
        if not os.path.exists(csv_path):
            print(f"[{mult}] WARNING: CSV file not found at {csv_path}, skipping.")
            continue

        # --- Parse work units from log --------------------------------- #
        work_units = None
        with open(log_path, 'r') as f:
            log = f.read()

        match = re.search(r'in\s+([\d.]+)\s+seconds\s+\(([\d.]+)\s+work units\)', log)
        if match:
            work_units = float(match.group(2))
            print(f"[{mult}] Work units found: {work_units}")
        else:
            print(f"[{mult}] WARNING: Work units not found in log, skipping.")
            continue

        # --- Load CSV and update Work Units row ------------------------ #
        df = pd.read_csv(csv_path)

        # Check if Work Units row already exists
        mask = (df["Section"] == "Solver") & (df["Name"] == "Work Units")

        if mask.any():
            # Row exists — update the value
            df.loc[mask, "Count"] = work_units
            print(f"[{mult}] Work Units row updated.")
        else:
            # Row doesn't exist — insert it after Solve Time row
            solve_time_idx = df[(df["Section"] == "Solver") & (df["Name"] == "Solve Time (s)")].index
            insert_at = int(solve_time_idx[0]) + 1 if len(solve_time_idx) > 0 else len(df)

            new_row = pd.DataFrame([{
                "Section":    "Solver",
                "Name":       "Work Units",
                "Type":       "-",
                "Count":      work_units,
                "Index Sets": "-",
                "Notes":      ""
            }])

            df = pd.concat([df.iloc[:insert_at], new_row, df.iloc[insert_at:]], ignore_index=True)
            print(f"[{mult}] Work Units row inserted.")

        # --- Save back to CSV ------------------------------------------ #
        df.to_csv(csv_path, index=False)
        print(f"[{mult}] CSV saved to {csv_path}")

    print("\nDone with constraint tag:", constraint_tag)