import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import scipy.stats
from turs2.Ruleset import *
from turs2.Rule import *

def visualize_as_catplot(ruleset, type):
    #will use the ruleset to generate a graph showing all the variables of the ruleset per feature
    #type can be "box" or "swarm" depending on what the user wants

    #create the dataframe necessary for the plot using the feature and feature name data from the ruleset
    feature_df = pd.DataFrame(ruleset.data_info.features, columns=ruleset.data_info.feature_names)

    #initiate the catplot
    sns.catplot(data=feature_df, native_scale=True, kind=type)

    for rule in ruleset.rules:
        which_variables = np.where(rule.condition_count != 0)[0]
        col = (np.random.random(), np.random.random(), np.random.random())

        no_label = True

        for v in which_variables:
            cut = rule.condition_matrix[:, v][::-1]
            line = plt.hlines(cut, xmin=v-0.5, xmax=v+0.5, colors=col)

            if no_label:
                line.set_label(rule._print())
                no_label = False


    plt.legend(fontsize=6)
    plt.show()

def probability_distribution_graph(ruleset, only_rule = False):
    #ruleset is the ruleset we are using this method on, only_rule signifies whether we want to only show the graphs of
    #only the features which show up in the rules.

    #We use seaborne to make the graph
    sns.set()

    #Initialize the dataframe which will be ordered by features, we will need this to create the distribution graph
    #that we will compare the dataset after applying the rules to, rule_df is the dataframe which will we modify with
    #the rules we find
    feature_df = pd.DataFrame(ruleset.data_info.features, columns=ruleset.data_info.feature_names)
    rule_df = feature_df

    #To check whether it is the first element in the condition matrix or not, relevant for whether the later sign should
    #be > or <
    first = True

    for condition_duo in ruleset.rules[0].condition_matrix:
        index = 0
        for condition in condition_duo:
            if math.isnan(condition):
                index += 1
                continue
            elif first:
                rule_df = rule_df.drop(rule_df[rule_df.iloc[:, index] > condition].index)
            else:
                rule_df = rule_df.drop(rule_df[rule_df.iloc[:, index] < condition].index)

            index += 1
        first = False

    if only_rule:
        counter = 0

        for column in feature_df.columns[0:]:
            #sns.histplot(data=feature_df[column], ax=axes[counter], kde=True, color="blue", stat="density")
            #sns.histplot(data=rule_df[column], ax=axes[counter], kde=True, color="red", alpha=0.6, stat="density")
            if math.isnan(ruleset.rules[0].condition_matrix[0][counter]) and math.isnan(ruleset.rules[0].condition_matrix[1][counter]):
                counter += 1
                rule_df = rule_df.drop(columns=[column])
                continue
            else:
                print(ruleset.rules[0].condition_matrix[0][counter])
                print(ruleset.rules[0].condition_matrix[1][counter])
                #sns.kdeplot(data=feature_df[column], ax=axes[counter], color="blue")
                #sns.kdeplot(data=rule_df[column], ax=axes[counter], color="red", alpha=0.6)
                #print(scipy.stats.pearsonr(feature_df[column], rule_df[column]))
                counter += 1

        fig, axes = plt.subplots(len(rule_df.columns))
        counter = 0

        for column in rule_df:
            sns.kdeplot(data=feature_df[column], ax=axes[counter], color="blue")
            sns.kdeplot(data=rule_df[column], ax=axes[counter], color="red", alpha=0.6)
            counter += 1

        plt.subplots_adjust(hspace=1.5)
        plt.show()

def visualize_as_table(ruleset):
    for rule in ruleset.rules:
        rule.condition_count




