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
        if self.particles == "all":
            self.tag = ""
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
        else:
            self.tag = f"_{name}"

    def init_string(self, indent=1):
        if len(self.particles) == 1:
            return "    " * indent + f"set<Int_t> locUsedSoFar_{self.name};\n"
        else:
            return "    " * indent + f"set<map<Particle_t, set<Int_t>>> locUsedSoFar_{self.name};\n"

    def header_hists(self, indent=2):
        outstring = ""
        for hist_name in self.histograms:
            hist = Histogram(hist_name, self.config)
            outstring += hist.header_string(tag=self.tag, indent=indent)
        return outstring

    def init_hists(self, indent=1):
        outstring = ""
        for hist_name in self.histograms:
            hist = Histogram(hist_name, self.config)
            outstring += hist.init_string(tag=self.tag, indent=indent)
        return outstring

    def fill_string(self, indent=2):
        outstring = ""
        if len(self.particles) == 1:
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
            for hist_name in self.histograms:
                hist = Histogram(hist_name, self.config)
                outstring += hist.fill_string(tag=self.tag, indent=indent+1)
            outstring += "    " * (indent + 1) + f"locUsedSoFar_{self.name}.insert(loc{self.particles[0]}ID);\n"
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
            for hist_name in self.histograms:
                hist = Histogram(hist_name, self.config)
                outstring += hist.fill_string(tag=self.tag, indent=indent+1)
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

    def init_string(self, tag="", indent=1):
        if not self.has_destination:
            if self.is2D:
                return "    " * indent + f"dHist_{self.tag}{tag} = new TH2D(\"{self.tag}{tag}\", \"{self.title};{self.get_xlabel()};{self.get_ylabel()}\", {self.get_x_param('xbins')}, {self.get_x_param('xrange')[0]}, {self.get_x_param('xrange')[1]}, {self.get_y_param('ybins')}, {self.get_y_param('yrange')[0]}, {self.get_y_param('yrange')[1]});\n"
            else:
                return "    " * indent + f"dHist_{self.tag}{tag} = new TH1D(\"{self.tag}{tag}\", \"{self.title};{self.get_xlabel()};{self.get_ylabel()}\", {self.get_x_param('xbins')}, {self.get_x_param('xrange')[0]}, {self.get_x_param('xrange')[1]});\n"
        else:
            return ""

    def fill_string(self, tag="", indent=1):
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
            outstring += "    " * (indent + 1) + "continue;\n"
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
                for line in self.weight_config["code"]:
                    outstring += "    " * indent + line + "\n"
            outstring += "    " * indent + f"if({self.weight_config['condition']}) {{\n"
            outstring += "    " * (indent + 1) + f"if(locWeight < 0 && {self.weight_config['weight']} < 0) {{\n"
            outstring += "    " * (indent + 2) + f"locWeight *= -1 * {self.weight_config['weight']};\n"
            outstring += "    " * (indent + 1) + "} else {\n"
            outstring += "    " * (indent + 2) + f"locWeight *= {self.weight_config['weight']};\n"
            outstring += "    " * (indent + 1) + "}\n"
            outstring += "    " * indent + "}\n"
        return outstring
