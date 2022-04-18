#!/usr/bin/env python3
from Elements import Uniqueness, Histogram, Boost, Cut, Weight
import ROOT as root
import json
import argparse
from pprint import pprint
from pathlib import Path
import re
from particle import Particle


############# WRITE HEADER ###############
def get_header(treename, particle_map, config, basename="default"):
    header_text = f"""#ifndef DSelector_{basename}_h
#define DSelector_{basename}_h

#include <iostream>

#include "DSelector/DSelector.h"
#include "DSelector/DHistogramActions.h"
#include "DSelector/DCutActions.h"

#include "TH1D.h"
#include "TH2D.h"

class DSelector_{basename} : public DSelector {{

    public:

        DSelector_{basename}(TTree* locTree = NULL) : DSelector(locTree){{}}
        virtual ~DSelector_{basename}(){{}}

        void Init(TTree *tree);
        Bool_t Process(Long64_t entry);

    private:

        void Get_ComboWrappers(void);
        void Finalize(void);

        // BEAM POLARIZATION INFORMATION
        UInt_t dPreviousRunNumber;
        bool dIsPolarizedFlag; //else is AMO
        bool dIsPARAFlag; //else is PERP or AMO

        bool dIsMC;

        // CREATE REACTION-SPECIFIC PARTICLE ARRAYS

"""
    for step_index, step_contents in enumerate(particle_map):
        header_text += f"        // Step {step_index}\n"
        header_text += f"        DParticleComboStep* dStep{step_index}Wrapper;\n"
        for particle in step_contents:
            if not particle.get("particle"):
                continue
            elif particle.get("name") == "ComboBeam":
                header_text += "        DBeamParticle* dComboBeamWrapper;\n"
            elif particle.get("name").startswith("Target"):
                continue
            elif particle.get("name").startswith("Decaying"):
                if particle.get("index") < 0:
                    header_text += f"        DKinematicData* d{particle.get('name')}Wrapper;\n"
            elif particle.get("name").startswith("Missing"):
                header_text += f"        DKinematicData* d{particle.get('name')}Wrapper;\n"
            elif particle.get("particle").charge != 0:
                header_text += f"        DChargedTrackHypothesis* d{particle.get('name')}Wrapper;\n"
            else:
                header_text += f"        DNeutralParticleHypothesis* d{particle.get('name')}Wrapper;\n"
        header_text += "\n"
    header_text += "        // DEFINE YOUR HISTOGRAMS HERE\n"
    # HISTOGRAM INITIALIZATIONS
    for uniqueness in [Uniqueness(name, config, particle_map) for name in config["uniqueness"].keys()]:
        header_text += uniqueness.header_hists()
    # END HISTOGRAM INITIALIZATIONS
    header_text += f"""\n    ClassDef(DSelector_{basename}, 0);
}};

void DSelector_{basename}::Get_ComboWrappers(void) {{
"""
    for step_index, step_contents in enumerate(particle_map):
        header_text += f"    // Step {step_index}\n"
        header_text += f"    dStep{step_index}Wrapper = dComboWrapper->Get_ParticleComboStep({step_index});\n"
        for particle in step_contents:
            if not particle.get("particle"):
                continue
            elif particle.get("name") == "ComboBeam":
                header_text += f"    dComboBeamWrapper = static_cast<DBeamParticle*>(dStep{step_index}Wrapper->Get_InitialParticle());\n"
            elif particle.get("name").startswith("Target"):
                continue
            elif particle.get("name").startswith("Decaying"):
                if particle.get("index") < 0:
                    header_text += f"    d{particle.get('name')}Wrapper = dStep{step_index}Wrapper->Get_InitialParticle();\n"
            elif particle.get("name").startswith("Missing"):
                header_text += f"    d{particle.get('name')}Wrapper = dStep{step_index}Wrapper->Get_FinalParticle({particle.get('index')}));\n"
            elif particle.get("particle").charge != 0:
                header_text += f"    d{particle.get('name')}Wrapper = static_cast<DChargedTrackHypothesis*>(dStep{step_index}Wrapper->Get_FinalParticle({particle.get('index')}));\n"
            else:
                header_text += f"    d{particle.get('name')}Wrapper = static_cast<DNeutralParticleHypothesis*>(dStep{step_index}Wrapper->Get_FinalParticle({particle.get('index')}));\n"
        header_text += "\n"

    header_text += f"}}\n\n#endif // DSelector_{basename}_h"
    return header_text

