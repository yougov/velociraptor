# copied from jaraco.compat:py26compat
from __future__ import division

def total_seconds(td):
	"""
	Python 2.7 adds a total_seconds method to timedelta objects.
	See http://docs.python.org/library/datetime.html#datetime.timedelta.total_seconds
	"""
	try:
		result = td.total_seconds()
	except AttributeError:
		result = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
	return result
