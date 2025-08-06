This repository allows you to optimize regional investment portfolios for WWTPs in Lower South San Fransisco Bay

The steps below will show you how to: 
    (1) set-up your environment 
    (2) reproduce the manuscript results using the python analysis script 
    (3) reproduce the manuscript figures using the jupyter notebooks

1. Setting up your environment:
     1) Use the .yml file to activate your environment by running the following code in your terminal:
               conda env create -f environment.yml
     2) Activate your environment:
               conda activate sfbaycap   
   
3. Running python analysis scripts:
   The main directory contains four python scripts that will allow you to reproduce the results produced from this work. 
     1) Non_Staged_script.py: This script will run the capacity expansion optimization model (CapExpModel.py) using parameters that constrain the model to non-staged infrastructure planning (see manuscript for equations). This will create a folder in the Results directory titled "Non-Staged" that contains all csv file results for Non-coordinated (NS-NC), partially coordinated (NS-PC), and fully coordinated (NS-FC) infrastructure planning cases.
     2) Staged_script.py: This script will run the capacity expansion optimization model (CapExpModel.py) using parameters that constrain the model to staged infrastructure planning (see manuscript for equations). This will create a folder in the Results directory titled "Staged" that contains all csv file results for Non-coordinated (S-NC), partially coordinated (S-PC), and fully coordinated (S-FC) infrastructure planning cases.
     3) Unit_cost_PC_analysis.py: This script will run CapExpModel.py for S-PC (staged, partially coordinated) and computes the unit cost of treatment for all combination of WWTPs for a specified month (defined as unit_cost_dt). This will create a folder in the Results directory titled "Unit_cost_by_WWTP" that contains separate csv file for each timestep assesed.
     4) Sensitivity_analysis_discharge.py: This script will run CapExpModel.py for specified discharge scenarios defined by a mult that places a multiplier on the BACWA 30-year projection. For example, a mult=1.2 will optimize the infrastructure for a projected discharge 120% greater than the BACWA projection. The results of this sensitivity analysis will be saved as csv files in the Results directory in a folder titled "Sensitivity_all_coordination_S". For non-staged sensitivity results, set the parameter for "staged_infrastructure" to false and save the results in the folder "Sensitivity_all_coordination_NS".

4. Running jupyter notebooks:
   The directory "Jupyter_Scripts_for_Figures" contains all jupyter notebooks used to produce figures for this manuscript. The notebooks will import data from the Results directory (see previous step) and produce the required figures. All figures will be saved in the 'Figures' or 'Figures/SI' directory.


For questions, suggestions, or issues, please contact Sinan Abi Farraj (sinanaf@stanford.edu).
