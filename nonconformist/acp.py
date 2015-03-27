#!/usr/bin/env python

"""
Aggregated conformal predictors
"""

# Authors: Henrik Linusson

import numpy as np
from sklearn.cross_validation import KFold, StratifiedKFold
from sklearn.cross_validation import ShuffleSplit, StratifiedShuffleSplit

# -----------------------------------------------------------------------------
# Sampling strategies
# -----------------------------------------------------------------------------
class BootstrapSampler(object):
	"""Bootstrap sampler.

	Parameters
	----------

	Attributes
	----------

	See also
	--------

	References
	----------

	Examples
	--------
	"""
	def gen_samples(self, x, y, n_samples, problem_type):
		for i in range(n_samples):
			idx = np.array(range(y.size))
			train = np.random.choice(y.size, y.size, replace=True)
			cal_mask = np.array(np.ones(idx.size), dtype=bool)
			for j in train:
				cal_mask[j] = False
			cal = idx[cal_mask]

			yield train, cal

class CrossSampler(object):
	"""Cross-fold sampler.

	Parameters
	----------

	Attributes
	----------

	See also
	--------

	References
	----------

	Examples
	--------
	"""
	def gen_samples(self, x, y, n_samples, problem_type):
		if problem_type == 'classification':
			folds = StratifiedKFold(y, n_folds=n_samples)
		else:
			folds = KFold(y.size, n_folds=n_samples)
		for train, cal in folds:
			yield train, cal

class RandomSubSampler(object):
	"""Random subsample sampler.

	Parameters
	----------

	Attributes
	----------

	See also
	--------

	References
	----------

	Examples
	--------
	"""
	def __init__(self, calibration_portion=0.3):
		self.cal_portion = calibration_portion

	def gen_samples(self, x, y, n_samples, problem_type):
		if problem_type == 'classification':
			splits = StratifiedShuffleSplit(y,
			                                n_iter=n_samples,
			                                test_size=self.cal_portion)
		else:
			splits = ShuffleSplit(y.size,
			                      n_iter=n_samples,
			                      test_size=self.cal_portion)

		for train, cal in splits:
			yield train, cal

# -----------------------------------------------------------------------------
# Conformal ensemble
# -----------------------------------------------------------------------------
class AggregatedCp(object):
	"""Aggregated conformal predictor.

	Parameters
	----------

	Attributes
	----------

	See also
	--------

	References
	----------

	Examples
	--------
	"""
	def __init__(self,
	             cp_class,
	             nc_class,
	             sampler=BootstrapSampler,
	             aggregation_func=None,
	             nc_class_params=None,
	             n_models=10):
		self.predictors = []
		self.n_models = n_models
		self.cp_class = cp_class
		self.nc_class = nc_class
		self.nc_class_params = nc_class_params if nc_class_params else {}
		self.sampler = sampler()

		if aggregation_func is not None:
			self.p_agg_func = aggregation_func
		else:
			self.p_agg_func = lambda x: np.mean(x, axis=2)

	def fit(self, x, y):
		self.predictors = []
		idx = np.random.permutation(y.size)
		x, y = x[idx, :], y[idx]
		samples = self.sampler.gen_samples(x,
		                                   y,
		                                   self.n_models,
		                                   self.cp_class.get_problem_type())
		for train, cal in samples:
			predictor = self.cp_class(self.nc_class(**self.nc_class_params))
			predictor.fit(x[train, :], y[train])
			predictor.calibrate(x[cal, :], y[cal])
			self.predictors.append(predictor)

	def predict(self, x, significance=None):
		is_regression = self.cp_class.get_problem_type() == 'regression'

		f = lambda p, x: p.predict(x, significance if is_regression else None)
		predictions = np.dstack([f(p, x) for p in self.predictors])
		predictions = self.p_agg_func(predictions)

		if significance and not is_regression:
			return predictions >= significance
		else:
			return predictions