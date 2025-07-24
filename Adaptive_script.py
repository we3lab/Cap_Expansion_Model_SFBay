from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath) 
params = json.load(open(fp))

# Initialize parameters
params["version_num"] = 'Adaptive_11Jun25'
params["seasonal_regulation"] = True
params["sensitivity_analysis"] = False
params["update_figures"] = False

# Adaptive infrastructure
params["adaptive_infrastructure"]= True

params["trading_market_year"] = 0
params["unfix_infrastructure_year"] = 0  
params["marginal_cost_analysis"] = True



# Case 2: Staged, not coordinated
params["Constraint_tag"] = 'No_coordination'
    ## Assume no joint_infrastructure
params["joint_infrastructure"]= False
    ## Assume that there is no trading market
params["trading_market"] = False 

params['figpath'] = 'Figures/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + params["Constraint_tag"] + "_"

if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

m = capacity_expansion(params)
m.main()

print("completed adaptive and not coordinated optimization for run")



# Case 4: Adaptive, partially coordinated
params['Constraint_tag'] = 'Partial_coordination'

    ## Allow for only trading markets
params["joint_infrastructure"]= False
params["trading_market"] = True                 


    ## save the capex file path to read the capex results
params['figpath_capex'] = params['figpath']  

params['figpath'] = 'Figures/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + params["Constraint_tag"] + "_" 

params['figpath_opex_partial'] = params['figpath']

if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

m = capacity_expansion(params)
m.main()

print("completed adaptive and partially coordinated optimization for run")


# Case 6: Adaptive, fully coordinated
params['Constraint_tag'] = 'Full_coordination'

    ## Allow for only trading markets
params["joint_infrastructure"]= True
params["trading_market"] = True                 


    ## save the capex file path to read the capex results
params['figpath_capex'] = params['figpath']  

params['figpath'] = 'Figures/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + params["Constraint_tag"] + "_" 

if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

m = capacity_expansion(params)
m.main()
print("completed adaptive and fully coordinated optimization for run")


# Case 7: Adaptive, fully coordinated, coordination at year 10
year = 10
params['Constraint_tag'] = 'Full_coordination_' + str(year) + '_yr'

## Allow for only trading markets
params["joint_infrastructure"]= True
params["trading_market"] = True    
params["trading_market_year"] = year
params["unfix_infrastructure_year"] = year                 


## New figure path for capex optimization
params['figpath'] = 'Figures/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + params["Constraint_tag"] + "_" 

if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

m = capacity_expansion(params)
m.main()
print("completed adaptive and fully coordinated optimization for year = {}".format(year))


# Case 8: Adaptive, fully coordinated, coordination at year 20
year = 20
params['Constraint_tag'] = 'Full_coordination_' + str(year) + '_yr'

## Allow for only trading markets
params["joint_infrastructure"]= True
params["trading_market"] = True    
params["trading_market_year"] = year
params["unfix_infrastructure_year"] = year                 


## New figure path for capex optimization
params['figpath'] = 'Figures/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + params["Constraint_tag"] + "_" 

if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

m = capacity_expansion(params)
m.main()

print("completed adaptive and fully coordinated optimization for year = {}".format(year))