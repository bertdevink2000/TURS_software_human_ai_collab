from sklearn import tree
import numpy as np

from nml_regret import *
from utils import calc_probs
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder
import pandas as pd
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.metrics import precision_recall_curve, roc_curve, roc_auc_score, auc, average_precision_score, f1_score, confusion_matrix
import copy
from sklearn.tree import DecisionTreeClassifier
import matplotlib.pyplot as plt
from tree_utils import *
from scipy.special import gammaln


def get_nml_cldata(X, y, clf):
    num_class = len(np.unique(y))
    which_nodes = clf.apply(X)

    negloglike, regert_list = [], []
    for i in np.unique(which_nodes):
        instances_covered = (which_nodes == i)
        y_covered = y[instances_covered]

        p = calc_probs(y_covered, num_class)
        p = p[p != 0]

        negloglike.append(-np.sum(np.log2(p) * p) * np.count_nonzero(instances_covered))
        regert_list.append(regret(len(y_covered), num_class))
    return np.sum(negloglike) + np.sum(regert_list)


def chooselog2(N, k):
    return (gammaln(N + 1) - gammaln(N - k + 1) - gammaln(k + 1)) / log(2)


def get_cl_model(tree, X_train):
    features = tree.feature
    cuts = tree.threshold
    is_leaf = (tree.children_left == -1)
    n_leaves = np.count_nonzero(is_leaf)
    n_nodes = len(features)

    # Assume that we always go left if we can, the bits we need are:
    bits_for_number_of_nodes = 2 * np.log2(n_nodes)
    # bits_for_leaves_position = chooselog2(len(is_leaf), n_leaves)  ## To MUCH REDUNDANCY HERE;
    bits_for_leaves_position = np.log2(n_nodes)  # Just a guess, probably wrong..

    num_features = len(X_train[0])

    features_non_leaf = features[~is_leaf]
    p_feature_name = calc_probs(features_non_leaf, num_features)

    # naive_bits_for_which_dimension_in_condition = np.log2(num_features) * len(features_non_leaf)
    nml_bits_for_which_dimension_in_condition = \
        -np.sum(np.log2(p_feature_name[p_feature_name != 0]) * p_feature_name[p_feature_name != 0]) + \
        regret(len(features_non_leaf), num_features)

    bits_for_cuts = np.sum(np.log2(tree.n_node_samples[tree.n_node_samples != 0]))

    cl_model = bits_for_number_of_nodes + bits_for_leaves_position + nml_bits_for_which_dimension_in_condition + bits_for_cuts

    return cl_model

def get_tree_cl(x_train, y_train, num_class):
    n = len(y_train)
    if n > 1000:
        min_samples = np.arange(10, max(50, int(n*0.01)), 20)
    else:
        min_samples = np.arange(10, 110, 20)

    # best_tree_cl = np.inf
    probs = calc_probs(y_train, num_class)
    best_sum_cl_data = np.sum(-np.log2(probs[y_train]))
    best_sum_regrets = regret(len(y_train), num_class)
    best_tree_cl = best_sum_cl_data + best_sum_regrets

    for min_sample in min_samples:
        clf = DecisionTreeClassifier(min_samples_leaf=min_sample, random_state=1)
        clf = clf.fit(x_train, y_train)
        nml_cl_data = get_nml_cldata(x_train, y_train, clf)
        cl_model = get_cl_model(clf.tree_, x_train)
        tree_cl = nml_cl_data + cl_model

        if tree_cl <= best_tree_cl:
            best_tree_cl = tree_cl

    return [best_tree_cl]


def get_entropy(target, num_class):
    probs = calc_probs(target, num_class)
    entropy = -np.sum(np.log2(probs[target]))

    return entropy