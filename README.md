
# PSelector
A pythonic version of the GlueX DSelector

## Background
The [MakeDSelector](https://github.com/JeffersonLab/gluex_root_analysis/blob/master/programs/MakeDSelector/MakeDSelector.cc) program was designed to generate a template based on the reaction topology of an input `ROOT` file. However, that is as far as its usefulness extends. Additionally, it adds a lot of commented-out optional code which is helpful when learning about analysis actions and the general workings of the `DSelector`. While this is useful to a new coder (every new GlueX worker should read through the default file created by this program to learn how it works), it makes mature `DSelector`s more difficult to read. The onus of deleting the cluttering comments and example code is put on the user, and [some of these default actions](https://github.com/JeffersonLab/gluex_root_analysis/blob/e80344f7700030251081531a462d66d56df28110/programs/MakeDSelector/MakeDSelector.cc#L257-L306) can be rather confusing for new users who see variables created with no internal use.

These were some of my initial reasons for creating `MakePSelector`. This project was inspired by [Hao Li](https://github.com/lihaoahil)'s work on an alternative `MakeDSelector` program which takes an optional configuration file. In that case, the code was all written on top of the given `MakeDSelector` program, so it still kept the comments and boilerplate code mentioned above, but it allowed users to specify histograms in a single line of code, insert blocks of raw text as code in the final `DSelector`, and had the neat option to allow the user to generate 2D histograms out of two existing 1D histograms with a simple syntax. Hao's code also created a chained syntax for generating boosted versions of 4-vectors, similar to this program, as well as some syntax which handled uniqueness tracking.

I have taken his work a step further by gauging which typical actions a user might take happen to have the same default code. For example, we might want to introduce a weight for each combo which is propagated into histograms. The syntax for creating cuts/selections rarely diverges from a simple if-statement. Histograms and boosts are also fairly standard in their implementation. There are additionally some fields which can be added to the configuration file to simplify workflows.

For example, the default `MakeDSelector` requires a GlueX analysis `ROOT` tree as input. It uses this `TFile` to grab a map of the reaction topology from which it generates track wrappers and reaction steps. Entering the path for this file can be tedious depending on your file hierarchy, and it typically doesn't change at all between `DSelector`s. Without a configuration file, it's necessary to manually point the program to this file, but `MakePSelector` grabs the path from the `source` field, which means the user doesn't have to remember the path every time they make a change to the configuration. Similarly, the `MakeDSelector` program requires the name of the `TTree` inside the analysis tree. It is standard practice that `ROOT` analysis files only contain a single `TTree`, so selecting that tree is made the standard behavior of `MakePSelector`.

Additional features include a unified syntax for making cuts, ways to specify additional 4-vectors (which can be included in boosts), blocks for adding raw C code to the `DSelector` through the configuration file, and methods which generate folders for each uniqueness tracking group. The latter can also be extended to create folders which contain sets of histograms with events which pass specified cuts. This allows the user to see the effect of each cut sequentially while still outputting a set of cuts.

The configuration file is designed to be able to handle any standard analysis action. Special bits of code which modify the typical flow of a `DSelector` must be manually added to the resulting `.C` and `.h` files. If there is a specific instance of this which you believe might be useful for other users, feel free to fork this repository and add it, or let me know what features you would like to see.

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
  --no-folders          don't generate folders for each uniqueness block (may
                        be faster but less organized)
  --cut-accidentals     cut accidentals rather than subtract them
```

### More Detailed Usage

`MakePSelector` takes a configuration file as its only required argument. The details of this configuration file are listed below. The optional arguments are:
- `--name` This allows you to change the output name of the DSelector files. For instance, we could use `MakePSelector config.json --name demo` to create files with the names `DSelector_demo.C` and `DSelector_demo.h`. If no arguemnt is used, this will default to the tree name minus the `_Tree` suffix, so a tree named `ksks__B4_Tree` would generate a DSelector named `DSelector_ksks__B4.C`.
- `--no-folders` disables the creation of subdirectories in the `ROOT` histogram output file. Use this if you want a flat histogram interface or for compatibility with other post-processing plotting tools which assume no directory structure. Otherwise, it is recommended to omit this flag to have more organized histograms.
- `--cut-accidentals` switches the treatment of accidentals from the default (subraction by weighting them as -1/n where n is the number of out-of-time peaks) to selecting only the central beam peak.

## Writing a Configuration File
Configuration files for `MakePSelector` are written in TOML (Tom's Obvious, Minimal Language). This project originally used JSON, but the most recent update uses TOML because of the ability to write comments and multiline strings.
### Minimum Configuration:
```toml
source = "path/to/source.root"
```
### Configuration Fields:
#### source
This field contains the (absolute) path to the template `ROOT` file containing a GlueX-formatted data `TTree`. `MakeDSelector` also inputs such a template file, but `MakePSelector` is intended to be run each time the configuration file is changed, so it would be an unneccessary hassle to have to type in the path every time.

#### name
The `name` field is optional and has the same behavior as the `--name` flag in the command-line interface. However, the `--name` flag will override this field if given.

#### vectors
This field contains a dictionary containing recipes to create `TLorentzVectors` which can be boosted along with the 4-momenta/4-positions which are created by default for each particle. For instance,
```toml
[vectors]
locMesonHypoP4 = "locDecayingKShort1P4 + locDecayingKShort2P4"
locSigmaHypo1P4 = "locDecayingKShort1P4 + locProtonP4"
locSigmaHypo2P4 = "locDecayingKShort2P4 + locProtonP4"
```
creates three new `TLorentzVectors` from the sums of others.

#### boosts
This field describes boost frames and their relation to one another. Boosts can be nested to refer to boosts which happen in a specific order (boost order does not commute!). Example:
```toml
[boosts.COM]
boostvector = "locBeamP4 + dTargetP4"

[boosts.COM.boosts.MESON]
boostvector = "locMesonHypoP4_Measured"
```
Here, `COM` is the name given to the center-of-momentum frame. It is also the suffix added to `TLorentzVector`s which are boosted to this frame. For instance, a vector called `locPiMinus1P4_Measured` will become `locPiMinus1P4_Measured_COM`. Each named boost contains at least one field called `boostvector` which describes the 4-vector for the boost. In this example, we are adding the beam momentum to the target momentum to get the center of momentum. We can also nest `boost` fields inside each other. Here, the `MESON` boost follows the `COM` boost. Be sure to use `boostvector` names which *do not* include boosted tags, as these will be added automatically (there is no need to use `locMesonHypoP4_Measured_COM` to describe the boost vector here, this will be made implicit in the DSelector code).

One can use any of the default `TLorentzVector`s as well as any vector defined in the `vectors` field for a boost vector.

#### variables
This field contains any raw code to add directly to the DSelector:
```toml
[variables]
confidence_level = """
Double_t locChiSqDOF, locConfidenceLevel, loclog10ConfidenceLevel;
locChiSqDOF = dComboWrapper->Get_ChiSq_KinFit("") / dComboWrapper->Get_NDF_KinFit("");
locConfidenceLevel = dComboWrapper->Get_ConfidenceLevel_KinFit("");
loclog10ConfidenceLevel = log10(locConfidenceLevel);
"""
MMS = """
TLorentzVector locMissingP4 = locBeamP4_Measured + dTargetP4 - locProtonP4_Measured - locPiMinus1P4_Measured - locPiPlus1P4_Measured - locPiMinus2P4_Measured - locPiPlus2P4_Measured;
"""
```
Each "variable" should be given a name (this makes the coding easier but also helps with the organization and readability of the final C code). All of these code blocks are inserted verbatim into the DSelector combo loop and can use any vectors (and their boosted forms) declared in the `vectors` field. The code sample here describes how to get variables like the confidence level and missing mass squared. Note that they are written in the same order as the configuration file, so the order will matter if you define a variable in one block and use it in another.

#### cuts
Perhaps the most important field, this allows for specification and toggling of various data selections. Each cut has an `enabled` field (true/false) and a `condition` field (a boolean which must be met for the combo to be cut). All cut language is exclusive by default, meaning that if the condition is true, the combo will be cut, and if it is false, it will be kept (in contrast to language where a selection is made, i.e. a condition being true results in the combo being selected or kept). Here is an example of a group of cuts which remove different portions of the data based on confidence level:
```toml
[cuts] # this table header is optional
[cuts.confidence_level]
enabled = true
condition = "locConfidenceLevel < 1e-4"

[cuts.select_hc]
enabled = false
condition = "locConfidenceLevel < 1e-9"

[cuts.select_lc]
enabled = false
condition = "locConfidenceLevel > 1e-10 || locConfidenceLevel < 1e-20"
```
Here, only one cut is enabled, so the others will not enter the final DSelector code at all. The enabled cut removes all combos with `locConfidenceLevel` less than `1e-4` (thus selecting high-confidence events).

#### weights
The `weights` field can be used to assign different weights based on conditional statements (such as a sideband subtraction).
```toml
[weights] # again, this is optional
[weights.some_weight]
enabled = true
weight = "0.3"
condition = "true"

[weights.another_weight]
enabled = true
weight = "my_factor"
condition = "locConfidenceLevel > 1e-9"
code = """
Double_t my_factor = 0.4;
if(locConfidenceLevel < 1e-4) {
  my_factor = 0.2
}
"""
```
This code describes two weights, one of which gives all events a weight of `0.3` and the other of which gives a weight which depends on several conditions: the weight is only applied if the confidence level is greater than `1e-9` and if this is true it checks whether or not it is less than `1e-4` and assigns different weights accordingly. Anything written in the `code` field here is inserted immediately before the weight is applied and can access code from any of the prior fields like `variables` and `vectors`. Note that `enabled` is a boolean field while `condition` is a string. `condition` gets written directly as code, so `condition = "true"` just creates an `if(true)` statement in the C code. Additionally, the `weight` parameter is a string rather than an float to allow for more complicated expressions to be entered directly into the code.

#### uniqueness
This field keeps track of the uniqueness of the combos being plotted in various histograms. You may define multiple fields here, but you must define at least some uniqueness tracking for each histogram you want to create:
```toml
[uniqueness]
[uniqueness.track_all]
particles = "all"
histograms = "all"

[uniqueness.track_none]
particles = "none"
histograms = "all"

[uniqueness.track_beam]
particles = ["Beam"]
histograms = ["MissingMassSquared"]
cuts = ["select_hc"]

[uniqueness.track_a_few]
particles = ["PiPlus1", "PiMinus1"]
histograms = "all"
```
Note the use of `"all"` and `"none"` in the `particles` field. The keyword `"none"` is special and it allows you to add histograms which skip uniqueness tracking. Similarly, `"all"` is shorthand for including all of the trackable particles, including the beam. Finally, in the `histogram` field, `"all"` is a shorthand which applies this tracking to every histogram. If the `--no-folders` option is used, each tracking field creates copies of histograms with a `_<tracker name>` suffix added to them, although in the case of `"all"` particles, no suffix is added, and in the case of `"none"`, the suffix `_allcombos` is added. Because of this, you cannot define multiple uniqueness trackers with "all" or "none" particle fields. However, without `--no-folders`,

#### histograms
The `histograms` field contains the information needed to create each histogram. There are several use cases, but the simplest histogram can be generated as:
```toml
[histograms]
[histograms.MissingMassSquared]
x = "locMissingP4.M2()"
xrange = [-0.1, 0.1]
xbins = 201
xlabel = "(Missing Mass)^{2}"

[histograms.Log10KinFitCL]
x = "loclog10ConfidenceLevel"
xrange = [-20, 0]
xbins = 200
xlabel = "Log(CL)"
```
The `x` parameter describes the variable to plot (this can also include any inline C code, like `locMissingP4.M2()`, for example). `xrange` describes the minimum and maximum bin edges, and `xbins` tells the program how many bins to use in the histogram. Additionally, the user may supply fields like `xlabel`, `ylabel`, and `title` to label the histogram correspondingly (these take a string which may include the proper ROOT-to-LaTeX formatters).

To make a 2D histogram, we just include `y`, `yrange`, and `ybins` fields:
```toml
[histograms.vanHove]
x = "locVanHoveX"
xrange = [-3.0, 3.0]
xbins = 100
xlabel = "X"
y = "locVanHoveY"
yrange = [-3.0, 3.0]
ybins = 100
ylabel = "Y"
```
There is an alternative way to create 2D histograms if two 1D histograms are already defined. We can use the `xhist` and `yhist` fields to copy information from existing histograms (this can also be used with just `xhist` to create copies of 1D histograms). Changing any of the fields will overwrite the existing data copied over from the old histogram into the new one. For example:
```toml
[histograms.KShort1_InvMass]
x = "locDecayingKShort1P4_Measured.M()"
xrange = [0.3, 0.7]
xbins = 100
xlabel = "K_{S,1}^{0} Invariant Mass (GeV/c^{2})"

[histograms.KShort2_InvMass]
x = "locDecayingKShort2P4_Measured.M()"
xhist = "KShort1_InvMass"
xlabel = "K_{S,2}^{0} Invariant Mass (GeV/c^{2})"

[histograms.Ks1vsKs2]
xhist = "KShort1_InvMass"
xbins = 400
yhist = "KShort2_InvMass"
title = "Correlation Plot"
```
creates three histograms. The first has all fields explicitly defined. The `KShort2_InvMass` histogram inherets `xrange` and `xbins` from `KShort1_InvMass` but changes the `x` variable as well as the `xlabel`. Finally, `Ks1vsKs2` is a 2D histogram showing the correlation of the kaon masses, but it overwrites the number of `xbins` and adds a `title`.

One final field exists to allow for some very specific use cases: `destination` can be used to double-fill a histogram:
```toml
[histograms.HXCosTheta]
x = "locKShort1HX.CosTheta()"
xrange = [ -1, 1, ]
xbins = 50
xlabel = "cos(#theta_{HX})"

[histograms.HXCosTheta2]
destination = "HXCosTheta"
x = "locKShort2HX.CosTheta()"
```
What is the use of this? Well, suppose we had two identical kaons and we wanted to plot an angle in the kaon + kaon center-of-momentum frame. The kaons are back-to-back in this frame, so we could plot both of them in the same histogram by specifying that the `destination` of the second histogram is the first histogram. Using the `destination` field will cause the program to ignore everything except `x` and `y` fields for that particular histogram, essentially sending the `x` and/or `y` variables to the `destination`.

#### output
The `output` field allows the user to generate flat trees alongside the default output histograms and analysis trees. It is not a required field, so if it is omitted, no flat trees will be generated. However, if one wishes to flatten a tree, it is simple to do. The code below fills flat trees with all of the information required for an [AmpTools](https://github.com/mashephe/AmpTools) analysis, for example:
```toml
[output.Total_Weight]
name = "Weight"
type = "Float_t"
value = "locWeight"

[output.E_Beam]
name = "E_Beam"
type = "Float_t"
value = "locBeamP4.E()"

[output.Px_Beam]
name = "Px_Beam"
type = "Float_t"
value = "locBeamP4.Px()"

[output.Py_Beam]
name = "Py_Beam"
type = "Float_t"
value = "locBeamP4.Py()"

[output.Pz_Beam]
name = "Pz_Beam"
type = "Float_t"
value = "locBeamP4.Pz()"

[output.E_FinalState]
name = "E"
type = "Float_t"

[output.E_FinalState.array]
name = "FinalState"
values = [
    "locProtonP4.E()",
    "locDecayingKShort1P4.E()",
    "locDecayingKShort2P4.E()",
]

[output.Px_FinalState]
name = "Px"
type = "Float_t"

[output.Px_FinalState.array]
name = "FinalState"
values = [
    "locProtonP4.Px()",
    "locDecayingKShort1P4.Px()",
    "locDecayingKShort2P4.Px()",
]

[output.Py_FinalState]
name = "Py"
type = "Float_t"

[output.Py_FinalState.array]
name = "FinalState"
values = [
    "locProtonP4.Py()",
    "locDecayingKShort1P4.Py()",
    "locDecayingKShort2P4.Py()",
]

[output.Pz_FinalState]
name = "Pz"
type = "Float_t"

[output.Pz_FinalState.array]
name = "FinalState"
values = [
    "locProtonP4.Pz()",
    "locDecayingKShort1P4.Pz()",
    "locDecayingKShort2P4.Pz()",
]
```
Each `output` subfield defines a new branch in the flat tree with the given `type`. Branches will be filled from the code in the `value` field. Note the added syntax which allows for the creation of arrays. The `array` field contains an array `name` as well as a list of `values` rather than a single `value`. The TOML syntax is flexible, so we could also write one of these arrays as
```toml
[output.Pz_FinalState]
name = "Pz"
type = "Float_t"
array.name = "FinalState"
array.values = [
    "locProtonP4.Pz()",
    "locDecayingKShort1P4.Pz()",
    "locDecayingKShort2P4.Pz()",
]
```
In either case, this will create a branch named "Pz_FinalState" which contains an array of the three particles' z-momenta. The DSelector's `dFlatTreeInterface` handles all of the numbering branches (`N_FinalState` in this example).

## Installing
The `MakePSelector` program can be installed by cloning this repository and running
```
pip3 install .
```
in the root project directory. Due to the specificity of this program, I do not see the need to publish it to PyPI. When installed in this way it will make the `MakePSelector` script available for execution from any directory. 

> Note that `MakePSelector` is written for `python3`. I will not write a version for `python2`, as it has been [deprecated/sunset since 2020 and is no longer supported](https://www.python.org/doc/sunset-python-2/). If you are still using `python2` for analysis, 99% of your code can be updated by simply converting your `print` statements.

## Dependencies
This program has two dependencies, [particle](https://github.com/scikit-hep/particle) from the Scikit-HEP group and [tomli](https://github.com/hukkin/tomli) which parses TOML files. However, if you are using Python 3.11 or later, the `tomllib` package is now native and will be used instead.

There is also a hidden `PyROOT` dependency. I wish this were not the case, but the particle decay map is located in the `UserInfo` part of the TTree, which is unfortunately not easily accessible by libraries like `uproot`. This means your version of ROOT must be built with `python3` compatibility, which is not how the default ROOT binaries ship from CERN. If you build ROOT from source (about four lines of shell code), it should automatically detect a `python3` installation.

## Changelog

v1.1.0
- Added optional `name` field which can be overridden by `--name` flag
- Removed `continue` statements from cuts. The default behavior now will be that everything survives till histograms are filled, `uniqueness` blocks without a `cuts` field and output (flat)trees will only be filled with combos that survived `enabled` cuts.
	- This allows for the following behavior: The user specifies three sequential cuts, `cut1`, `cut2`, and `cut3`. They wish to see the effect of each sequential cut on their histograms. They can then create `uniqueness` blocks with `cuts = ["cut1"]`, `cuts = ["cut1", "cut2"]`, and one block which doesn't have the field for all of the cuts. The `enabled` keyword only effects this final block, as well as output (flat)trees, so the end result will contain three folders, one with histograms of events which pass `cut1`, another with events which pass `cut1` and `cut2`, and another with events which pass all enabled cuts.

v1.0.0
- Added the `cut` field to `uniqueness` blocks, allowing for histograms to only be plotted if they pass the specified cuts
- Removed the `--force` option and made this the default behavior

v0.0.2
- Switched configuration file support from JSON to TOML

v0.0.1
- Initial Release

Planned features will be added as issues arise. I can imagine there will be lots of very specific features or shorthands that might be appreciated. For example, we almost always want to calculate things like the Mandelstam "t" or the missing mass squared, so in the future I might implement a shorthand to do this automatically.