def get_source(treename, particle_map, config, basename="default", cut_accidentals=False):
    source_text = f"""#include "DSelector_{basename}.h"

void DSelector_{basename}::Init(TTree *locTree) {{

    dOutputFileName = "hist_{basename}.root";
    dOutputTreeFileName = "tree_{basename}.root";
    dFlatTreeFileName = "";
    dFlatTreeName = "";

    bool locInitializedPriorFlag = dInitializedFlag;
    DSelector::Init(locTree);
    if(locInitializedPriorFlag) {{
        return;
    }}
    Get_ComboWrappers();
    dPreviousRunNumber = 0;
"""
    ###################################### add analysis action stuff here if we want that
    # false/true is measured/kinfit
    source_text += f"""    dAnalysisActions.push_back(new DHistogramAction_ParticleID(dComboWrapper, false));
    dAnalysisActions.push_back(new DHistogramAction_PIDFOM(dComboWrapper));
    dAnalysisActions.push_back(new DHistogramAction_KinFitResults(dComboWrapper));
    dAnalysisActions.push_back(new DHistogramAction_BeamEnergy(dComboWrapper, false));
    dAnalysisActions.push_back(new DHistogramAction_ParticleComboKinematics(dComboWrapper, false));

    Initialize_Actions();

"""
    ###################################### add histograms
    source_text += "    // DEFINE HISTOGRAMS HERE\n"
    for uniqueness in [Uniqueness(name, config, particle_map) for name in config["uniqueness"].keys()]:
        source_text += uniqueness.init_hists()
    
    source_text += "\n"

    ###################################### custom main tree stuff
    ###################################### custom flat tree stuff

    source_text += f"""
    dIsMC = (dTreeInterface->Get_Branch("MCWeight") != NULL);

}}

Bool_t DSelector_{basename}::Process(Long64_t locEntry) {{

    DSelector::Process(locEntry);
    //cout << "RUN " Get_RunNumber() << ", EVENT " << Get_EventNumber() << endl;
    //TLorentzVector locProductionX4 = Get_X4_Production();

    // If the run number changes, use RCDB to get polarization info:
    UInt_t locRunNumber = Get_RunNumber();
    if(locRunNumber != dPreviousRunNumber) {{
        dIsPolarizedFlag = dAnalysisUtilities.Get_IsPolarizedBeam(locRunNumber, dIsPARAFlag);
        dPreviousRunNumber = locRunNumber;
    }}

"""
    source_text += f"""
    Reset_Actions_NewEvent();
"""
    ###################################### uniqueness tracking
    for uniqueness in [Uniqueness(name, config, particle_map) for name in config["uniqueness"].keys()]:
        source_text += uniqueness.init_string()

    ###################################### fill custom output branches
    ###################################### loop over combos
    source_text += f"""

    for(UInt_t loc_i = 0; loc_i < Get_NumCombos(); ++loc_i) {{

        dComboWrapper->Set_ComboIndex(loc_i);
        if(dComboWrapper->Get_IsComboCut()) {{
            continue;
        }}

        // GET PARTICLE INDICES FOR UNIQUENESS TRACKING
"""
    for step_index, step_contents in enumerate(particle_map):
        source_text += f"        // Step {step_index}\n"
        for particle in step_contents:
            if not particle.get("particle"):
                continue
            elif particle.get("name") == "ComboBeam":
                source_text += "        Int_t locBeamID = dComboBeamWrapper->Get_BeamID();\n" 
            elif particle.get("name").startswith("Target"):
                continue
            elif particle.get("name").startswith("Decaying"):
                continue
            elif particle.get("name").startswith("Missing"):
                continue
            elif particle.get("particle").charge != 0:
                source_text += f"        Int_t loc{particle.get('name')}TrackID = d{particle.get('name')}Wrapper->Get_TrackID();\n" 
            else:
                source_text += f"        Int_t loc{particle.get('name')}NeutralID = d{particle.get('name')}Wrapper->Get_NeutralID();\n" 
        source_text += "\n"

    ###################################### Get four-vectors
    vector_names = []
    for step_index, step_contents in enumerate(particle_map):
        source_text += f"        // Step {step_index}\n"
        for particle in step_contents:
            if not particle.get("particle"):
                continue
            elif particle.get("name") == "ComboBeam":
                source_text += "        TLorentzVector locBeamP4 = dComboBeamWrapper->Get_P4();\n" 
                source_text += "        TLorentzVector locBeamP4_Measured = dComboBeamWrapper->Get_P4_Measured();\n" 
                source_text += "        TLorentzVector locBeamX4 = dComboBeamWrapper->Get_X4();\n" 
                source_text += "        TLorentzVector locBeamX4_Measured = dComboBeamWrapper->Get_X4_Measured();\n" 
                vector_names += ["locBeamP4", "locBeamP4_Measured"]
            elif particle.get("name").startswith("Target"):
                continue
            elif particle.get("name").startswith("Decaying"):
                if particle.get("index") < 0:
                    source_text += f"        TLorentzVector loc{particle.get('name')}P4 = d{particle.get('name')}Wrapper->Get_P4();\n"
                    source_text += f"        TLorentzVector loc{particle.get('name')}X4 = d{particle.get('name')}Wrapper->Get_X4();\n"
                    vector_names.append(f"loc{particle.get('name')}P4")
            elif particle.get("name").startswith("Missing"):
                source_text += f"        TLorentzVector loc{particle.get('name')}P4 = d{particle.get('name')}Wrapper->Get_P4();\n"
                source_text += f"        TLorentzVector loc{particle.get('name')}X4 = d{particle.get('name')}Wrapper->Get_X4();\n"
                vector_names.append(f"loc{particle.get('name')}P4")
            else:
                source_text += f"        TLorentzVector loc{particle.get('name')}P4 = d{particle.get('name')}Wrapper->Get_P4();\n"
                source_text += f"        TLorentzVector loc{particle.get('name')}P4_Measured = d{particle.get('name')}Wrapper->Get_P4_Measured();\n"
                source_text += f"        TLorentzVector loc{particle.get('name')}X4 = d{particle.get('name')}Wrapper->Get_X4();\n"
                source_text += f"        TLorentzVector loc{particle.get('name')}X4_Measured = d{particle.get('name')}Wrapper->Get_X4_Measured();\n"
                vector_names += [f"loc{particle.get('name')}P4", f"loc{particle.get('name')}P4_Measured"]
        source_text += "\n"
    # Define some particle-related vectors here
    for key, val in config["vectors"].items():
        source_text += f"        TLorentzVector {key} = {val};\n"
        vector_names.append(key)
    source_text += "\n"
    # Boosts
    for boost in [Boost(name, config, vector_names) for name in config["boosts"].keys()]:
        source_text += boost.boost_string()
    

    ###################################### Old Accidental Weighting
    n_out_of_time = -1
    num_from_treename = re.search("_B(\d+)", treename).group(1)
    if num_from_treename:
        n_out_of_time = int(num_from_treename)
    source_text += """
        // Accidentals:
        Double_t locDeltaT_RF = dAnalysisUtilities.Get_DeltaT_RF(Get_RunNumber(), locBeamX4_Measured, dComboWrapper);
"""
    if cut_accidentals:
        source_text += """
        // Cut Accidentals
        if(fabs(locDeltaT_RF) > 0.5 * 4.008) {
            dComboWrapper->Set_IsComboCut(true);
            continue;
        }
        Double_t locWeight = 1.0;
"""
    else:
        source_text += f"""
        // Subtract Accidentals
        Double_t locHistAccidWeightFactor = (fabs(locDeltaT_RF) > 0.5 * 4.008) ? -1/{2 * n_out_of_time} : 1;
        Double_t locWeight = locHistAccidWeightFactor;
"""
    # Define boost-related vectors here?
    for varname, varcode in config["variables"].items():
        source_text += "\n"
        source_text += f"        // {varname}\n"
        for line in varcode:
            source_text += "        " + line + "\n"

    # Execute Analysis Actions
    source_text += """
        if(!Execute_Actions()) {
            continue;
        }
"""

    # Cuts
    for cut in [Cut(name, config) for name in config["cuts"].keys()]:
        source_text += f"\n        // CUT: {cut.name}\n"
        source_text += cut.cut_string()
    source_text += "\n\n"

    # Weights
    for weight in [Weight(name, config) for name in config["weights"].keys()]:
        source_text += f"\n        // WEIGHT: {weight.name}\n"
        source_text += weight.weight_string()
    source_text += "\n\n"

    # Fill Histograms
    for uniqueness in [Uniqueness(name, config, particle_map) for name in config["uniqueness"].keys()]:
        source_text += uniqueness.fill_string()
    # End Combo Loop
    source_text += "    } // End of Combo Loop\n\n    Fill_NumCombosSurvivedHists();\n"

    # Fill output tree
    source_text += """
    Bool_t locIsEventCut = true;
    for(UInt_t loc_i = 0; loc_i < Get_NumCombos(); ++loc_i) {
        dComboWrapper->Set_ComboIndex(loc_i);
        if(dComboWrapper->Get_IsComboCut()) {
            continue;
        }
        locIsEventCut = false; // At least one combo succeeded
        break;
    }
    if(!locIsEventCut && dOutputTreeFileName != "") {
        Fill_OutputTree();
    }
"""
    source_text += f"""
    return kTRUE;
}}

void DSelector_{basename}::Finalize(void) {{
    DSelector::Finalize();
}}"""
    return source_text



