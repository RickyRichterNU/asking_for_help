import pathlib
import os
from functools import \
    partial 
import numpy as np
import time
 
#idmtools   
from idmtools.assets import Asset, AssetCollection  
from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

#emodpy
from emodpy.emod_task import EMODTask
from emodpy.utils import EradicationBambooBuilds
from emodpy.bamboo import get_model_files
import emod_api.config.default_from_schema_no_validation as dfs
import emod_api.campaign as camp
import emod_api.interventions.common as common#added for change properties

from emod_api import schema_to_class as s2c#added for change properties

#emodpy-malaria
import emodpy_malaria.demographics.MalariaDemographics as Demographics
import emodpy_malaria.interventions.treatment_seeking as cm
import emod_api.demographics.PreDefinedDistributions as Distributions
from emodpy_malaria.reporters.builtin import *



import manifest


#sim_years = 1
# as a global variable at the top of the script, like sim_years that we use to define simulation duration:
#serialize_years = 50
serialize_years = 2
num_seeds = 3 #sets the number of random seeds


###CONFIG######
#change all config parameters here
def set_param_fn(config):
    """
    This function is a callback that is passed to emod-api.config to set config parameters, including the malaria defaults.
    """
    import emodpy_malaria.malaria_config as conf
    config = conf.set_team_defaults(config, manifest)

    config.parameters.Air_Temperature_Filename = os.path.join('climate','example_air_temperature_daily.bin')
    config.parameters.Land_Temperature_Filename = os.path.join('climate','example_air_temperature_daily.bin')
    config.parameters.Rainfall_Filename = os.path.join('climate','example_rainfall_daily.bin')
    config.parameters.Relative_Humidity_Filename = os.path.join('climate', 'example_relative_humidity_daily.bin')

    conf.add_species(config, manifest, ["gambiae", "arabiensis", "funestus"])

    config.parameters.Simulation_Duration = serialize_years*365
    config.parameters.Run_Number = 0
    config.parameters.x_Temporary_Larval_Habitat = 0.316228
    config.parameters.x_Birth = 3.62


    # add to config parameter setup
    config.parameters.Base_Individual_Sample_Rate = 1   
    config.parameters.Inset_Chart_Include_Pregnancies = 1
    
    config.parameters.Serialized_Population_Writing_Type = "TIMESTEP"
    config.parameters.Serialization_Time_Steps = [365 * serialize_years]
    config.parameters.Serialization_Mask_Node_Write = 0
    config.parameters.Serialization_Precision = "REDUCED"
    return config
  

# This creats a function with parameters param and values which can be used later in the sim builder to generate sweeps over a parameter
def set_param(simulation, param, value):
    """
    Set specific parameter value
    Args:
        simulation: idmtools Simulation
        param: parameter
        value: new value
    Returns:
        dict
    """
    return simulation.task.set_parameter(param, value)

###CAMPAIGNS#######
def build_camp():
    """
    This function builds a campaign input file for the DTK using emod_api.
    """

    camp.set_schema(manifest.schema_file)

    common.change_individual_property_triggered(camp, 
                              new_ip_key='Pregnancy', new_ip_value='IsPregnant',
                              target_sex="Female", triggers=['Pregnant'], daily_prob = 1, revert_in_days = -1, blackout=True)
    common.change_individual_property_triggered(camp, 
                              new_ip_key='Pregnancy', new_ip_value='NotPregnant',
                              target_sex="Female", triggers=['GaveBirth'],daily_prob = 1, revert_in_days = -1, blackout=True)
    return camp


###DEMOGRAPHIC######
def build_demog():
    """
    This function builds a demographics input file for the DTK using emod_api.
    """

    demog = Demographics.from_template_node(lat=5.7376, lon=-0.4404, pop=3000, name="Example_Site")
    #demog.SetEquilibriumVitalDynamics()

    age_distribution = Distributions.AgeDistribution_SSAfrica
    demog.SetAgeDistribution(age_distribution)
    

    
    # Add custom IP to demographics                              
    initial_distribution = [1, 0] 
    demog.AddIndividualPropertyAndHINT(Property="Pregnancy", Values=["NotPregnant", "IsPregnant"],
                                        InitialDistribution=initial_distribution)
    
    return demog

def general_sim(selected_platform):
    """
    This function is designed to be a parameterized version of the sequence of things we do 
    every time we run an emod experiment. 
    """

    # Set platform and associated values, such as the maximum number of jobs to run at one time
    platform = Platform(selected_platform, job_directory=manifest.job_directory, partition='b1139', time='2:00:00',
                            account='b1139', modules=['singularity'], max_running_jobs=10)

    # create EMODTask 
    print("Creating EMODTask (from files)...")

    
    task = EMODTask.from_default2(
        config_path="config.json",
        eradication_path=manifest.eradication_path,
        campaign_builder=build_camp,
        schema_path=manifest.schema_file,
        param_custom_cb=set_param_fn,
        ep4_custom_cb=None,
        demog_builder=build_demog,
        plugin_report=None
    )
    
    
    # set the singularity image to be used when running this experiment
    task.set_sif(manifest.SIF_PATH, platform)
    task.config.parameters.Birth_Rate_Dependence = "INDIVIDUAL_PREGNANCIES"
    event_list=['Pregnant','GaveBirth']
    task.config.parameters.Custom_Individual_Events = ['Ind_Property_Blackout']
    
    #add weather directory as an asset
    task.common_assets.add_directory(os.path.join(manifest.input_dir, "example_weather", "out"), relative_path="climate")
    
    # Create simulation sweep with builder
    builder = SimulationBuilder()
    builder.add_sweep_definition(partial(set_param, param='Run_Number'), range(num_seeds))


    #adding event recorder
    add_event_recorder(task, event_list=event_list,
                        start_day=1, end_day=serialize_years*365,
                        min_age_years=0,
                        max_age_years=100,
                        ips_to_record=['Pregnancy'],
                        property_change_ip_to_record="Pregnancy"
                        )

    # create experiment from builder
    user = os.getlogin()
    experiment = Experiment.from_builder(builder, task, name= f'{user}_FE_example_burnin50_IP')


    # The last step is to call run() on the ExperimentManager to run the simulations.
    experiment.run(wait_until_done=False, platform=platform)




if __name__ == "__main__":
    import emod_malaria.bootstrap as dtk
    import pathlib

    dtk.setup(pathlib.Path(manifest.eradication_path).parent)

    selected_platform = "SLURM_LOCAL"
    general_sim(selected_platform)
