# http://stackoverflow.com/questions/2343535/easiest-way-to-serialize-a-simple-class-object-with-simplejson
import json

def toJSON(obj):
	"""Represent instance of a class as JSON.
	Arguments:
	obj -- any object
	Return:
	String that reprent JSON-encoded object.
	"""
	def serialize(obj):
		"""Recursively walk object's hierarchy."""
		if isinstance(obj, (bool, int, long, float, basestring)):
		  return obj
		elif isinstance(obj, dict):
		  obj = obj.copy()
		  for key in obj:
		    obj[key] = serialize(obj[key])
		  return obj
		elif isinstance(obj, list):
		  return [serialize(item) for item in obj]
		elif isinstance(obj, tuple):
		  return tuple(serialize([item for item in obj]))
		elif hasattr(obj, '__dict__'):
		  return serialize(obj.__dict__)
		else:
		  return repr(obj) # Don't know how to handle, convert to string
	return json.dumps(serialize(obj))

def parseJSON(jsonstr):
	jsonstr = jsonstr.replace("true","True").replace("false","False")
	return eval(jsonstr)