def get_particle_map(path):
    f = root.TFile(path)
    treename = str(f.GetListOfKeys()[0].GetName())
    tree = f.Get(treename)
    branches = [str(key.GetName()) for key in tree.GetListOfBranches()]
    userinfo = tree.GetUserInfo()
    name_to_pid = userinfo.FindObject("NameToPIDMap")
    pos_to_name = userinfo.FindObject("PositionToNameMap")
    output = []
    for key in pos_to_name:
        step_index = int(str(key.GetName()).split("_")[0])
        particle_index = int(str(key.GetName()).split("_")[1])
        particle_name = str(pos_to_name.GetValue(key).GetName())
        particle_pid = int(str(name_to_pid.GetValue(particle_name)))
        try:
            particle = Particle.from_pdgid(particle_pid)
        except ParticleNotFound:
            particle = None
        except InvalidParticle:
            particle = None
        if step_index >= len(output):
            output.append([{"index": particle_index,
                            "name": particle_name,
                            "pid": particle_pid,
                            "particle": particle}])
        else:
            output[step_index].append({"index": particle_index,
                                       "name": particle_name,
                                       "pid": particle_pid,
                                       "particle": particle})
    output_sorted = []
    for step_list in output:
        output_sorted.append(sorted(step_list, key=lambda d: d.get("index")))
    return treename, branches, output_sorted

