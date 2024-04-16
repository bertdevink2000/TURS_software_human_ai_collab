import sys
import os

current_dir = os.getcwd()
sys.path.extend([current_dir + "/turs2/"])

# # for mac local
# sys.path.extend(['/Users/yanglincen/projects/TURS'])
# sys.path.extend(['/Users/yanglincen/projects/TURS/turs2'])
# # for DSlab server:
# sys.path.extend(['/home/yangl3/projects/turs'])
# sys.path.extend(['/home/yangl3/projects/turs/turs2'])

import numpy as np
import pandas as pd
import copy
import time
import cProfile
from datetime import datetime
from line_profiler import LineProfiler
import cProfile, pstats
import dill

from sklearn.preprocessing import LabelEncoder, OrdinalEncoder, OneHotEncoder
from sklearn.metrics import roc_auc_score, precision_recall_curve, f1_score, auc, log_loss
from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import RandomForestClassifier

from turs2.DataInfo import *
from turs2.Ruleset import *
from turs2.utils_predict import *
from turs2.ModelEncoding import *
from turs2.DataEncoding import *
from turs2.utils_visualization import *

from turs2.exp_utils import *
from turs2.exp_predictive_perf import *

np.seterr(all='raise')

exp_res_alldata = []
date_and_time = datetime.now().strftime("%Y%m%d_%H%M%S")

if len(sys.argv) == 1:
    data_name = "25_musk.npz"
else:
    data_name = sys.argv[1]

print("Running on: ", data_name)
d_np = np.load("../ADbench_datasets_Classical/" + data_name)
X = d_np["X"]
y = d_np["y"]
d_original = pd.DataFrame(np.concatenate([X, y.reshape(-1, 1)], axis=1))
d = preprocess_data(d_original)

num_class = len(np.unique(y))
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=2)

for fold, (train_index, test_index) in enumerate(skf.split(X, y)):
    X_train, y_train = X[train_index], y[train_index]
    X_test, y_test = X[test_index], y[test_index]

    start_time = time.time()
    alg_config = AlgConfig(
        num_candidate_cuts=20, max_num_rules=500, max_grow_iter=500, num_class_as_given=None,
        beam_width=10,
        log_learning_process=False,
        dataset_name=None,
        feature_names=["X" + str(i) for i in range(X.shape[1])],
        validity_check="either"
    )
    data_info = DataInfo(X=X_train, y=y_train, beam_width=None, alg_config=alg_config)

    data_encoding = NMLencoding(data_info)
    model_encoding = ModelEncodingDependingOnData(data_info)
    ruleset = Ruleset(data_info=data_info, data_encoding=data_encoding, model_encoding=model_encoding)
    ruleset.fit(max_iter=1000, printing=True)

    data_name = data_name.split(".", 1)[0]
    filehandler = open(data_name + "_ruleset_object.pkl", 'wb')
    dill.dump(ruleset, filehandler)