from . import collapser_llcsb
from . import collapser_ll

def get_collapser(criteria):
	if (criteria == 0):
	# For the moment there is only one collapser to choose
 	# low latency & code Size balanced
		return collapser_llcsb.choose_functions_to_collapse
	else :
		return collapser_ll.choose_functions_to_collapse
