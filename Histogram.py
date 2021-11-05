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
        self.uniqueness = kwargs.get("uniqueness")
        self.weight = kwargs.get("weight")
        self.xhist = kwargs.get("xhist")
        self.yhist = kwargs.get("yhist")

    def resolve(self, others):
        if self.xhist:
            if not self.xrange:
                self.xrange = others.get(self.xhist).get("xrange")
            if not self.xbins:
                self.xbins = others.get(self.xhist).get("xbins")
            if not self.xlabel:
                self.xlabel = other.get(self.xhist).get("xlabel")

class HistogramRegister:
    def __init__(self):
        self.histograms = {}

    def register(self, config):
        hist_list = config.get("histograms")
        if hist_list:
            self.histograms = {hist_name: Histogram(hist_info) for hist_name, hist_info in hist_list.items()}
            for hist_name, histogram in self.histograms.items():
                assert histogram.x, f"Must provide at least an 'x' parameter in {hist_name}"
                histogram.resolve(self.histograms)
