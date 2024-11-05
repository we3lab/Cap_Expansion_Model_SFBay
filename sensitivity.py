from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath)     
params = json.load(open(fp))

params["version_num"] = 'sensivity_analysis_31Oct24'
params["Constraint_tag"] = "Subembayment"
params["seasonal_regulation"] = True

params["sensitivity_analysis"] = True
params["update_figures"] = False


projection_multipliers = np.linspace(0.8,1.1, 50)


for i, mult in enumerate(projection_multipliers):
    params["projection_multiplier"] = mult

    if not os.path.exists('Sensitivity/'):
        os.makedirs('Sensitivity/')

    if params['seasonal_regulation']:
        params['figpath'] = 'Sensitivity/' + params['version_num'] + "/Seasonal/" + params['Constraint_tag'] + "/"  + str(mult) + "/" 
        params['figpath_base'] = 'Sensitivity/' + params['version_num'] + "/Seasonal/" + params['Constraint_tag'] + "_" + str(mult) + "_" 
    else:
        params['figpath'] = 'Sensitivity/' + params['version_num'] + "/Year_round/" + params['Constraint_tag'] + "/"  + str(mult) + "/" 
        params['figpath_base'] = 'Sensitivity/' + params['version_num'] + "/Year_round/" + params['Constraint_tag'] + "_" + str(mult) + "_" 

    if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

    m = capacity_expansion(params)



    m.main()

    print("completed sensitivity run {}".format(i+1))