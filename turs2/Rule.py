import numpy as np
from turs2.utils_calculating_cl import *
from turs2.nml_regret import *
from functools import partial


def calc_negloglike(p, n):
    return -n * np.sum(np.log2(p[p !=0 ]) * p[p != 0])


def store_grow_info(excl_bi_array, incl_bi_array, icol, cut, cut_option, excl_normalized_gain, incl_normalized_gain):
    return {"excl_bi_array": excl_bi_array, "incl_bi_array": incl_bi_array, "icol": icol, "cut": cut,
            "cut_option": cut_option, "excl_normalized_gain": excl_normalized_gain,
            "incl_normalized_gain": incl_normalized_gain}


def store_grow_info_rulelist(excl_bi_array, icol, cut, cut_option, excl_normalized_gain):
    return {"excl_bi_array": excl_bi_array, "icol": icol, "cut": cut,
            "cut_option": cut_option, "excl_normalized_gain": excl_normalized_gain}


class Rule:
    def __init__(self, indices, indices_excl_overlap, data_info, rule_base, condition_matrix, ruleset,
                 excl_normalized_gain, incl_normalized_gain):
        self.ruleset = ruleset

        self.indices = indices  # corresponds to the original dataset
        self.indices_excl_overlap = indices_excl_overlap  # corresponds to the original
        self.data_info = data_info  # meta data of the original whole dataset

        self.bool_array = self.get_bool_array(self.indices)
        self.bool_array_excl = self.get_bool_array(self.indices_excl_overlap)

        self.coverage = len(self.indices)
        self.coverage_excl = len(self.indices_excl_overlap)

        self.rule_base = rule_base  # the previous level of this rule, i.e., the rule from which "self" is obtained

        self.features = self.data_info.features[indices]
        self.target = self.data_info.target[indices]  # target sub-vector covered by this rule
        self.features_excl_overlap = self.data_info.features[indices_excl_overlap]  # feature rows covered by this rule WITHOUT ruleset's cover
        self.target_excl_overlap = self.data_info.target[indices_excl_overlap]  # target covered by this rule WITHOUT ruleset's cover

        self.nrow, self.ncol = len(self.indices), self.data_info.features.shape[1]  # local nrow and local ncol
        self.nrow_excl, self.ncol_excl = len(self.indices_excl_overlap), self.data_info.features.shape[1]  # local nrow and ncol, excluding ruleset's cover

        self.condition_matrix = condition_matrix
        self.condition_count = (~np.isnan(condition_matrix[0])).astype(int) + (~np.isnan(condition_matrix[1])).astype(int)

        self.prob_excl = self._calc_probs(target=self.target_excl_overlap)
        self.prob = self._calc_probs(target=self.target)
        self.regret_excl = regret(self.nrow_excl, data_info.num_class)
        self.regret = regret(self.nrow, data_info.num_class)

        self.neglog_likelihood_excl = calc_negloglike(p=self.prob_excl, n=self.nrow_excl)

        self.cl_model = self.get_cl_model_indep_data(self.condition_count)
        if self.rule_base is None:
            self.excl_normalized_gain, self.incl_normalized_gain = -np.Inf, -np.Inf
        else:
            self.excl_normalized_gain = excl_normalized_gain
            self.incl_normalized_gain = incl_normalized_gain

    def _calc_probs(self, target):
        return calc_probs(target, num_class=self.data_info.num_class, smoothed=False)
    
    def update_cl_model_indep_data(self, icol, cut_option):
        if cut_option == LEFT_CUT:
            if self.condition_matrix[LEFT_CUT, icol] == 1:
                return self.cl_model
            else:
                condition_count = np.array(self.condition_count)
                condition_count[icol] = 1
                return self.get_cl_model_indep_data(condition_count)
        else:
            if self.condition_matrix[RIGHT_CUT, icol] == 1:
                return self.cl_model
            else:
                condition_count = np.array(self.condition_count)
                condition_count[icol] += 1
                return self.get_cl_model_indep_data(condition_count)

    def get_cl_model_indep_data(self, condition_count):
        num_variables = np.count_nonzero(condition_count)
        if num_variables == 0:
            return 0
        else:
            l_num_variables = self.data_info.cl_model["l_number_of_variables"][num_variables - 1]
            l_which_variables = self.data_info.cl_model["l_which_variables"][num_variables - 1]
            l_cuts = np.sum(self.data_info.cl_model["l_cut"][0][condition_count == 1]) + \
                np.sum(self.data_info.cl_model["l_cut"][1][condition_count == 2])
            return l_num_variables + l_which_variables + l_cuts  # TODO I NEED TO ENCODE THE NUMBER OF RULES?

    def get_bool_array(self, indices):
        bool_array = np.zeros(self.data_info.nrow, dtype=bool)
        bool_array[indices] = True
        return bool_array

    def grow_rulelist(self):
        candidate_cuts = self.data_info.candidate_cuts
        excl_best_normalized_gain = -np.Inf
        for icol in range(self.ncol):
            candidate_cuts_selector = (candidate_cuts[icol] < np.max(self.features_excl_overlap[:, icol])) & \
                                      (candidate_cuts[icol] >= np.min(self.features_excl_overlap[:, icol]))
            candidate_cuts_icol = candidate_cuts[icol][candidate_cuts_selector]

            for i, cut in enumerate(candidate_cuts_icol):
                excl_left_bi_array = (self.features_excl_overlap[:, icol] < cut)
                excl_right_bi_array = ~excl_left_bi_array

                excl_left_normalized_gain, cl_model, two_total_cl_left_excl = self.calculate_excl_gain(bi_array=excl_left_bi_array, icol=icol, cut_option=LEFT_CUT, cl_model=None)
                excl_right_normalized_gain, cl_model, two_total_cl_right_excl = self.calculate_excl_gain(bi_array=excl_right_bi_array, icol=icol, cut_option=LEFT_CUT, cl_model=cl_model)

                if excl_left_normalized_gain > excl_best_normalized_gain and excl_left_normalized_gain > excl_right_normalized_gain:
                    best_excl_grow_info = store_grow_info_rulelist(excl_left_bi_array, icol, cut, LEFT_CUT, excl_left_normalized_gain)
                    excl_best_normalized_gain = excl_left_normalized_gain
                elif excl_right_normalized_gain > excl_best_normalized_gain and excl_right_normalized_gain > excl_left_normalized_gain:
                    best_excl_grow_info = store_grow_info_rulelist(excl_right_bi_array, icol, cut, RIGHT_CUT, excl_right_normalized_gain)
                    excl_best_normalized_gain = excl_right_normalized_gain
                else:
                    pass
        excl_grow_res = self.make_rule_from_grow_info_rulelist(best_excl_grow_info)
        return excl_grow_res

    def grow(self):
        candidate_cuts = self.data_info.candidate_cuts
        excl_best_normalized_gain, incl_best_normalized_gain = -np.Inf, -np.Inf
        for icol in range(self.ncol):
            if self.rule_base is None:
                candidate_cuts_selector = (candidate_cuts[icol] < np.max(self.features_excl_overlap[:, icol])) & \
                                          (candidate_cuts[icol] >= np.min(self.features_excl_overlap[:, icol]))
                candidate_cuts_icol = candidate_cuts[icol][candidate_cuts_selector]
            else:
                candidate_cuts_icol = candidate_cuts[icol]
            for i, cut in enumerate(candidate_cuts_icol):
                excl_left_bi_array = (self.features_excl_overlap[:, icol] < cut)
                excl_right_bi_array = ~excl_left_bi_array

                excl_left_normalized_gain, cl_model, two_total_cl_left_excl = self.calculate_excl_gain(bi_array=excl_left_bi_array, icol=icol, cut_option=LEFT_CUT, cl_model=None)
                excl_right_normalized_gain, cl_model, two_total_cl_right_excl = self.calculate_excl_gain(bi_array=excl_right_bi_array, icol=icol, cut_option=LEFT_CUT, cl_model=cl_model)

                incl_left_bi_array = (self.features[:, icol] < cut)
                incl_right_bi_array = ~incl_left_bi_array

                incl_left_normalized_gain, cl_model, total_negloglike = self.calculate_incl_gain(incl_bi_array=incl_left_bi_array, excl_bi_array=excl_left_bi_array, icol=icol, cut_option=LEFT_CUT, cl_model=cl_model)
                incl_right_normalized_gain, cl_model, total_negloglike = self.calculate_incl_gain(incl_bi_array=incl_right_bi_array, excl_bi_array=excl_right_bi_array, icol=icol, cut_option=RIGHT_CUT, cl_model=cl_model)

                if excl_left_normalized_gain > excl_best_normalized_gain and excl_left_normalized_gain > excl_right_normalized_gain:
                    best_excl_grow_info = store_grow_info(excl_left_bi_array, incl_left_bi_array, icol, cut, LEFT_CUT, excl_left_normalized_gain, incl_left_normalized_gain)
                    excl_best_normalized_gain = excl_left_normalized_gain
                elif excl_right_normalized_gain > excl_best_normalized_gain and excl_right_normalized_gain > excl_left_normalized_gain:
                    best_excl_grow_info = store_grow_info(excl_right_bi_array, incl_right_bi_array, icol, cut, RIGHT_CUT, excl_right_normalized_gain, incl_right_normalized_gain)
                    excl_best_normalized_gain = excl_right_normalized_gain
                else:
                    pass

                if incl_left_normalized_gain > incl_best_normalized_gain and incl_left_normalized_gain > incl_right_normalized_gain:
                    best_incl_grow_info = store_grow_info(excl_left_bi_array, incl_left_bi_array, icol, cut, LEFT_CUT, excl_left_normalized_gain, incl_left_normalized_gain)
                    incl_best_normalized_gain = incl_left_normalized_gain
                elif incl_right_normalized_gain > incl_best_normalized_gain and incl_right_normalized_gain > incl_left_normalized_gain:
                    best_incl_grow_info = store_grow_info(excl_right_bi_array, incl_right_bi_array, icol, cut, RIGHT_CUT, excl_right_normalized_gain, incl_right_normalized_gain)
                    incl_best_normalized_gain = incl_right_normalized_gain
                else:
                    pass
        excl_grow_res = self.make_rule_from_grow_info(best_excl_grow_info)
        incl_grow_res = self.make_rule_from_grow_info(best_incl_grow_info)

        return [excl_grow_res, incl_grow_res]

    def make_rule_from_grow_info(self, grow_info):
        indices = self.indices[grow_info["incl_bi_array"]]
        indices_excl_overlap = self.indices_excl_overlap[grow_info["excl_bi_array"]]

        condition_matrix = np.array(self.condition_matrix)
        condition_matrix[grow_info["cut_option"], grow_info["icol"]] = grow_info["cut"]
        rule = Rule(indices=indices, indices_excl_overlap=indices_excl_overlap, data_info=self.data_info,
                    rule_base=self, condition_matrix=condition_matrix, ruleset=self.ruleset,
                    excl_normalized_gain=grow_info["excl_normalized_gain"],
                    incl_normalized_gain=grow_info["incl_normalized_gain"])  # TODO: this is wrong
        return rule

    def make_rule_from_grow_info_rulelist(self, grow_info):
        indices_excl_overlap = self.indices_excl_overlap[grow_info["excl_bi_array"]]
        indices = indices_excl_overlap

        condition_matrix = np.array(self.condition_matrix)
        condition_matrix[grow_info["cut_option"], grow_info["icol"]] = grow_info["cut"]
        rule = Rule(indices=indices, indices_excl_overlap=indices_excl_overlap, data_info=self.data_info,
                    rule_base=self, condition_matrix=condition_matrix, ruleset=self.ruleset,
                    excl_normalized_gain=grow_info["excl_normalized_gain"],
                    incl_normalized_gain=grow_info["excl_normalized_gain"])  # TODO: this is wrong
        return rule

    def calculate_incl_gain(self, incl_bi_array, excl_bi_array, icol, cut_option, cl_model=None):
        excl_coverage, incl_coverage = np.count_nonzero(excl_bi_array), np.count_nonzero(incl_bi_array)

        if cl_model is None:
            cl_model = self.update_cl_model_indep_data(icol, cut_option)

        p_excl = self._calc_probs(self.target_excl_overlap[excl_bi_array])
        p_incl = self._calc_probs(self.target[incl_bi_array])

        modelling_groups = self.ruleset.modelling_groups
        both_negloglike = np.zeros(len(modelling_groups), dtype=float)
        for i, modeling_group in enumerate(modelling_groups):
            # Note: both_negloglike[i] represents negloglike(modelling_group \setdiff rule) + negloglike(modelling_Group, rule) # noqa
            both_negloglike[i] = modeling_group.evaluate_rule_approximate(indices=self.indices[incl_bi_array])  # TODO: implement this later in the ModellingGroup class.

        non_overlapping_negloglike = -excl_coverage * np.sum(p_excl * np.log2(p_incl))
        total_negloglike = non_overlapping_negloglike + np.sum(both_negloglike)

        # NOTE that for absolute gain: the regret for all rules already in the rule set will cancel out
        absolute_gain = self.ruleset.total_negloglike - total_negloglike - regret(incl_coverage, self.data_info.num_class) - cl_model # TODO: implement this later
        normalized_gain = absolute_gain / excl_coverage

        return [normalized_gain, cl_model, total_negloglike]

    def calculate_excl_gain(self, bi_array, icol, cut_option, cl_model):
        if cl_model is None:
            cl_model = self.update_cl_model_indep_data(icol, cut_option)

        coverage = np.count_nonzero(bi_array)

        if coverage == 0:
            return [-np.Inf, cl_model, self.ruleset.elserule_total_cl + cl_model]

        p = self._calc_probs(self.target_excl_overlap[bi_array])
        negloglike = calc_negloglike(p, coverage)

        else_bool = np.zeros(self.data_info.nrow, dtype=bool)
        else_bool[self.ruleset.uncovered_indices] = True
        else_bool[self.indices_excl_overlap[bi_array]] = False
        else_coverage = np.count_nonzero(else_bool)

        else_p = self._calc_probs(self.data_info.target[else_bool])
        else_negloglike = calc_negloglike(else_p, else_coverage)

        both_negloglike = negloglike + else_negloglike
        both_regret = regret(else_coverage, self.data_info.num_class) + regret(coverage, self.data_info.num_class)

        both_total_cl = both_negloglike + both_regret + cl_model  # "Both" is to emphasize that we ignore the rules already added to the ruleset.

        normalized_gain = (self.ruleset.elserule_total_cl - both_total_cl) / coverage  # TODO: get the elserule_total_cl
        return [normalized_gain, cl_model, both_total_cl]