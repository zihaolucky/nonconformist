#!/usr/bin/env python

"""
Inductive conformal predictors.
"""

# Authors: Henrik Linusson

from __future__ import division

import numpy as np

# -----------------------------------------------------------------------------
# Base inductive conformal predictor
# -----------------------------------------------------------------------------
class BaseIcp(object):
	"""Base class for inductive conformal predictors.
	"""

	__problem_type = None

	@classmethod
	def get_problem_type(cls):
		"""Problem type of conformal predictor.

		Returns
		-------
			problem_type : string or None
				None, 'classification' or 'regression'
		"""
		return cls.__problem_type

	def __init__(self, nc_function):
		self.cal_x, self.cal_y = None, None
		self.nc_function = nc_function

	def fit(self, x, y):
		"""Fit underlying nonconformity scorer.

		Parameters
		----------
		x : numpy array of shape [n_samples, n_features]
			Inputs of examples for fitting the nonconformity scorer.

		y : numpy array of shape [n_samples]
			Outputs of examples for fitting the nonconformity scorer.

		Returns
		-------
		None
		"""
		#TODO: incremental?
		self.nc_function.fit(x, y)

	def calibrate(self, x, y, increment=False):
		"""Calibrate conformal predictor based on underlying nonconformity
		scorer.

		Parameters
		----------
		x : numpy array of shape [n_samples, n_features]
			Inputs of examples for calibrating the conformal predictor.

		y : numpy array of shape [n_samples, n_features]
			Outputs of examples for calibrating the conformal predictor.

		increment : boolean
			If ``True``, performs an incremental recalibration of the conformal
			predictor. The supplied ``x`` and ``y`` are added to the set of
			previously existing calibration examples, and the conformal
			predictor is then calibrated on both the old and new calibration
			examples.

		Returns
		-------
		None
		"""
		# TODO: conditional
		self._calibrate_hook(x, y, increment)
		self._update_calibration_set(x, y, increment)
		self.cal_scores = self.nc_function.calc_nc(self.cal_x, self.cal_y)

	def _calibrate_hook(self, x, y, increment):
		pass

	def _update_calibration_set(self, x, y, increment):
		if increment and self.cal_x is not None and self.cal_y is not None:
			self.cal_x = np.vstack([self.cal_x, x])
			self.cal_y = np.hstack([self.cal_y, y])
		else:
			self.cal_x, self.cal_y = x, y

# -----------------------------------------------------------------------------
# Inductive conformal classifier
# -----------------------------------------------------------------------------
class IcpClassifier(BaseIcp):
	"""Inductive conformal classifier.

	Parameters
	----------
	nc_function : object
		Nonconformity scorer object used to calculate nonconformity of
		calibration examples and test patterns. Should implement ``fit(x, y)``
		and ``calc_nc(x, y)``.

	smoothing : boolean
		Decides whether to use stochastic smoothing of p-values.

	Attributes
	----------

	See also
	--------
	IcpRegressor

	References
	----------

	Examples
	--------
	"""

	__problem_type = 'classification'

	def __init__(self, nc_function, smoothing=True):
		super(IcpClassifier, self).__init__(nc_function)
		self.classes = None
		self.last_p = None
		self.smoothing = smoothing

	def _calibrate_hook(self, x, y, increment=False):
		self._update_classes(y, increment)

	def _update_classes(self, y, increment):
		if self.classes is None or not increment:
			self.classes = np.unique(y)
		else:
			self.classes = np.unique(np.hstack([self.classes, y]))

	def predict(self, x, significance=None):
		"""Predict the output values for a set of input patterns

		Parameters
		----------
		x : numpy array of shape [n_samples, n_features]
			Inputs of patters for which to predict output values.

		significance: float or None
			Significance level (maximum allowed error rate) of predictions.
			Should be a float between 0 and 1. If ``None``, then the p-values
			are output rather than the predictions.

		Returns
		-------
		p : numpy array of shape [n_samples, n_classes]
			If significance is ``None``, then p contains the p-values for each
			sample-class pair; if significance is a float between 0 and 1, then
			p is a boolean array denoting which labels are included in the
			prediction sets.
		"""
		n_test_objects = x.shape[0]
		p = np.zeros((n_test_objects, self.classes.size))
		for i, c in enumerate(self.classes):
			test_class = np.zeros(x.shape[0])
			test_class.fill(c)

			# TODO: maybe calculate p-values using cython or similar
			# TODO: interpolated p-values

			test_nc_scores = self.nc_function.calc_nc(x, test_class)
			n_cal = self.cal_scores.size
			for j, nc in enumerate(test_nc_scores):
				n_ge = np.sum(self.cal_scores >= nc)
				p[j, i] = n_ge / (n_cal + 1)

			if self.smoothing:
				p[:, i] += np.random.uniform(0, 1, n_test_objects) / (n_cal + 1)
			else:
				p[:, i] += 1 / (n_cal + 1)

		if significance:
			return p > significance
		else:
			return p

# -----------------------------------------------------------------------------
# Inductive conformal regressor
# -----------------------------------------------------------------------------
class IcpRegressor(BaseIcp):
	"""Inductive conformal regressor.

	Parameters
	----------

	Attributes
	----------

	See also
	--------
	IcpClassifier

	References
	----------

	Examples
	--------
	"""

	__problem_type = 'regression'

	def __init__(self, nc_function):
		super(IcpRegressor, self).__init__(nc_function)

	def predict(self, x, significance):
		# TODO: interpolated p-values
		return self.nc_function.predict(x, self.cal_scores, significance)