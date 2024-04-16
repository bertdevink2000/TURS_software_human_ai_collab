import dill

from turs2.utils_visualization import *
from turs2.Ruleset import *
from turs2.Rule import *

data_name = "23_mammography"

filehandler = open(data_name + "_ruleset_object.pkl", 'rb')
ruleset = dill.load(filehandler)

ruleset.probability_distribution_graph(True)
