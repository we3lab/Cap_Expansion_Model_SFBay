from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath)     
params = json.load(open(fp))

params["version_num"] = 'loop_over_market_years_14Nov24'
params["seasonal_regulation"] = True


params["sensitivity_analysis"] = False
params["update_figures"] = False
params["only_opex_trading"]= False

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


params["only_opex_trading"]= True

# year when market is established
## if market_year = 0; then market is established at time = 0
## if market_year = 30; then market is established only at the end of the simulation
market_years = np.linspace(0,30,31).astype(np.int64)

## save the capex file path to read the capex results
params['figpath_capex'] = params['figpath']  

# loop over all years
for year in market_years:
    params["market_year"] = year
    params["Constraint_tag"] = "Subembayment"

    ## create new figure path for opex optimization
    params['figpath'] = 'Figures/' + params['version_num'] +  "/" + file_tag + "opex_opt/" + str(year) + "/" 
    params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + file_tag + "opex_opt_"  + str(year) + "_" 

    if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

    m = capacity_expansion(params)

    m.main()

    print('completed opex optimization run for market year:', year)

print("completed opex optimization run for all years")