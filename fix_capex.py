from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath)     
params = json.load(open(fp))

params["version_num"] = 'Only_fix_build_16Nov24'
params["seasonal_regulation"] = True
params["sensitivity_analysis"] = False
params["update_figures"] = False
params["fix_infrastructure"]= False

params["Constraint_tag"] = "Individual"


params["projection_multiplier"] = 1.0

if params["seasonal_regulation"]:
    file_tag = "Seasonal/"
else:
    file_tag = "Year_round/"

params['figpath'] = 'Figures/' + params['version_num'] +  "/" + file_tag + "capex_opt/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + file_tag + "capex_opt_" 

if not os.path.exists(params['figpath']):
    os.makedirs(params['figpath'])

m = capacity_expansion(params)

m.main()

print("completed capex optimization run")


# Operating cost only
params["fix_infrastructure"]= True
params["Constraint_tag"] = "Subembayment"       # operating market always running
params["unfix_infrastructure_year"] = None      # no joint infrastructure can be built


## save the capex file path to read the capex results
params['figpath_capex'] = params['figpath']    



## create new figure path for opex optimization
params['figpath'] = 'Figures/' + params['version_num'] +  "/" + file_tag + "opex_opt/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + file_tag + "opex_opt_" 

if not os.path.exists(params['figpath']):
    os.makedirs(params['figpath'])

m = capacity_expansion(params)

m.main()

print("completed opex optimization run")


# Capital + Operating cost optimization


params["fix_infrastructure"]= False 
params["Constraint_tag"] = "Subembayment"

## create new figure path for capex_opex optimization
params['figpath'] = 'Figures/' + params['version_num'] +  "/" + file_tag + "capex_opex_opt/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + file_tag + "capex_opex_opt_" 

if not os.path.exists(params['figpath']):
    os.makedirs(params['figpath'])

m = capacity_expansion(params)

m.main()

print("completed capex and opex optimization run")

