from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os


# Script that optimizes regional infrastructure for NS-NC, NS-PC, and NS-FC cases

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath)     
params = json.load(open(fp))

# Initialize parameters
params["version_num"] = 'Non_Staged'
params["capex_costing_method"] = "load"
if params["capex_costing_method"] == "flow":
    params["version_num"] = params["version_num"] + "_flow_costing"

params["seasonal_regulation"] = True
params["sensitivity_analysis"] = False
params["update_figures"] = False
params["unit_cost_analysis"] = False

# Not staged infrastructure
params["staged_infrastructure"]= False



# Case 1: Not staged, not coordinated
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

print("completed not staged and not coordinated optimization for run")



# Case 3: Not staged, partially coordinated
params['Constraint_tag'] = 'Partial_coordination'

    ## Allow for only trading markets
params["joint_infrastructure"]= False
params["trading_market"] = True                 


    ## save the capex file path to read the capex results
params['figpath_capex'] = params['figpath']  

params['figpath'] = 'Results/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params["Constraint_tag"] + "_" 

if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

m = capacity_expansion(params)
m.main()

print("completed not staged and partially coordinated optimization for run")


# Case 5: Not staged, fully coordinated
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

print("completed not staged and fully coordinated optimization for run")