class Uniqueness:
    def __init__(self, name, config, particle_map):
        self.config = config
        self.uniqueness_config = config["uniqueness"][name]
        self.histograms = self.uniqueness_config["histograms"]
        self.particle_map = particle_map
        if self.histograms == "all":
            self.histograms = [hist_name for hist_name in self.config["histograms"].keys()]
        self.particles = self.uniqueness_config["particles"]
        self.name = name
        self.folder_name = self.uniqueness_config.get("folder", name)
        self.cuts = self.uniqueness_config.get("cuts", None)
        if self.cuts is not None:
            if isinstance(self.cuts, str):
                self.cuts = [self.cuts]
            assert isinstance(self.cuts, list), f"Uniqueness cuts must be a list of cut names or a single string for one cut (error in {self.name})"
        if self.particles == "all":
            if self.name == "all":
                self.tag = ""
            else:
                self.tag = f"_{name}"
            self.particles = ["Beam"]
            for step in self.particle_map:
                for particle in step:
                    if "Beam" in particle.get("name"):
                        continue
                    elif "Target" in particle.get("name"):
                        continue
                    elif "Decaying" in particle.get("name"):
                        continue
                    elif "Missing" in particle.get("name"):
                        continue
                    else:
                        self.particles.append(particle.get("name"))
        elif self.particles == "none":
            self.tag = "_allcombos"
            self.particles = []
        else:
            self.tag = f"_{name}"

    def folder_string(self, indent=1):
        return "    " * indent + f"TDirectory *dir{self.name} = dir_main->mkdir(\"{self.folder_name}\");\n"

    def init_string(self, indent=1):
        if len(self.particles) == 0:
            return "    " * indent + "// Some histograms will be generated without uniqueness tracking\n"
        elif len(self.particles) == 1:
            return "    " * indent + f"set<Int_t> locUsedSoFar_{self.name};\n"
        else:
            return "    " * indent + f"set<map<Particle_t, set<Int_t>>> locUsedSoFar_{self.name};\n"

    def header_hists(self, indent=2, n_folders=1):
        outstring = ""
        for hist_name in self.histograms:
            hist = Histogram(hist_name, self.config)
            outstring += hist.header_string(tag=self.tag, indent=indent)
        return outstring

    def init_hists(self, indent=1, n_dir=-1):
        outstring = ""
        for hist_name in self.histograms:
            hist = Histogram(hist_name, self.config)
            outstring += hist.init_string(tag=self.tag, indent=indent, n_dir=n_dir)
        return outstring

    def fill_hists(self, indent=3, n_dir=-1):
        outstring = ""
        if self.cuts is not None:
            outstring = "    " * indent + "if(!("
            outstring += ") && !(".join([self.config['cuts'][cut_name]["condition"] for cut_name in self.cuts])
            outstring += ")) {\n"
        else:
            outstring = "    " * indent + "if(!dComboWrapper->Get_IsComboCut()) {\n" # if no cuts are listed, use all enabled cuts
        for hist_name in self.histograms:
            hist = Histogram(hist_name, self.config)
            outstring += hist.fill_string(tag=self.tag, indent=indent+1, n_dir=n_dir)
        outstring += "    " * indent + "}\n"
        return outstring

    def fill_string(self, indent=2, n_dir=-1):
        outstring = ""
        if len(self.particles) == 0:
            outstring += self.fill_hists(indent=2, n_dir=n_dir)
        elif len(self.particles) == 1:
            if self.particles[0] == "Beam":
                outstring += "    " * indent + f"if(locUsedSoFar_{self.name}.find(loc{self.particles[0]}ID) == locUsedSoFar_{self.name}.end()) {{\n"
            else:
                for step in self.particle_map:
                    for particle in step:
                        if particle.get("name") == self.particles[0]:
                            if particle.get("particle").charge != 0:
                                outstring += "    " * indent + f"if(locUsedSoFar_{self.name}.find(loc{self.particles[0]}TrackID)) == locUsedSoFar_{self.name}.end()) {{\n"
                            else:
                                outstring += "    " * indent + f"if(locUsedSoFar_{self.name}.find(loc{self.particles[0]}NeutralID)) == locUsedSoFar_{self.name}.end()) {{\n"
            outstring += self.fill_hists(n_dir=n_dir)
            outstring += "    " * (indent + 1) + f"locUsedSoFar_{self.name}.insert(loc{self.particles[0]}ID);\n"
            outstring += "    " * indent + "}\n"
        else:
            outstring += "    " * indent + f"map<Particle_t, set<Int_t>> locUsedThisCombo_{self.name};\n"
            for tracked_particle in self.particles:
                if tracked_particle == "Beam":
                    outstring += "    " * indent + f"locUsedThisCombo_{self.name}[Unknown].insert(locBeamID);\n"
                else:
                    for step in self.particle_map:
                        for particle in step:
                            if particle.get("name") == tracked_particle:
                                if particle.get("particle").charge != 0:
                                    outstring += "    " * indent + f"locUsedThisCombo_{self.name}[PDGtoPType({particle.get('pid')})].insert(loc{tracked_particle}TrackID);\n"
                                else:
                                    outstring += "    " * indent + f"locUsedThisCombo_{self.name}[PDGtoPType({particle.get('pid')})].insert(loc{tracked_particle}NeutralID);\n"
            outstring += "    " * indent + f"if(locUsedSoFar_{self.name}.find(locUsedThisCombo_{self.name}) == locUsedSoFar_{self.name}.end()) {{\n"
            outstring += self.fill_hists(n_dir=n_dir)
            outstring += "    " * (indent + 1) + f"locUsedSoFar_{self.name}.insert(locUsedThisCombo_{self.name});\n"
            outstring += "    " * indent + "}\n"
        return outstring

