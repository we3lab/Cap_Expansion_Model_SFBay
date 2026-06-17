from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os
import pandas as pd

def scale_facilities(input_file, output_file, n_plants):
    """
    Creates a scaled facility CSV by duplicating rows from the original.

    Args:
        input_file  : path to original CSV (3 facility rows)
        output_file : path to save the new CSV
        n_plants    : number of facilities (any multiple or partial multiple of 3)
    """
    df = pd.read_csv(input_file)
    n_original = len(df)

    rows = [df.iloc[i].copy() for i in range(n_original)]  # keep original rows

    for extra in range(n_plants - n_original):
        source_idx = extra % n_original          # cycles through 0, 1, 2, 0, 1, 2 ...
        copy_number = (extra // n_original) + 2  # 2 for first copy, 3 for second, etc.

        source_row = df.iloc[source_idx].copy()
        source_row["WWTP"]         = str(source_row["WWTP"])         + str(copy_number)
        source_row["Abbreviation"] = str(source_row["Abbreviation"]) + str(copy_number)
        rows.append(source_row)

    result = pd.DataFrame(rows).reset_index(drop=True)
    result.to_csv(output_file, index=False)
    print(f"[scale_facilities] {n_plants} facilities written to: {output_file}")
    return result

# Script that runs sensitivity analysis for all coordination cases as a function of discharge multipliers

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath)     
params = json.load(open(fp))


params["seasonal_regulation"] = True
params["sensitivity_analysis"] = True
params["update_figures"] = False
params["unit_cost_analysis"] = False

min_plants = 3
max_plants = 9
plant_projections = np.arange(min_plants, max_plants + 1, 1) 
input_file = params["WWTP_data_path"]

params["thread_num"] = 8
params["mingap_tag"] = 0.01 

#for staged_scenario in ["Non_Staged", "Staged"]:
for staged_scenario in ["Staged"]:
    if staged_scenario == "Non_Staged":
        params["staged_infrastructure"]= False
        params["version_num"] = 'Sensitivity_all_coordination_PlantNumb_NS'
    
    elif staged_scenario == "Staged":
        params["staged_infrastructure"]= True
        params["version_num"] = 'Sensitivity_all_coordination_PlantNumb_S'
    
    for i, mult in enumerate(plant_projections):
        mult = int(mult)
        scale_facilities(input_file, f"Input_Data/Input_Data_numb_facilities/Lower_South_Bay_input{mult}.csv", mult)
        params["WWTP_data_path"] = f"Input_Data/Input_Data_numb_facilities/Lower_South_Bay_input{mult}.csv"

        # No coordination
        params['Constraint_tag'] = 'No_coordination'

        ## Optimize for infrastructure
        params["joint_infrastructure"]= False
        ## Assume that there is no trading market
        params["trading_market"] = False                     

        
        ## Sensitivity 
        params['figpath'] = 'Results/' + params['version_num'] +  "/" + params['Constraint_tag'] + "/"  + str(mult) + "/" 
        params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params['Constraint_tag'] +  "_" + str(mult) + "_" 

        if not os.path.exists(params['figpath']):
            os.makedirs(params['figpath'])

        m = capacity_expansion(params)
        m.main()

        print("completed no coordination optimization for run = {}".format(i))



        # Partial coordination
        params['Constraint_tag'] = 'Partial_coordination'

        # Allow for only trading markets
        
        params["joint_infrastructure"]= False
        params["trading_market"] = True      
        params["trading_market_year"] = 0
        params["unfix_infrastructure_year"] = 0           

        # year when market is established
        ## save the capex file path to read the capex results
        params['figpath_capex'] = params['figpath']  

        params['figpath'] = 'Results/' + params['version_num'] +  "/" + params['Constraint_tag'] + "/"  + str(mult) + "/" 
        params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params['Constraint_tag'] +  "_" + str(mult) + "_" 

        if not os.path.exists(params['figpath']):
            os.makedirs(params['figpath'])

        m = capacity_expansion(params)
        m.main()

        print("completed partial coordination optimization for run = {}".format(i))


        # Full coordination
        params['Constraint_tag'] = 'Full_coordination'

        # Allow for only trading markets
        
        params["joint_infrastructure"]= True
        params["trading_market"] = True
        params["trading_market_year"] = 0
        params["unfix_infrastructure_year"] = 0                   

        params['figpath'] = 'Results/' + params['version_num'] +  "/" + params['Constraint_tag'] + "/"  + str(mult) + "/" 
        params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params['Constraint_tag'] +  "_" + str(mult) + "_" 

        if not os.path.exists(params['figpath']):
            os.makedirs(params['figpath'])

        m = capacity_expansion(params)
        m.main()

        print("completed full coordination optimization for run = {}".format(i))

        
        print("completed all optimization for run = {}".format(i))