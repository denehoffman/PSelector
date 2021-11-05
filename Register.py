from pprint import pprint

class Histogram:
    def __init__(self, **kwargs):
        # Current compatible histogram keywords:
        self.x = kwargs.get("x")
        self.xrange = kwargs.get("xrange")
        self.xbins = kwargs.get("xbins")
        self.xlabel = kwargs.get("xlabel")
        self.y = kwargs.get("y")
        self.yrange = kwargs.get("yrange")
        self.ybins = kwargs.get("ybins")
        self.ylabel = kwargs.get("ylabel")
        self.title = kwargs.get("title")
        self.weight = kwargs.get("weight")
        self.xhist = kwargs.get("xhist")
        self.yhist = kwargs.get("yhist")
        if not self.weight:
            self.weight = "locHistAccidWeightFactor"

    def resolve(self, others):
        if self.xhist:
            if not self.x:
                self.x = others.get(self.xhist).x
            if not self.xrange:
                self.xrange = others.get(self.xhist).xrange
            if not self.xbins:
                self.xbins = others.get(self.xhist).xbins
            if not self.xlabel:
                self.xlabel = others.get(self.xhist).xlabel
        if self.yhist:
            if not self.y:
                self.y = others.get(self.yhist).x
            if not self.yrange:
                self.yrange = others.get(self.yhist).xrange
            if not self.ybins:
                self.ybins = others.get(self.yhist).xbins
            if not self.ylabel:
                self.ylabel = others.get(self.yhist).xlabel

    def get_label_string(self):
        return f"{self.title if self.title else ''};{self.xlabel if self.xlabel else ''};{self.ylabel if self.ylabel else ''}"

    def is_valid(self):
        xvalid = self.x and self.xrange and self.xbins
        yvalid = self.yrange and self.ybins if self.y else True
        return xvalid and yvalid


class HistogramRegister:
    def __init__(self, config):
        self.histograms = {}
        hist_dict = config.get("histograms")
        if not hist_dict:
            hist_dict = {}
        hist_dict["MissingMassSquared"] = {"x": "locMissingMassSquared", "xrange": [-0.06, 0.06], "xbins": 600, "xlabel": "Missing Mass Squared (GeV/c^{2})^{2}"}
        hist_dict["BeamEnergy"] = {"x": "locBeamP4.E()", "xrange": [0.0, 12.0], "xbins":600, "xlabel": "Beam Energy (GeV)"}
        self.histograms = {hist_name: Histogram(**hist_info) for hist_name, hist_info in hist_dict.items()}
        for hist_name, histogram in self.histograms.items():
            histogram.resolve(self.histograms)
            assert histogram.is_valid(), f"Invalid histogram: {hist_name}!"

    def get_hist_names(self):
        return list(self.histograms.keys())

class Uniqueness:
    def __init__(self, **kwargs):
        self.particles = kwargs.get("particles")
        if not self.particles:
            self.particles = []
        self.histograms = kwargs.get("histograms")
        if not self.histograms:
            self.histograms = []
        for particle in self.particles:
            particle = particle.replace("loc", "")
        

class UniquenessRegister:
    def __init__(self, config, hist_names):
        self.uniqueness = {}
        uniq_dict = config.get("uniqueness")
        if not uniq_dict:
            uniq_dict = {}
        if not uniq_dict.get("default"):
            uniq_dict["default"] = {"particles": "all", "histograms": []}
        if not uniq_dict.get("beam"):
            uniq_dict["beam"] = {"particles": ["Beam"], "histograms": ["BeamEnergy"]}
        for hist_name in hist_names:
            tracked = False
            for uniq_name, uniq_info in uniq_dict.items():
                if not uniq_name == "default":
                    if hist_name in uniq_info.get('histograms'):
                        tracked = True
            if not tracked:
                uniq_dict["default"]["histograms"].append(hist_name)
                
        self.uniqueness = {uniq_name: Uniqueness(**uniq_info) for uniq_name, uniq_info in uniq_dict.items()}

class CodeRegister:
    def __init__(self, config):
        lines = config.get("code")
        self.code = []
        if lines:
            self.code = lines