class Histogram:
    def __init__(self, name, config):
        self.config = config
        self.histogram_config = self.config["histograms"][name]
        self.tag = name
        self.has_destination = False
        if "destination" in self.histogram_config.keys(): # option for double-filling
            self.tag = self.histogram_config["destination"]
            self.has_destination = True
        self.sourced_x = "xhist" in self.histogram_config.keys()
        self.sourced_y = "yhist" in self.histogram_config.keys()
        self.is2D = ("y" in self.histogram_config.keys()) or self.sourced_y
        assert ("x" in self.histogram_config.keys()) or self.sourced_x, f"No 'x' variable for histogram {name}"
        assert ("xrange" in self.histogram_config.keys()) or self.sourced_x or self.has_destination, f"No 'xrange' variable for histogram {name}"
        assert ("xbins" in self.histogram_config.keys()) or self.sourced_x or self.has_destination, f"No 'xbins' variable for histogram {name}"
        if self.is2D:
            assert ("yrange" in self.histogram_config.keys()) or self.sourced_y or self.has_destination, f"No 'yrange' variable for histogram {name}"
            assert ("ybins" in self.histogram_config.keys()) or self.sourced_y or self.has_destination, f"No 'ybins' variable for histogram {name}"
        self.title = self.histogram_config.get("title")
        if not self.title:
            self.title = ""
        if "weight" in self.histogram_config.keys():
            self.weight = self.histogram_config["weight"]
        else:
            self.weight = "locWeight"

    def get_x_param(self, param_name):
        if param_name in self.histogram_config.keys():
            return self.histogram_config[param_name]
        else:
            return Histogram(self.histogram_config["xhist"], self.config).get_x_param(param_name)

    def get_y_param(self, param_name):
        if param_name in self.histogram_config.keys():
            return self.histogram_config[param_name]
        else:
            return Histogram(self.histogram_config["yhist"], self.config).get_x_param(param_name.replace("y", "x"))

    def get_xlabel(self):
        xlabel = self.histogram_config.get("xlabel")
        if not xlabel:
            if self.sourced_x:
                xlabel = self.get_x_param("xlabel")
            else:
                xlabel = ""
        return xlabel

    def get_ylabel(self):
        ylabel = self.histogram_config.get("ylabel")
        if not ylabel:
            if self.sourced_y:
                ylabel = self.get_y_param("ylabel")
            else:
                ylabel = ""
        return ylabel

    def header_string(self, tag="", indent=1):
        if not self.has_destination:
            if self.is2D:
                return "    " * indent + f"TH2D* dHist_{self.tag}{tag};\n"
            else:
                return "    " * indent + f"TH1D* dHist_{self.tag}{tag};\n"
        else:
            return ""

    def init_string(self, tag="", indent=1, n_dir=-1):
        if not self.has_destination:
            if n_dir >= 0:
                tag = f"[{n_dir}]"
                if self.is2D:
                    return "    " * indent + f"dHist_{self.tag}{tag} = new TH2D(\"{self.tag}\", \"{self.title};{self.get_xlabel()};{self.get_ylabel()}\", {self.get_x_param('xbins')}, {self.get_x_param('xrange')[0]}, {self.get_x_param('xrange')[1]}, {self.get_y_param('ybins')}, {self.get_y_param('yrange')[0]}, {self.get_y_param('yrange')[1]});\n"
                else:
                    return "    " * indent + f"dHist_{self.tag}{tag} = new TH1D(\"{self.tag}\", \"{self.title};{self.get_xlabel()};{self.get_ylabel()}\", {self.get_x_param('xbins')}, {self.get_x_param('xrange')[0]}, {self.get_x_param('xrange')[1]});\n"
            else:
                if self.is2D:
                    return "    " * indent + f"dHist_{self.tag}{tag} = new TH2D(\"{self.tag}{tag}\", \"{self.title};{self.get_xlabel()};{self.get_ylabel()}\", {self.get_x_param('xbins')}, {self.get_x_param('xrange')[0]}, {self.get_x_param('xrange')[1]}, {self.get_y_param('ybins')}, {self.get_y_param('yrange')[0]}, {self.get_y_param('yrange')[1]});\n"
                else:
                    return "    " * indent + f"dHist_{self.tag}{tag} = new TH1D(\"{self.tag}{tag}\", \"{self.title};{self.get_xlabel()};{self.get_ylabel()}\", {self.get_x_param('xbins')}, {self.get_x_param('xrange')[0]}, {self.get_x_param('xrange')[1]});\n"
        else:
            return ""

    def fill_string(self, tag="", indent=1, n_dir=-1):
        if n_dir >= 0:
            tag = f"[{n_dir}]"
        if self.is2D:
            return "    " * indent + f"dHist_{self.tag}{tag}->Fill({self.get_x_param('x')}, {self.get_y_param('y')}, {self.weight});\n"
        else:
            return "    " * indent + f"dHist_{self.tag}{tag}->Fill({self.get_x_param('x')}, {self.weight});\n"


