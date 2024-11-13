import marimo

__generated_with = "0.9.14"
app = marimo.App()


@app.cell
def types():
    # All your imports should be in this cell
    from dataclasses import dataclass
    from CapExpModel import capacity_expansion
    import numpy as np
    import pandas as pd
    from matplotlib import pyplot as plt 
    import os, json, warnings
    import plotly.express as px
    import plotly.io as pio


    import expd as ex

    @dataclass
    class Inputs(ex.Model):
        a: ex.NonNeg[float]
        b: str

    @dataclass
    class Outputs(ex.Model):
        a: dict
    return (
        Inputs,
        Outputs,
        capacity_expansion,
        dataclass,
        ex,
        json,
        np,
        os,
        pd,
        pio,
        plt,
        px,
        warnings,
    )


@app.cell
def trial(Inputs, Outputs, capacity_expansion, json, os):
    def trial(inputs: Inputs) -> Outputs:

        basepath = "CapExpParams.json"
        fp = os.path.join(os.getcwd(),basepath)     
        params = json.load(open(fp))

        params["projection_multiplier"] = inputs.a
        params["version_num"] = inputs.b

        if params['seasonal_regulation']:
            params['figpath'] = 'Figures/' + params['version_num'] + "/Seasonal/" + params['Constraint_tag'] + "/"
            params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + params['Constraint_tag'] + "_Seasonal_" 
        else:
            params['figpath'] = 'Figures/' + params['version_num'] + "/Year_round/" + params['Constraint_tag'] + "/"
            params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + params['Constraint_tag'] + "_YearRound_" 



        if not os.path.exists(params['figpath']):
            os.makedirs(params['figpath'])


        m = capacity_expansion(params)
        model = m.main() 

        results_dict = m.summary.to_dict(orient='index')

        return Outputs(
            a=results_dict
        )
    return (trial,)


@app.cell
def __(Inputs, trial):
    trial(Inputs(a=1, b="test_version"))
    return


if __name__ == "__main__":
    app.run()
