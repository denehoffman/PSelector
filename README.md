# PSelector
A pythonic version of the GlueX DSelector

## Usage
```
$ MakePSelector --help
usage: MakePSelector [-h] [-n NAME] [-f] [--cut-accidentals] config
positional arguments:
  config                path to configuration file

optional arguments:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  (optional) name for selector class and files, i.e.
                        "DSelector_<name>.C/.h". Defaults to tree name without
                        "_Tree"
  -f, --force           force overwriting existing output files
  --cut-accidentals     cut accidentals rather than subtract them
```

### More Detailed Usage

`MakePSelector` takes a configuration file as its only required argument. The details of this configuration file are listed below. The optional arguments are:
- `--name` This allows you to change the output name of the DSelector files. For instance, we could use `MakePSelector config.json --name demo` to create files with the names `DSelector_demo.C` and `DSelector_demo.h`. If no arguemnt is used, this will default to the tree name minus the `_Tree` suffix, so a tree named `ksks__B4_Tree` would generate a DSelector named `DSelector_ksks__B4.C`.
- `--force` This argument exists to prevent accidental overwriting of existing DSelectors. Using it will allow the `MakePSelector` script to overwrite a DSelector with the same name, while excluding it will throw an error and not write anything.
- `--cut-accidentals` switches the treatment of accidentals from the default (subraction by weighting them as -1/n where n is the number of out-of-time peaks) to selecting only the central beam peak.