class Boost:
    def __init__(self, name, config, vector_names, from_name=""):
        self.name = name
        self.tag = f"_{name}"
        self.boost_config = config["boosts"][name]
        self.boost_vector = self.boost_config["boostvector"]
        self.vector_names = vector_names
        self.from_name = from_name
        if self.from_name:
            self.from_tag = f"_{from_name}"
        else:
            self.from_tag = ""

    def boost_string(self, indent=2):
        outstring = "    " * indent + f"// Boost: {self.from_name} -> {self.name}\n"
        outstring += "    " * indent + f"TLorentzVector locBoostP4{self.tag} = {self.boost_vector}{self.from_tag};\n"
        outstring += "    " * indent + "// Boosted Vectors:\n"
        for vector_name in self.vector_names:
            outstring += "    " * indent + f"TLorentzVector {vector_name}{self.tag} = {vector_name}{self.from_tag};\n"
        outstring += "\n"
        for vector_name in self.vector_names:
            outstring += "    " * indent + f"{vector_name}{self.tag}.Boost(-locBoostP4{self.tag}.BoostVector());\n"
        outstring += "\n"
        sub_boost_dict = self.boost_config.get("boosts")
        if sub_boost_dict:
            for key in sub_boost_dict.keys():
                boost = Boost(key, self.boost_config, self.vector_names, from_name=self.name)
                outstring += boost.boost_string()
        return outstring

