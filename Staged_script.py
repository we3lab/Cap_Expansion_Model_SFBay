from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os

# Script that optimizes regional infrastructure for S-NC, S-PC, and S-FC cases

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath) 
params = json.load(open(fp))

# Initialize parameters
params["version_num"] = 'Staged'
params["capex_costing_method"] = "flow"
if params["capex_costing_method"] == "flow":
    params["version_num"] = params["version_num"] + "_flow_costing"

params["seasonal_regulation"] = True
params["sensitivity_analysis"] = False
params["update_figures"] = False

# Staged infrastructure
params["staged_infrastructure"]= True

params["trading_market_year"] = 0
params["unfix_infrastructure_year"] = 0  
params["marginal_cost_analysis"] = False


# Case 2: Staged, not coordinated
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



# Case 4: staged, partially coordinated
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


# Case 6: staged, fully coordinated
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


# Case 7: staged, fully coordinated, coordination at year 10
year = 10
params['Constraint_tag'] = 'Full_coordination_' + str(year) + '_yr'

## Allow for only trading markets
params["joint_infrastructure"]= True
params["trading_market"] = True    
params["trading_market_year"] = year
params["unfix_infrastructure_year"] = year                 


## New figure path for capex optimization
params['figpath'] = 'Results/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params["Constraint_tag"] + "_" 

if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

m = capacity_expansion(params)
m.main()
print("completed staged and fully coordinated optimization for year = {}".format(year))


# Case 8: staged, fully coordinated, coordination at year 20
year = 20
params['Constraint_tag'] = 'Full_coordination_' + str(year) + '_yr'

## Allow for only trading markets
params["joint_infrastructure"]= True
params["trading_market"] = True    
params["trading_market_year"] = year
params["unfix_infrastructure_year"] = year                 


## New figure path for capex optimization
params['figpath'] = 'Results/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params["Constraint_tag"] + "_" 

if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

m = capacity_expansion(params)
m.main()

print("completed staged and fully coordinated optimization for year = {}".format(year))