## Writing a Configuration File
Configuration files for `MakePSelector` are written in JSON (JavaScript Object Notation). This format was chosen because it is human-parsable and the `json` package is part of the standard `python3` library (unlike `yaml`). The [JSON homepage](https://www.json.org/) has a good explanation of how the format works.
### Minimum Configuration:
```json
{
    "source": "path/to/source.root",
    "vectors": {},
    "boosts": {},
    "variables": {},
    "cuts": {},
    "weights": {},
    "uniqueness": {},
    "histograms": {}
}
```
#### source
This field contains the (absolute) path to the template `ROOT` file containing a GlueX-formatted data `TTree`. `MakeDSelector` also inputs such a template file, but `MakePSelector` is intended to be run each time the configuration file is changed, so it would be an unneccessary hassle to have to type in the path every time.

#### vectors
This field contains a dictionary containing recipes to create `TLorentzVectors` which can be boosted along with the 4-momenta/4-positions which are created by default for each particle. For instance,
```json
{
    "vectors": {
        "locDecayingKShort1P4_Measured": "locPiMinus1P4_Measured + locPiPlus1P4_Measured",
        "locDecayingKShort2P4_Measured": "locPiMinus2P4_Measured + locPiPlus2P4_Measured",
        "locMesonHypoP4_Measured": "locDecayingKShort1P4_Measured + locDecayingKShort2P4_Measured"
    }
}
```
creates two new `TLorentzVectors` from the sums of others.

#### boosts
This field describes boost frames and their relation to one another. Boosts can be nested to refer to boosts which happen in a specific order (boost order does not commute!). Example:
```json
{
    "boosts": {
        "COM": {
            "boostvector": "locBeamP4 + dTargetP4",
            "boosts": {
                "MESON": {
                    "boostvector": "locMesonHypoP4_Measured"
                }
            }
        }
    }
}
```
Here, `COM` is the name given to the center-of-momentum frame. It is also the suffix added to `TLorentzVector`s which are boosted to this frame. For instance, a vector called `locPiMinus1P4_Measured` will become `locPiMinus1P4_Measured_COM`. Each named boost contains at least one field called `boostvector` which describes the 4-vector for the boost. In this example, we are adding the beam momentum to the target momentum to get the center of momentum. We can also nest `boost` fields inside each other. Here, the `MESON` boost follows the `COM` boost. Be sure to use `boostvector` names which *do not* include boosted tags, as these will be added automatically (there is no need to use `locMesonHypoP4_Measured_COM` to describe the boost vector here, this will be made implicit in the DSelector code).

One can use any of the default `TLorentzVector`s as well as any vector defined in the `vectors` field for a boost vector.

#### variables
This field contains any raw code to add directly to the DSelector. Unfortunately, one of the limitations of the `JSON` format is that newlines are not interpreted in strings (although if you wish to write `\n` after every line, you are free to do so). Instead, the code is specified through a list of strings:
```json
{
    "variables": {
        "confidence_level": ["Double_t locConfidenceLevel, loclog10ConfidenceLevel;",
            "locConfidenceLevel = dComboWrapper->Get_ConfidenceLevel_KinFit(\"\");",
            "loclog10ConfidenceLevel = log10(locConfidenceLevel);"],
        "MMS": ["TLorentzVector locMissingP4 = locBeamP4_Measured + dTargetP4 - locProtonP4_Measured - locPiMinus1P4_Measured - locPiPlus1P4_Measured - locPiMinus2P4_Measured - locPiPlus2P4_Measured;"],
    }
}
```
Each "variable" should be given a name (this makes the coding easier but also helps with the organization and readability of the final C code). All of these code blocks are inserted verbatim into the DSelector combo loop and can use any vectors (and their boosted forms) declared in the `vectors` field. The code sample here describes how to get variables like the confidence level and missing mass squared.

#### cuts
Perhaps the most important field, this allows for specification and toggling of various data selections. Each cut has an `enabled` field (true/false) and a `condition` field (a boolean which must be met for the combo to be cut). All cut language is exclusive by default, meaning that if the condition is true, the combo will be cut, and if it is false, it will be kept (in contrast to language where a selection is made, i.e. a condition being true results in the combo being selected or kept). Here is an example of a group of cuts which remove different portions of the data based on confidence level:
```json
{
    "cuts": {
        "confidence_level": {
            "enabled": false,
            "condition": "locConfidenceLevel < 1e-4"
        },
        "select_hc": {
            "enabled": true,
            "condition": "locConfidenceLevel < 1e-9"
        },
        "select_lc": {
            "enabled": false,
            "condition": "locConfidenceLevel > 1e-10 || locConfidenceLevel < 1e-20"
        }
    }
}
```
Here, only one cut is enabled, so the others will not enter the final DSelector code at all. The enabled cut removes all combos with `locConfidenceLevel` less than `1e-9` (thus selecting high-confidence events).

#### weights
The `weights` field can be used to assign different weights based on conditional statements (such as a sideband subtraction).
```json
{
    "some_weight": {
        "enabled": true,
        "weight": "0.3",
        "condition": "true"
    },
    "another_weight": {
        "enabled": true,
        "weight": "my_factor",
        "condition": "locConfidenceLevel > 1e-9",
        "code": ["Double_t my_factor = 0.4;",
                 "if(locConfidenceLevel < 1e-4) {",
                 "    my_factor = 0.2;"
                 "}"]
    }
}
```
This code describes two weights, one of which gives all events a weight of `0.3` and the other of which gives a weight which depends on several conditions: the weight is only applied if the confidence level is greater than `1e-9` and if this is true it checks whether or not it is less than `1e-4` and assigns different weights accordingly. Anything written in the `code` field here is inserted immediately before the weight is applied and can access code from any of the prior fields like `variables` and `vectors`.

#### uniqueness
This field keeps track of the uniqueness of the combos being plotted in various histograms. You may define multiple fields here, but you must define at least some uniqueness tracking for each histogram you want to create:
```json
{
    "uniqueness": {
        "all": {"particles": "all", "histograms": "all"},
        "beamtracking": {"particles": ["Beam"], "histograms": "all"}
    },
}
```
the `all` parameter has special use here. While in the second case, the suffix `_beamtracking` will be added to all histograms using this uniqueness tracking option, no such suffix will be applied to the `all` tracker. Inside each uniqueness tracker there are two fields, `particles` and `histograms`. `particles` can either be set to `all` to uniquely track all of the particles present in the final state (one histogram entry per each unique combination of all final-state particles) or a list of particles. The particle names can be found near the top of the DSelector and typically have names like `loc<name>ID` or `loc<name>TrackID` (like `locBeamID` or `locPiPlus2TrackID`). The `histograms` field can also be set to `all` to include all histograms in this configuration file or as a list of histogram names (specified in the next and final field).

#### histograms
The `histograms` field contains the information needed to create each histogram. There are several use cases, but the simplest histogram can be generated as:
```json
{
    "histograms": {
        "Log10KinFitCL": {
            "x": "loclog10ConfidenceLevel",
            "xrange": [-20, 0],
            "xbins": 200
        }
    }
}
```
The `x` parameter describes the variable to plot (this can also include any inline C code, like `locMissingP4.M2()`, for example). `xrange` describes the minimum and maximum bin edges, and `xbins` tells the program how many bins to use in the histogram. Additionally, the user may supply fields like `xlabel`, `ylabel`, and `title` to label the histogram correspondingly (these take a string which may include the proper ROOT-to-LaTeX formatters).

To make a 2D histogram, we just include `y`, `yrange`, and `ybins` fields:
```json
{
    "histograms": {
        "vanHove": {
            "x": "locVanHoveX",
            "xrange": [-3.0, 3.0],
            "xbins": 100,
            "xlabel": "X",
            "y": "locVanHoveY",
            "yrange": [-3.0, 3.0],
            "ybins": 100,
            "ylabel": "Y"
        }
    }
}
```
There is an alternative way to create 2D histograms if two 1D histograms are already defined. We can use the `xhist` and `yhist` fields to copy information from existing histograms (this can also be used with just `xhist` to create copies of 1D histograms). Changing any of the fields will overwrite the existing data copied over from the old histogram into the new one. For example:
```json
{
    "histograms": {
        "KShort1_InvMass": {
            "x": "locDecayingKShort1P4_Measured.M()",
            "xrange": [0.3, 0.7],
            "xbins": 100,
            "xlabel": "K_{S,1}^{0} Invariant Mass (GeV/c^{2})"
        },
        "KShort2_InvMass": {
            "xhist": "KShort1_InvMass",
            "x": "locDecayingKShort2P4_Measured.M()",
            "xlabel": "K_{S,2}^{0} Invariant Mass (GeV/c^{2})"
        },
        "Ks1vsKs2": {
            "xhist": "KShort1_InvMass",
            "yhist": "KShort2_InvMass"
        },
    }
}
```
creates three histograms. The first has all fields explicitly defined. The `KShort2_InvMass` histogram inherets `xrange` and `xbins` from `KShort1_InvMass` but changes the `x` variable as well as the `xlabel`. Finally, `Ks1vsKs2` is a 2D histogram showing the correlation of the kaon masses.

One final field exists to allow for some very specific use cases: `destination` can be used to double-fill a histogram:
```json
{
    "histograms": {
        "HXPhi": {
            "x": "locKShort1HX.Phi()",
            "xrange": ["-TMath::Pi()", "TMath::Pi()"],
            "xbins": 50,
            "xlabel": "#phi_{HX}"
        },
        "HXPhi2": {
            "destination": "HXPhi",
            "x": "locKShort2HX.Phi()"
        }
    }
}
```
Here, suppose we had two identical kaons and we wanted to plot an angle in the kaon + kaon center-of-momentum frame. The kaons are back-to-back in this frame, so we could plot both of them in the same histogram by specifying that the `destination` of the second histogram is the first histogram. Using the `destination` field will cause the program to ignore everything except `x` and `y` fields for that particular histogram.

## Installing
The `MakePSelector` program can be installed by cloning this repository and running
```
pip3 install .
```
in the root project directory. Due to the specificity of this program, I do not see the need to publish it to PyPI. When installed in this way it will make the `MakePSelector` script available for execution from any directory. Note that `MakePSelector` is written for `python3`. I will not write a version for `python2`, as it has been [deprecated/sunset since 2020 and is no longer supported](https://www.python.org/doc/sunset-python-2/). If you are still using `python2` for analysis, 99% of your code can be updated by simply converting your `print` statements.

Planned features will be added as issues arise. I can imagine there will be lots of very specific features or shorthands that might be appreciated. For example, we almost always want to calculate things like the Mandelstam t or the missing mass squared, so in the future I might implement a shorthand to do this automatically.
