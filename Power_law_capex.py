from CapExpModel import capacity_expansion
from pyomo.environ import SolverFactory, Var
import os, json
import numpy as np
import os

"""
Solves the capacity_expansion() Pyomo model by:
1. Subclassing capacity_expansion to intercept the built model
2. Deactivating the nonlinear capex_monthly_cond_power constraint
3. Injecting equivalent constraints using addGenConstrPow (native Gurobi)
4. Solving and writing results back to Pyomo variables
"""



def get_grb_var(solver, pyomo_var):
    """Map a Pyomo scalar variable to its gurobipy counterpart."""
    return solver._pyomo_var_to_solver_var_map[id(pyomo_var)]


class capacity_expansion_patched(capacity_expansion):
    """
    Subclass that intercepts build() to store the model as self.model,
    then overrides main() to inject addGenConstrPow instead of the
    nonlinear capex_monthly_cond_power constraint.
    """
    def __init__(self, params):
        self.params = params       # store before calling super().__init__
        super().__init__(params)
    
    def build(self):
        """Call parent build() and cache the returned model."""
        self.model = super().build()
        return self.model

    def main(self, mip_gap=0.01, time_limit=3000, threads=8):
        # 1. Build the model
        if not hasattr(self, "model"):
            self.build()
        model = self.model

        # 2. Deactivate the nonlinear constraint
        model.capex_monthly_cond_power.deactivate()

        # 3. Compile into gurobipy via gurobi_direct
        solver = SolverFactory("gurobi_direct")
        solver._presolve(model)
        grb = solver._solver_model  # underlying gurobipy Model
        grb.Params.FuncNonlinear = 1    # required for power functions with exponents < 1

        # 4. Inject power-law constraints via addGenConstrPow
        power_law_grb = {}  # (WWTP, L) -> gurobipy Var holding alpha*x_max^beta
        
        capex_costing_power = self.params["capex_costing_power"]

        for WWTP in model.WWTP:
            for L in capex_costing_power:

                alpha_wl = model.alpha[WWTP, L]
                beta_wl  = model.beta[WWTP, L]

                # auxiliary: x_pow = x_max[WWTP, L] ^ beta
                x_pow = grb.addVar(lb=0, name=f"x_pow_{WWTP}_{L}")
                grb.addGenConstrPow(
                    get_grb_var(solver, model.x_max[WWTP, L]),
                    x_pow,
                    beta_wl,
                    name=f"pow_{WWTP}_{L}",
                )
                grb.update()

                if L == "L2upg3":
                    # Special case:
                    #   capex = u * (alpha[L2upg3]*x_max[L2upg3]^beta[L2upg3]
                    #              - alpha[L2]    *x_max[L2]    ^beta[L2])
                    alpha_l2 = model.alpha[WWTP, "L2"]
                    beta_l2  = model.beta[WWTP, "L2"]

                    x_pow_l2 = grb.addVar(lb=0, name=f"x_pow_{WWTP}_L2_for_upg3")
                    grb.addGenConstrPow(
                        get_grb_var(solver, model.x_max[WWTP, "L2"]),
                        x_pow_l2,
                        beta_l2,
                        name=f"pow_{WWTP}_L2_for_upg3",
                    )
                    grb.update()

                    power_law_val = grb.addVar(lb=-1e9, name=f"power_law_{WWTP}_{L}")
                    grb.addConstr(
                        power_law_val == alpha_wl * x_pow - alpha_l2 * x_pow_l2,
                        name=f"scale_{WWTP}_{L}",
                    )

                else:
                    power_law_val = grb.addVar(lb=0, name=f"power_law_{WWTP}_{L}")
                    grb.addConstr(
                        power_law_val == alpha_wl * x_pow,
                        name=f"scale_{WWTP}_{L}",
                    )

                grb.update()
                power_law_grb[(WWTP, L)] = power_law_val

        # 5. Big-M linearisation of capex_monthly = u * power_law
        M = max(
            float(model.alpha[WWTP, L]) * self.x_max_allupgrades ** float(model.beta[WWTP, L])
            for WWTP in model.WWTP
            for L in capex_costing_power
        )

        for WWTP in model.WWTP:
            for L in capex_costing_power:
                pl = power_law_grb[(WWTP, L)]
                for t in model.t:
                    cm  = get_grb_var(solver, model.capex_monthly[WWTP, L, t])
                    u_v = get_grb_var(solver, model.u[WWTP, L, t])

                    grb.addConstr(cm <= M * u_v, name=f"bil_ub1_{WWTP}_{L}_{t}")
                    grb.addConstr(cm <= pl, name=f"bil_ub2_{WWTP}_{L}_{t}")
                    grb.addConstr(cm >= pl - M * (1 - u_v),name=f"bil_lb_{WWTP}_{L}_{t}")

        grb.update()

        # 6. Solver parameters
        grb.Params.MIPGap    = mip_gap
        grb.Params.TimeLimit = time_limit
        grb.Params.Threads   = threads

        # 7. Solve
        grb.optimize()

        # 8. Write results back to Pyomo variables
        for v in model.component_data_objects(Var, active=True):
            try:
                grb_var = get_grb_var(solver, v)
                v.set_value(grb_var.X)
            except Exception:
                pass

        print(f"\nObjective: {grb.ObjVal:.4f}")
        print(f"MIP Gap:   {grb.MIPGap:.4%}")
        print(f"Status:    {grb.Status}")

        model = self.print_results(model)

        return model, grb


if __name__ == "__main__":
    basepath = "CapExpParams.json"
    fp = os.path.join(os.getcwd(), basepath)
    params = json.load(open(fp))

    for staged_scenario in ["Non_staged", "Staged"]:
    
        if staged_scenario == "Non_staged":
            params["staged_infrastructure"]= False
            params["version_num"] = 'Staged_Power_law_NS'
        elif staged_scenario == "Staged":
            params["staged_infrastructure"]= True
            params["version_num"] = 'Staged_Power_law_S'
        
        
        # Initialize parameters
        
        params["seasonal_regulation"] = True
        params["sensitivity_analysis"] = False
        params["update_figures"] = False
        params["unit_cost_analysis"] = False

        ## Specify which upgrades should follow the log law:
        params["capex_costing_linear"] = ["SS"]
        params["capex_costing_power"] = ["L2", "L3", "L2upg3"]


        
        # Case 1 or 2: No coordination:
        
        params["Constraint_tag"] = 'No_coordination'
            ## Assume no joint_infrastructure
        params["joint_infrastructure"]= False
            ## Assume that there is no trading market
        params["trading_market"] = False 

        params['figpath'] = 'Results/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
        params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params["Constraint_tag"] + "_"


        if not os.path.exists(params['figpath']):
                os.makedirs(params['figpath'])


        ce = capacity_expansion_patched(params)
        model, grb = ce.main()



        # Case 3 or 4: partially coordinated
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

        ce = capacity_expansion_patched(params)
        model, grb = ce.main()
        
        
        # Case 5 or 6: Full coordination

        params["Constraint_tag"] = 'Full_coordination'
            ## Assume no joint_infrastructure
        params["joint_infrastructure"]= True
            ## Assume that there is no trading market
        params["trading_market"] = True 

        params['figpath'] = 'Results/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
        params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params["Constraint_tag"] + "_"

        if not os.path.exists(params['figpath']):
                os.makedirs(params['figpath'])


        ce = capacity_expansion_patched(params)
        model, grb = ce.main()