from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os

# Script that optimizes regional infrastructure for all six cases assuming an exponential projection for the flow and load projections

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath) 
params = json.load(open(fp))

# Initialize parameters
params["projected_flow_assumption"]= "exponential"

params["seasonal_regulation"] = True
params["sensitivity_analysis"] = False
params["update_figures"] = False

# Set parameters
params["trading_market_year"] = 0
params["unfix_infrastructure_year"] = 0  
params["marginal_cost_analysis"] = False



for staged_scenario in ["Non_Staged", "Staged"]:
    if staged_scenario == "Non_Staged":
        params["staged_infrastructure"]= False
        params["version_num"] = 'Exponential_projection_NS'
    elif staged_scenario == "Staged":
        params["staged_infrastructure"]= True
        params["version_num"] = 'Exponential_projection_S'

    # Case 1/2: Not coordinated
    params["Constraint_tag"] = 'No_coordination'
        ## Assume no joint_infrastructure
    params["joint_infrastructure"]= False
        ## Assume that there is no trading market
    params["trading_market"] = False 

    params['figpath'] = 'Results/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
    params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params["Constraint_tag"] + "_"

    if not os.path.exists(params['figpath']):
            os.makedirs(params['figpath'])

    m = capacity_expansion(params)
    m.main()

    print("completed staged and not coordinated optimization for run")



    # Case 3/4: partially coordinated
    params['Constraint_tag'] = 'Partial_coordination'

        ## Allow for only trading markets
    params["joint_infrastructure"]= False
    params["trading_market"] = True                 


        ## save the capex file path to read the capex results
    params['figpath_capex'] = params['figpath']  

    params['figpath'] = 'Results/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
    params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params["Constraint_tag"] + "_" 

    params['figpath_opex_partial'] = params['figpath']

    if not os.path.exists(params['figpath']):
            os.makedirs(params['figpath'])

    m = capacity_expansion(params)
    m.main()

    print("completed staged and partially coordinated optimization for run")


    # Case 5/6: Fully coordinated
    params['Constraint_tag'] = 'Full_coordination'

        ## Allow for only trading markets
    params["joint_infrastructure"]= True
    params["trading_market"] = True                 


        ## save the capex file path to read the capex results
    params['figpath_capex'] = params['figpath']  

    params['figpath'] = 'Results/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
    params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params["Constraint_tag"] + "_" 

    if not os.path.exists(params['figpath']):
            os.makedirs(params['figpath'])

    m = capacity_expansion(params)
    m.main()
    print("completed staged and fully coordinated optimization for run")