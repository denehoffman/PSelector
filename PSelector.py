import uproot
import ROOT as root
import numpy as np
import argparse
import re
from particle import Particle, ParticleNotFound, InvalidParticle

def get_particle_map(path):
    f = root.TFile(path)
    tree = f.Get(f.GetListOfKeys()[0].GetName())
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
    return output_sorted

def write_header(particle_map, basename="default"):
    header_text = f"""#ifndef DSelector_{basename}_h
#define DSelector_{basename}_h

#include <iostream>

#include "DSelector/DSelector.h"
#include "DSelector/DHistogramActions.h"
#include "DSelector/DCutActions.h

#include "TH1I.h"
#include "TH2I.h"

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
                header_text += f"        DNeutralTrackHypothesis* d{particle.get('name')}Wrapper;\n"
        header_text += "\n"
    
    # add histograms
    header_text += """        // DEFINE YOUR HISTOGRAMS HERE
        // EXAMPLES:
        TH1I* dHist_MissingMassSquared;
        TH1I* dHist_BeamEnergy;

"""
    header_text += f"""   ClassDef(DSelector_{basename}, 0);
}};

void DSelector_{basename}::Get_ComboWrappers(void) {{
"""
    for step_index, step_contents in enumerate(particle_map):
        header_text += f"        // Step {step_index}\n"
        header_text += f"        dStep{step_index}Wrapper = dComboWrapper->Get_ParticleComboStep({step_index});\n"
        for particle in step_contents:
            if not particle.get("particle"):
                continue
            elif particle.get("name") == "ComboBeam":
                header_text += "        dComboBeamWrapper = static_cast<DBeamParticle*>(dStep{step_index}Wrapper->Get_InitialParticle());\n"
            elif particle.get("name").startswith("Target"):
                continue
            elif particle.get("name").startswith("Decaying"):
                if particle.get("index") < 0:
                    header_text += f"        d{particle.get('name')}Wrapper = dStep{step_index}Wrapper->Get_InitialParticle();\n"
            elif particle.get("name").startswith("Missing"):
                header_text += f"        d{particle.get('name')}Wrapper = dStep{step_index}Wrapper->Get_FinalParticle({particle.get('index')}));\n"
            elif particle.get("particle").charge != 0:
                header_text += f"        d{particle.get('name')}Wrapper = static_cast<DChargedTrackHypothesis*>(dStep{step_index}Wrapper->Get_FinalParticle({particle.get('index')}));\n"
            else:
                header_text += f"        d{particle.get('name')}Wrapper = static_cast<DNeutralTrackHypothesis*>(dStep{step_index}Wrapper->Get_FinalParticle({particle.get('index')}));\n"
        header_text += "\n"
    
    header_text += f"}}\n\n#endif // DSelector_{basename}_h"

    return header_text

def write_source(particle_map, basename="default"):
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
    # add analysis action stuff here if we want that
    # false/true is measured/kinfit
    source_text += f"""    dAnalysisActions.push_back(new DHistogramAction_ParticleID(dComboWrapper, false));
    dAnalysisActions.push_back(new DHistogramAction_PIDFOM(dComboWrapper));
    dAnalysisActions.push_back(new DHistogramAction_KinFitResults(dComboWrapper));
    dAnalysisActions.push_back(new DHistogramAction_BeamEnergy(dComboWrapper, false));
    dAnalysisActions.push_back(new DHistogramAction_ParticleComboKinematics(dComboWrapper, false));

    Initialize_Actions();

"""
    # add histograms
    source_text += """    // DEFINE HISTOGRAMS HERE
    // EXAMPLES:
    dHist_MissingMassSquared = new TH1I("MissingMassSquared", ";Missing Mass Squared (GeV/c^{2})^{2}", 600, -0.06, 0.06);
    dHist_BeamEnergy = new TH1I("BeamEnergy", ";Beam Energy (GeV)", 600, 0.0, 12.0);

"""
    # custom main tree stuff
    # custom flat tree stuff
    
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
    # uniqueness tracking
    source_text += f"""
    Reset_Actions_NewEvent();
    
    set<Int_t> locUsedSoFar_BeamEnergy;
    set<map<Particle_t, set<Int_t>>> locUsedSoFar_MissingMass;

"""
    # fill custom output branches
    # loop over combos
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

    # Get four-vectors
    for step_index, step_contents in enumerate(particle_map):
        source_text += f"        // Step {step_index}\n"
        for particle in step_contents:
            if not particle.get("particle"):
                continue
            elif particle.get("name") == "ComboBeam":
                source_text += "        TLorentzVector locBeamP4 = dComboBeamWrapper->Get_P4();\n" 
                source_text += "        TLorentzVector locBeamP4_Measured = dComboBeamWrapper->Get_P4_Measured();\n" 
                source_text += "        TLorentzVector locBeamP4 = dComboBeamWrapper->Get_P4();\n" 
                source_text += "        TLorentzVector locBeamX4_Measured = dComboBeamWrapper->Get_X4_Measured();\n" 
            elif particle.get("name").startswith("Target"):
                continue
            elif particle.get("name").startswith("Decaying"):
                if particle.get("index") < 0:
                    source_text += f"        TLorentzVector loc{particle.get('name')}P4 = d{particle.get('name')}Wrapper->Get_P4();\n"
                    source_text += f"        TLorentzVector loc{particle.get('name')}X4 = d{particle.get('name')}Wrapper->Get_X4();\n"
            elif particle.get("name").startswith("Missing"):
                source_text += f"        TLorentzVector loc{particle.get('name')}P4 = d{particle.get('name')}Wrapper->Get_P4();\n"
                source_text += f"        TLorentzVector loc{particle.get('name')}X4 = d{particle.get('name')}Wrapper->Get_X4();\n"
            else:
                source_text += f"        TLorentzVector loc{particle.get('name')}P4 = d{particle.get('name')}Wrapper->Get_P4();\n"
                source_text += f"        TLorentzVector loc{particle.get('name')}P4_Measured = d{particle.get('name')}Wrapper->Get_P4_Measured();\n"
                source_text += f"        TLorentzVector loc{particle.get('name')}X4 = d{particle.get('name')}Wrapper->Get_X4();\n"
                source_text += f"        TLorentzVector loc{particle.get('name')}X4_Measured = d{particle.get('name')}Wrapper->Get_X4_Measured();\n"
        source_text += "\n"

    # Accidental Weighting
    source_text += f"""
    Double_t locBunchPeriod = dAnalysisUtilities.Get_BeamBunchPeriod(Get_RunNumber());
    Double_t locDeltaT_RF = dAnalysisUtilities.Get_DeltaT_RF(Get_RunNumber(), locBeamX4_Measured, dComboWrapper);
    Int_t locRelBeamBucket = dAnalysisUtilities.Get_RelativeBeamBucket(Get_RunNumber(), locBeamX4_Measured, dComboWrapper);
    Int_t locNumOutOfTimeBunchesInTree = 4;
    Int_t locNumOutOfTimeBunchesToUse = locNumOutOfTimeBunchesInTree - 1;
    Double_t locAccidentalScalingFactor = dAnalysisUtilities.Get_AccidentalScalingFactor(Get_RunNumber(), locBeamP4.E(), dIsMC);
    Double_t locAccidentalScalingFactorError = dAnalysisUtilities.Get_AccidentalScalingFactorError(Get_RunNumber(), locBeamP4.E());
    Double_t locHistAccidWeightFactor = locRelBeamBucket == 0 ? 1 : -locAccidentalScalingFactor / (2 * locNumOutOfTimeBunchesToUse);
    if abs(locRelBeamBucket) == 1 {{
        dComboWrapper->Set_IsComboCut(true);
        continue;
    }}

"""
    # Do Cuts
    
    # Missing Mass Squared Calculation
    source_text += "TLorentzVector locMissingP4_Measured = locBeamP4_Measured + dTargetP4;\n"
    source_text += "locMissingP4_Measured -= "
    isFirstFlag = True
    for step_index, step_contents in enumerate(particle_map):
        for particle in step_contents:
            if not particle.get("particle"):
                continue
            elif particle.get("name") == "ComboBeam":
                continue
            elif particle.get("name").startswith("Target"):
                continue
            elif particle.get("name").startswith("Decaying"):
                continue
            elif particle.get("name").startswith("Missing"):
                continue
            else:
                if not isFirstFlag:
                    source_text += " + "
                isFirstFlag = False
                source_text += f"loc{particle.get('name')}P4_Measured"
        source_text += ";\n"
        source_text += "double locMissingMassSquared = locMissingP4_Measured.M2();\n"

    # Execute Analysis Actions
    source_text += f"""
        if(!Execute_Actions()) {{
            continue;
        }}
"""
    # Fill custom output branches

    # Fill Histograms
    source_text += """
        if(locUsedSoFar_BeamEnergy.find(locBeamID) == locUsedSoFar_BeamEnergy.end()) {
            dHist_BeamEnergy->Fill(locBeamP4.E());
            
            locUsedSoFar_BeamEnergy.insert(locBeamID);
        }
        map<Particle_t, set<Int_t>> locUsedThisCombo_MissingMass;
        """
    for step_index, step_contents in enumerate(particle_map):
        for particle in step_contents:
            if not particle.get("particle"):
                continue
            elif particle.get("name") == "ComboBeam":
                source_text += "        locUsedThisCombo_MissingMass[Unknown].insert(locBeamID);\n"
            elif particle.get("name").startswith("Target"):
                continue
            elif particle.get("name").startswith("Decaying"):
                continue
            elif particle.get("name").startswith("Missing"):
                continue
            elif particle.get("particle").charge != 0:
                source_text += f"        locUsedThisCombo_MissingMass[EnumString(PDGtoPType({particle.get('pid')}))].insert(loc{particle.get('name')}TrackID);\n"
            else:
                source_text += f"        locUsedThisCombo_MissingMass[EnumString(PDGtoPType({particle.get('pid')}))].insert(loc{particle.get('name')}NeutralID);\n"
        source_text += "\n"
    source_text += """
    if(locUsedSoFar_MissingMass.find(locUsedThisCombo_MissingMass) == locUsedSoFar_MissingMass.end()) {
        dHist_MissingMassSquared->Fill(locMissingMassSquared, locHistAccidWeightFactor);
        }
    }

    Fill_NumCombosSurvivedHists();
"""
    
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

if __name__ == "__main__":
    print(write_source(get_particle_map("demo.root")))
