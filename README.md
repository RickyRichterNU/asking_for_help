# asking_for_help

Hi Everyone, I am having some problems with the function change_individual_property_triggered in emod_api/interventions/common.py.

In my ReportEventRecorder.csv I want to track the individual property Pregnancy that can be values 'IsPregnant' or 'NotPregnant'

In my ReportEventRecorder.csv, I want to see three events 'Pregnant', 'GaveBirth' and 'PropertyChange' to reflect the different statuses of the IP Pregnancy.

However, in my ReportEventRecorder.csv I do not see the 'PropertyChange' event and in the Pregnancy column, all values are NotPregnant (even when the value should be IsPregnant).

I went back through dtk-tools/dtk/interventions to see what the differences there were between common.py and and property_change.py and decided to add blackout functionality from property_change.py to common.py to see if that would resolve the issue.
Unfortunately that did not change the output and after attempting a few other fixes I have not found a way to get change_individual_property_triggered in emod_api/interventions/common.py to function how I would expect/want it to.

If any of you can please give me some advice I'd greatly appreciate it. 

Here is some code from my run_burnin python script. If you would like to see all the code involved in this problem I have created this github repository here: https://github.com/RickyRichterNU/asking_for_help
```
def build_camp():
    """
    This function builds a campaign input file for the DTK using emod_api.
    """
    camp.set_schema(manifest.schema_file)

    common.change_individual_property_triggered(camp, 
                              new_ip_key='Pregnancy', new_ip_value='IsPregnant',
                              #ip_restrictions=[{'Pregnancy': 'NotPregnant'}],
                              target_sex="Female", triggers=['Pregnant'], daily_prob = 1, revert_in_days = -1, blackout=True)
    common.change_individual_property_triggered(camp, 
                              new_ip_key='Pregnancy', new_ip_value='NotPregnant',
                              #ip_restrictions=[{'Pregnancy': 'NotPregnant'}],
                              target_sex="Female", triggers=['GaveBirth'],daily_prob = 1, revert_in_days = -1, blackout=True)
    return camp
```

```
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
```

Then later on in the script (after I use the SimulationBuilder() ) I added the following event recorder

```
add_event_recorder(task, event_list=event_list,
                        start_day=1, end_day=serialize_years*365,
                        min_age_years=0,
                        max_age_years=100,
                        ips_to_record=['Pregnancy'],
                        #must_have_ip_key_value = 'Pregnancy:IsPregnant',
                        property_change_ip_to_record="Pregnancy"
                        )
```