def main():
    parser_desc = """
#############################################################\n
# Pythonic MakeDSelector                                    #\n
# Author: Nathaniel D. Hoffman - Carnegie Mellon University #\n
# Created: 3 Nov 2021                                       #\n
#                                                           #\n
# Use this program as a substitute for MakeDSelector, or    #\n
# optionally include a configuration file to handle all     #\n
# selections, histograms, analysis actions, and outputs.    #\n
#############################################################\n
"""
    parser = argparse.ArgumentParser(description=parser_desc)
    parser.add_argument("config", help="path to configuration file")
    parser.add_argument("-n", "--name", help="(optional) name for selector class and files, i.e. \"DSelector_<name>.C/.h\". Defaults to tree name without \"_Tree\"")
    parser.add_argument("-f", "--force", action="store_true", help="force overwriting existing output files")
    parser.add_argument("--cut-accidentals", action="store_true", help="cut accidentals rather than subtract them")
    args = parser.parse_args()
    if args.config:
        config_path = Path(args.config).resolve()
        assert config_path.exists(), f"Could not access {str(config_path)}!"
    else:
        config_path = None
    config = {"uniqueness": {}, "histograms": {}}
    if config_path:
        print(f"Using {str(config_path)} to supplement DSelector generation")
        with open(config_path, 'r') as stream:
            config = json.load(stream)

    input_path = Path(config["source"]).resolve()
    assert input_path.exists(), f"Could not access {str(input_path)}!"
    treename, branches, particle_map = get_particle_map(str(input_path))
    if args.name:
        basename = args.name
    else:
        basename = treename.replace("_Tree", "")
    output_source_path = Path(".") / f"DSelector_{basename}.C"
    output_header_path = Path(".") / f"DSelector_{basename}.h"
    if not args.force:
        assert not output_source_path.exists(), f"{str(output_source_path)} already exists in this directory, run with '--force' to overwrite this file!"
        assert not output_header_path.exists(), f"{str(output_header_path)} already exists in this directory, run with '--force' to overwrite this file!"

    print(f"Generating {str(output_source_path)} and {str(output_header_path)}...")
    with open(output_source_path, 'w') as source, open(output_header_path, 'w') as header:
        source.write(get_source(treename, particle_map, config, basename, cut_accidentals=args.cut_accidentals))
        header.write(get_header(treename, particle_map, config, basename))

if __name__ == "__main__":
    main()