class Cut:
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.cut_config = self.config['cuts'][name]

    def cut_string(self, indent=2):
        outstring = ""
        if self.cut_config["enabled"]:
            outstring += "    " * indent + f"if({self.cut_config['condition']}) {{\n"
            outstring += "    " * (indent + 1) + "dComboWrapper->Set_IsComboCut(true);\n"
            # outstring += "    " * (indent + 1) + "continue;\n"
            outstring += "    " * indent + "}\n"
        return outstring

class Weight:
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.weight_config = self.config['weights'][name]

    def weight_string(self, indent=2):
        outstring = ""
        if self.weight_config["enabled"]:
            if self.weight_config.get("code"):
                for line in self.weight_config["code"].splitlines():
                    outstring += "    " * indent + line + "\n"
            outstring += "    " * indent + f"if({self.weight_config['condition']}) {{\n"
            outstring += "    " * (indent + 1) + f"if(locWeight < 0 && {self.weight_config['weight']} < 0) {{\n"
            outstring += "    " * (indent + 2) + f"locWeight *= -1 * {self.weight_config['weight']};\n"
            outstring += "    " * (indent + 1) + "} else {\n"
            outstring += "    " * (indent + 2) + f"locWeight *= {self.weight_config['weight']};\n"
            outstring += "    " * (indent + 1) + "}\n"
            outstring += "    " * indent + "}\n"
        return outstring

class FlatBranch:
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.branch_config = self.config['output'][name]
        self.isArray = bool(self.branch_config.get('array'))
        self.num_name = ""
        if self.isArray:
            self.num_name = f"Num{self.branch_config['array']['name']}"

    def init_string(self, indent=1):
        outstring = "    " * indent + f"// Create Flat {self.name} branch\n"
        if self.isArray:
            array_config = self.branch_config['array']
            dtype = self.branch_config['type']
            array_name = array_config['name']
            array_values = array_config['values']
            outstring += "    " * indent + f"""dFlatTreeInterface->Create_Branch_FundamentalArray<{dtype}>("{self.branch_config['name']}_{array_name}", "{self.num_name}");\n"""
        else:
            dtype = self.branch_config['type']
            outstring += "    " * indent + f"""dFlatTreeInterface->Create_Branch_Fundamental<{dtype}>("{self.branch_config['name']}");\n"""
        return outstring


    def init_num_string(self, indent=1):
        return "    " * indent + f"""dFlatTreeInterface->Create_Branch_Fundamental<Int_t>("{self.num_name}");\n"""


    def fill_string(self, indent=2):
        outstring = "    " * indent + f"// Fill Flat {self.name} branch\n"
        if self.isArray:
            array_config = self.branch_config['array']
            dtype = self.branch_config['type']
            array_name = array_config['name']
            array_values = array_config['values']
            num_name = f"Num{self.branch_config['name']}"
            for i, value in enumerate(array_values):
                outstring += "    " * indent + f"""dFlatTreeInterface->Fill_Fundamental<{dtype}>("{self.branch_config['name']}_{array_name}", {array_values[i]}, {i});\n"""
        else:
            dtype = self.branch_config['type']
            value = self.branch_config['value']
            outstring += "    " * indent + f"""dFlatTreeInterface->Fill_Fundamental<{dtype}>("{self.branch_config['name']}", {value});\n"""
        return outstring


    def fill_num_string(self, indent=2):
        array_config = self.branch_config['array']
        array_values = array_config['values']
        return "    " * indent + f"""dFlatTreeInterface->Fill_Fundamental<Int_t>("{self.num_name}", {len(array_values)});\n"""
