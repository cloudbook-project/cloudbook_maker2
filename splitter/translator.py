import logging
import os
import ast
import astunparse
import re

function_invocations = []
translated_functions = {}
function_list = []
file = ""
aux_config_dict = {}
#global vars to generate code in every global declaration inside function
actual_fun_name = ""
actual_fun_fname = ""
du_dest = ""
fun_dest = ""

return_fun = False

class invocation_scanner(ast.NodeVisitor):

	def visit_Call(self, node):
		global function_invocations
		global function_list
		if isinstance(node.func, ast.Name):
				if file+"."+node.func.id in function_list: #invocacion tipo fun()
					logging.debug("		la invocacion %s esta en la lista", file+"."+node.func.id)
					function_invocations.append(node)
				else: #esta la fun en otro fichero
					aux_func_list = [] #function list without the complete path
					for i in function_list:
						aux_func_list.append(i[i.rfind(".")+1:len(i)])
					apparitions = aux_func_list.count(node.func.id) #apparitions of function in program
					if apparitions == 1:
						#add complete_path_name
						for i in function_list:
							if i[i.rfind(".")+1:len(i)] == node.func.id:
								function_invocations.append(node)
								break
					elif apparitions > 1:
						logging.error("		ERROR: too many functions with same name")
		elif isinstance(node.func,ast.Attribute):
			if isinstance(node.func.value,ast.Attribute):
				logging.error("		ERROR: more than one abstraction level on call, in progress")
			elif isinstance(node.func.value,ast.Name): #is global_var.fun()
				if file+"."+node.func.value.id in function_list:
					function_invocations.append(node)
				else: #not global var, is imported_function.fun()
					aux_func_list = [] #function list without the complete path
					for i in function_list:
						aux_func_list.append(i[i.rfind(".")+1:len(i)])
					apparitions = aux_func_list.count(node.func.attr) #apparitions of function in program
					if apparitions == 1:
						#add complete_path_name
						for i in function_list:
							if i[i.rfind(".")+1:len(i)] == node.func.attr:
								function_invocations.append(node)
								break
					elif apparitions > 1:
						logging.error("		ERROR: too many functions with same name")
			elif isinstance(node.func.value,ast.Subscript):
				#Es un elemento de diccionario o de una lista
				logging.debug("		La invocacion es de tipo Subscript de un nivel %s",node.func.value.value.id)
				if file+"."+node.func.value.value.id in function_list: #global_var[x].fun()
					function_invocations.append(node)
				else:
					logging.error("		The subscript is not from global var in lineno %s", node.lineno)
				#para ampliar en el futuro
				'''aux_node = node.func.value
				veces=1
				while isinstance(aux_node.value,ast.Subscript):
					veces+=1
					aux_node = aux_node.value
				logging.debug("Madre mia, %s",veces)'''

			else:
				logging.error("		ERROR: Unknown type of invocation in %s",node.lineno)


class RewriteInvocationName(ast.NodeTransformer):

	def visit_Call(self, node):
		global file
		global aux_config_dict
		global function_list
		global actual_fun_name
		global actual_fun_fname
		global du_dest
		global fun_dest

		global_var_modification = False
		global_var_subscript = False
		subscript_index = []
		old_node_node = node
		old_node = astunparse.unparse(node)
		parallel_invocation = False

		if isinstance(node.func, ast.Name):
			invoked_fun_name = node.func.id
			node.func.id = "invoker"
				
		elif isinstance(node.func,ast.Attribute):
			if isinstance(node.func.value,ast.Name):
				if file+"."+node.func.value.id in function_list: #global_var.fun() , keep global var
					invoked_fun_name = node.func.value.id
					global_var_modification = True
					global_var_name = node.func.value.id
					global_var_fun = node.func.attr
					node.func = ast.Name()
					node.func.id = "invoker"
					global_var_op = ast.Constant()
					#node.args = []
				else: #file.fun()	keep fun()
					invoked_fun_name = node.func.attr
					node.func = ast.Name()
					node.func.id = "invoker"
			elif isinstance(node.func.value,ast.Subscript):
				invoked_fun_name = node.func.value.value.id
				global_var_modification = True	
				global_var_subscript = True
				subscript_index.append(node.func.value.slice.value)
				global_var_name = node.func.value.value.id
				global_var_fun = node.func.attr
				global_var_slice = node.func.value.slice
				node.func = ast.Name()
				node.func.id = "invoker"

		#ya tengo el nombre de la funcion a invocar, ahora a hacer el invoker
		invoked_du = get_invoked_du(invoked_fun_name)
		invoked_fun = get_invoked_fun(invoked_fun_name)
		invoker_fun = actual_fun_fname

		logging.debug("			%s ==> invoker_%s",node.func.id,translated_functions[file+"."+invoked_fun_name])
		arg_list = get_args_list(node)
		kwargs_dict = get_kwargs_dict(node)

		if file+"."+invoked_fun_name in aux_config_dict["pragmas"]["local"]: #si es local solo cambio nombre, no traduzco
			node.func.id = translated_functions[file+"."+invoked_fun_name]
			new_node = node
			try:
				new_node.func.id = translated_functions[file+"."+invoked_fun_name]
			except:
				new_node.func.value = translated_functions[file+"."+invoked_fun_name]
			return

		if file+"."+invoked_fun_name in aux_config_dict["pragmas"]["parallel"]: #si es paralela escribo el thread counter
			parallel_invocation = True


		if global_var_modification == True:
			new_list = ast.List()
			new_list.ctx = ast.Load()
			new_list.elts = []
			global_var_version = ast.Constant()
			global_var_version.value = 0
			global_var_version.kind = None
			new_list.elts.append(global_var_version)
			global_var_op = ast.Constant()
			global_var_op.value = "."+global_var_fun
			global_var_op.kind = None
			new_list.elts.append(global_var_op)
			for arg in node.args:
				new_list.elts.append(arg)
			arg_list = new_list

		if global_var_subscript:
			index_const = ast.Constant()
			index_const.value = "index"
			index_const.kind = None
			kwargs_dict.keys.append(index_const)
			list_index = ast.List()
			list_index.ctx = ast.Load()
			list_index.elts = []
			for i in subscript_index:
				list_index.elts.append(i)
			kwargs_dict.values.append(list_index)


		new_dict = ast.Dict()
		new_dict.keys = []
		new_dict.values = []
		for i in (("invoked_du",invoked_du), ("invoked_function",invoked_fun), ("invoker_function",invoker_fun)):
			print(i)
			new_key = ast.Constant()
			new_key.value = i[0]#deberia ser invoked_du, fun y invokerfun
			new_key.kind = None
			new_value = ast.Constant()
			new_value.value = i[1]
			new_value.kind = None
			new_dict.keys.append(new_key)
			new_dict.values.append(new_value)
		
		#creo diccionario de parametros
		params_dict = ast.Dict()
		params_dict.keys = []
		params_dict.values = []
		#creo clave args que meto en el diccionario de parametros
		new_key = ast.Constant()
		new_key.value = "args"
		new_key.kind = None
		new_value = arg_list
		params_dict.keys.append(new_key)
		params_dict.values.append(new_value)
		#todo, crear la key kwargs y meter el dict kwargs
		new_key = ast.Constant()
		new_key.value = "kwargs"
		new_key.kind = None
		new_value = kwargs_dict
		params_dict.keys.append(new_key)
		params_dict.values.append(new_value)
		#Creo Campo params en el diccionario de la invocacion y lo meto
		new_key = ast.Constant()
		new_key.value = 'params'
		new_key.kind = None
		new_value = params_dict
		new_dict.keys.append(new_key)
		new_dict.values.append(new_value)

		node.args = []
		node.args.append(new_dict)
		node.func.id = 'invoker' 
		'''new_node = ast.Call()
		new_node.func = ast.Name()
		new_node.func.ctx = ast.Load()
		new_node.args = []
		new_node.args.append(new_dict)
		new_node.func.id = 'invoker'
		new_node.keywords = [] '''

		if global_var_modification:
			node.func.id = old_node+" "*4*node.col_offset+'invoker'
		if parallel_invocation:
			node.func.id = "invoker({'invoked_du': 'du_0', 'invoked_function': 'thread_counter', 'invoker_function': 'thread_counter', 'params': {'args': ['++'], 'kwargs': {}}})\n"+" "*4*node.col_offset+'invoker'
			
		#node.func.id = old_node+"\n"+'invoker'

class RewriteAssginationsAsInvocations(ast.NodeTransformer):

	def visit_Assign(self, node):
		#logging.debug("ASIGNACION: %s",astunparse.unparse(node))
		global file
		old_node = astunparse.unparse(node)
		clean_file_name = file+"."
		global_var_names = []
		subscript_index = []
		offset = node.col_offset
		old_node = "\t"*offset+old_node

		for var in node.targets:
			if isinstance(var,ast.Name):
				if clean_file_name+var.id in function_list:
					#invocation_list.append({"type":"global","name": clean_file_name+var.id,"line": node.lineno, "offset":node.col_offset, "value": 1})
					global_var_names.append(var.id)
					logging.debug("Assign %s",clean_file_name+var.id)
				else:
					return node
			elif isinstance(var,ast.Tuple):
				for i in var.elts:
					if clean_file_name+i.id in function_list:
						#invocation_list.append({"type":"global","name": clean_file_name+i.id,"line": node.lineno, "offset":node.col_offset, "value": 1})
						global_var_names.append(i.id)
						logging.debug("Assign %s",clean_file_name+var.id)
					else:
						return node
			elif isinstance(var,ast.Subscript):
				#comprobar que este en la lista de funciones
				if isinstance(var.value,ast.Name):
					if clean_file_name+var.value.id in function_list:
						#invocation_list.append({"type":"global","name": clean_file_name+var.value.id,"line": node.lineno, "offset":node.col_offset, "value": 1})
						global_var_names.append(var.value.id)
						#logging.debug("A VER: %s",var.slice.value.id)
						subscript_index.append(var.slice.value)
						logging.debug("Assign %s",clean_file_name+var.value.id)
					else:
						return node
				else:
					#logging.error("ERROR left part of subscript assignation %s not included in line %s", type(var), node.lineno)
					return node
			else:
				#logging.error("ERROR left part of assignation %s not included in line %s", type(var), node.lineno)
				return node
		logging.debug("ASIGNACIONES: %s",global_var_names)

		for global_var_name in global_var_names:
			invoked_du = get_invoked_du(global_var_name)
			invoked_fun = get_invoked_fun(global_var_name)
			invoker_fun = aux_config_dict["function_translated"][clean_file_name+global_var_name]

			new_dict = ast.Dict()
			new_dict.keys = []
			new_dict.values = []
			for i in (("invoked_du",invoked_du), ("invoked_function",invoked_fun), ("invoker_function",invoker_fun)):
				new_key = ast.Constant()
				new_key.value = i[0]#deberia ser invoked_du, fun y invokerfun
				new_key.kind = None
				new_value = ast.Constant()
				new_value.value = i[1]
				new_value.kind = None
				new_dict.keys.append(new_key)
				new_dict.values.append(new_value)

			#creao arg_list
			new_list = ast.List()
			new_list.ctx = ast.Load()
			new_list.elts = []
			global_var_version = ast.Constant()
			global_var_version.value = 0
			global_var_version.kind = None
			new_list.elts.append(global_var_version)
			global_var_op = ast.Constant()
			global_var_op.value = "="
			global_var_op.kind = None
			new_list.elts.append(global_var_op)
			new_list.elts.append(node.value)
			arg_list = new_list
			#creo kwargs_dict
			kwargs_dict = ast.Dict()
			kwargs_dict.keys = []
			kwargs_dict.values = []
			index_const = ast.Constant()
			index_const.value = "index"
			index_const.kind = None
			kwargs_dict.keys.append(index_const)
			list_index = ast.List()
			list_index.ctx = ast.Load()
			list_index.elts = []
			for i in subscript_index:
				list_index.elts.append(i)
			kwargs_dict.values.append(list_index)
			#creo diccionario de parametros
			params_dict = ast.Dict()
			params_dict.keys = []
			params_dict.values = []
			#creo clave args que meto en el diccionario de parametros
			new_key = ast.Constant()
			new_key.value = "args"
			new_key.kind = None
			new_value = arg_list
			params_dict.keys.append(new_key)
			params_dict.values.append(new_value)
			#todo, crear la key kwargs y meter el dict kwargs
			new_key = ast.Constant()
			new_key.value = "kwargs"
			new_key.kind = None
			new_value = kwargs_dict
			params_dict.keys.append(new_key)
			params_dict.values.append(new_value)
			#Creo Campo params en el diccionario de la invocacion y lo meto
			new_key = ast.Constant()
			new_key.value = 'params'
			new_key.kind = None
			new_value = params_dict
			new_dict.keys.append(new_key)
			new_dict.values.append(new_value)

			new_node = ast.Call()
			new_node.func = ast.Name()
			new_node.func.id = "\n"+" "*(4*offset)+'invoker'
			new_node.func.ctx = ast.Load()
			new_node.args = []
			new_node.args.append(new_dict)
			new_node.keywords = []

			return node,new_node
			#return ast.copy_location(new_node,node)
			#return node,ast.fix_missing_locations(new_node)

	'''def visit_AugAssign(self, node):
		if isinstance(node.target,ast.Name):
			if clean_file_name+node.target.id in function_list:
				invocation_list.append({"type":"global","name": clean_file_name+node.target.id,"line": node.lineno, "offset":node.col_offset, "value": 1})
		else:
			logging.error("ERROR left part of augmented assgination not included in line %s", node.lineno)'''

class RewriteFunctionName(ast.NodeTransformer):

    def visit_FunctionDef(self, node):
    	global file
    	##print("	",node.id,"==>",translated_functions[file+"."+node.id])
    	#node.id = translated_functions[file+"."+node.id]
    	node.name = translated_functions[file+"."+node.name]

class RewriteParallelFunctionName(ast.NodeTransformer):

    def visit_FunctionDef(self, node):
    	global file
    	##print("	",node.id,"==>",translated_functions[file+"."+node.id])
    	#node.id = translated_functions[file+"."+node.id]
    	node.name = "parallel_"+node.name

class RewriteGlobalDeclaration(ast.NodeTransformer):

    def visit_Global(self, node):
    	global file
    	global actual_fun_name
    	global actual_fun_fname
    	global aux_config_dict
    	##print("	",node.id,"==>",translated_functions[file+"."+node.id])
    	#node.id = translated_functions[file+"."+node.id]
    	global_nodes = []
    	for global_var in node.names:    		
    		#print("Miro la global",global_var)
    		#Es complejo, coge cada "global algo", y lo cambia por el código de cargar la variable. Uso el config dict como aux, porque no puedo pasarlo como parametro
    		if global_var in aux_config_dict["global_vars"]["global"]:
    			global_nodes.append(create_global_declaration_node(global_var,actual_fun_name,actual_fun_fname, aux_config_dict))
    		else:
    			return node
    	return global_nodes 		


def tranlateInvocations(config_dict):
	logging.debug("<<<Enter in translate invocations")
	global translated_functions
	global function_list
	global file
	global function_invocations
	global aux_config_dict
	global actual_fun_name
	global actual_fun_fname

	translated_functions = config_dict["function_translated"]
	function_list = config_dict["function_list"]
	aux_config_dict = config_dict

	for function in config_dict["program_data"]["functions"]:
		#get invocations inside functions
		file = function[:function.rfind(".")]
		actual_fun_name = function
		actual_fun_fname = translated_functions[function]
		function_node = config_dict["program_data"]["functions"][function]
		logging.debug("	Checking function %s", function)
		invocation_scanner().visit(function_node)
		for invocation in function_invocations:
			logging.debug("		Vamos a traducir %s:%s",invocation,astunparse.unparse(invocation))
			RewriteInvocationName().visit(invocation)
		RewriteAssginationsAsInvocations().visit(function_node)
		ast.fix_missing_locations(function_node)
		logging.debug("	Invocations translated")
		#logging.debug("		%s",astunparse.unparse(config_dict["program_data"]["functions"][function]))
		function_invocations = []
		#traduccion de declaracionde variables globales
		translateGlobalDeclaration(config_dict,file,function,function_node)
		

def translateParallelFunctionName(node):
	RewriteParallelFunctionName().visit(node)

def translateFunctionNames(config_dict):
	global file

	for function in config_dict["program_data"]["functions"]:
		file = function[:function.rfind(".")]
		RewriteFunctionName().visit(config_dict["program_data"]["functions"][function])

def translateGlobalDeclaration(config_dict,file,function,function_node):
	global actual_fun_name
	global actual_fun_fname
	global translated_functions
	global du_dest
	global fun_dest
	global aux_config_dict

	aux_config_dict = config_dict

	actual_fun_name = function
	actual_fun_fname = translated_functions[function]
	#guardamos el nombre de la funcion acualen la que estamos y hacemos el visit
	RewriteGlobalDeclaration().visit(function_node)

def create_global_declaration_node(global_var,actual_fun_name,actual_fun_fname, config_dict):
	print("voy a escribir el codigo de la declaracion global")
	global du_dest
	global fun_dest
	#busco la du destino, la funcion destino y todo eso
	for du in config_dict["dus"]:
		for fun in config_dict["dus"][du]:
			if fun[fun.rfind(".")+1:] == global_var:
				du_dest = du
	#du_dest = [du_dest]

	for fun in config_dict["function_translated"]:
		if fun[fun.rfind(".")+1:] == global_var:
			print("la encuentro")
			fun_dest = config_dict["function_translated"][fun]

	print("fun_dest",fun_dest)
	
	#invocation_params = "{'invoked_du':\'"+ du_dest+"\','invoked_function':\'"+fun_dest+"\','invoker_function':\'"+ actual_fun_fname+"\','params': {'args':["+'''str('''+actual_fun_fname+'''.ver_'''+global_var+'''),"None"'''+"],'kwargs':{}}}"
	invocation_params = "{'invoked_du':\'"+ du_dest+"\','invoked_function':\'"+fun_dest+"\','invoker_function':\'"+ actual_fun_fname+"\','params': {'args':["+''+actual_fun_fname+'''.ver_'''+global_var+''',"None"'''+"],'kwargs':{}}}"

	code = '''
if not hasattr('''+actual_fun_fname+''', '''+'"'+global_var+'"'+'''):
	'''+actual_fun_fname+"."+global_var+''' = None
if not hasattr('''+actual_fun_fname+''', '''+'"ver_'+global_var+'"'+'''):
	'''+actual_fun_fname+".ver_"+global_var+''' = 0

aux_'''+global_var+''',aux_ver = invoker('''+invocation_params+''')
if aux_'''+global_var+''' != "None":
	'''+actual_fun_fname+"."+global_var+''' = aux_'''+global_var+'''
'''+global_var+''' = '''+actual_fun_fname+"."+global_var+'''
'''+actual_fun_fname+".ver_"+global_var+''' = aux_ver
ver_'''+global_var+''' = '''+actual_fun_fname+".ver_"+global_var+'''
'''
	#print("la convierto en:\n",code)
	du_dest = ""
	fun_dest = ""
	return ast.parse(code)

def get_invoked_du(fun_name):
	for du in aux_config_dict["dus"]:
		for fun in aux_config_dict["dus"][du]:
			if fun[fun.rfind(".")+1:] == fun_name:
				du_dest = du
	return du_dest

def get_invoked_fun(fun_name):
	for fun in aux_config_dict["function_translated"]:
		if fun[fun.rfind(".")+1:] == fun_name:
			fun_dest = aux_config_dict["function_translated"][fun]
	return fun_dest

def get_args_list(node):
	args_list = ast.List()
	args_list.ctx = ast.Load()
	args_list.elts = []
	for arg in node.args:
		args_list.elts.append(arg)
	return args_list

def get_kwargs_dict(node):
	kwargs_dict = ast.Dict()
	kwargs_dict.keys = []
	kwargs_dict.values = []
	for arg in node.keywords:
		kwargs.dict.keys.append(arg.arg)
		kwargs.dict.values.append(arg.value)
	return kwargs_dict

class visitReturn(ast.NodeVisitor):

	def visit_Return(self, node):
		global return_fun

		logging.debug("Return node: %s",astunparse.unparse(node))
		return_fun = True

class RewriteReturnValue(ast.NodeTransformer):

	def visit_FunctionDef(self, node):
		global aux_config_dict

		translate = False

		logging.debug("		Func name: %s tiene return",(node.name))
		#Si no es local
		if node.name not in aux_config_dict["pragmas"]["local"]:
			translate = True
		for i in aux_config_dict["pragmas"]["local"]:
			if aux_config_dict["function_translated"][i] == node.name:
				translate = False
		if translate == True:
			logging.debug(ast.dump(node.body[-1]))
			for i in node.body:
				if isinstance(i,ast.Return):
					logging.debug("		Return en %s",node.lineno)
					#return_node = ast.Return()
					#return_node.ctx = ast.Load()
					if i.value == None:
						new_value = ast.Constant()
						new_value.value="Cloudbook_done"
						new_value.kind = None
					else:
						new_value = i.value
					i.value = ast.Call()
					i.value.func = ast.Attribute()
					i.value.args = []
					i.value.args.append(new_value)
					i.value.keywords = []
					i.value.func.value = ast.Name()
					i.value.func.value.id = 'json'
					i.value.func.value.ctx = ast.Load()
					i.value.func.attr = 'dumps'
					i.value.func.ctx = ast.Load()
					logging.debug("Queda asi",astunparse.unparse(i))
					#i = return_node
		return node

class AddReturnValue(ast.NodeTransformer):

	def visit_FunctionDef(self, node):
		logging.debug("		Func name: %s  no tiene return",(node.name))
		return_fun = False
		return_node = ast.Return()
		return_node.value = ast.Call()
		return_node.value.func = ast.Attribute()
		return_node.value.args = []
		cloudbook_done = ast.Constant()
		cloudbook_done.value = "Cloudbook: Done"
		cloudbook_done.kind = None
		return_node.value.args.append(cloudbook_done)
		return_node.value.keywords = []
		return_node.value.func.value = ast.Name()
		return_node.value.func.value.id = 'json'
		return_node.value.func.value.ctx = ast.Load()
		return_node.value.func.attr = 'dumps'
		return_node.value.func.ctx = ast.Load()
		logging.debug("		Quiero meter %s",astunparse.unparse(return_node))
		node.body.append(return_node)
		#return node.append(return_node)

def translateReturns(config_dict):
	logging.debug("<<<Enter in translate returns")
	global function_list
	global file
	global aux_config_dict
	global return_fun

	function_list = config_dict["function_list"]
	aux_config_dict = config_dict

	return_fun = False
	return_node = ast.Return()
	return_node.value = ast.Call()
	return_node.value.func = ast.Attribute()
	return_node.value.args = []
	return_node.value.keywords = []
	return_node.value.func.value = ast.Name()
	return_node.value.func.value.id = 'json'
	return_node.value.func.value.ctx = ast.Load()
	return_node.value.func.attr = 'dumps'
	return_node.value.func.ctx = ast.Load()

	for function in config_dict["program_data"]["functions"]:
		#get invocations inside functions
		file = function[:function.rfind(".")]
		function_node = config_dict["program_data"]["functions"][function]
		logging.debug("	Checking function %s", function)
		#logging.debug("		",ast.dump(function_node))
		visitReturn().visit(function_node)
		if return_fun:
			RewriteReturnValue().visit(function_node)
		else:
			AddReturnValue().visit(function_node)
		logging.debug("	Returns changed/added")
		return_fun = False


class AddThreadBeforeReturn(ast.NodeTransformer):

	def visit_Return(self, node):

		thread_call = ast.Call()
		thread_dict = ast.Dict()
		thread_dict.keys = []
		thread_dict.values = []

		'''thread_dict.keys.append('invoked_du')
		thread_dict.values.append('du_0')
		thread_dict.keys.append('invoked_function')
		thread_dict.values.append('thread_counter')
		thread_dict.keys.append('invoker_function')
		thread_dict.values.append('thread_counter')
		#thread_dict.keys.append('params')'''

		invoked_du = 'du_0'
		invoked_fun = "thread_counter"
		invoker_fun = "thread_counter"
		for i in (("invoked_du",invoked_du), ("invoked_function",invoked_fun), ("invoker_function",invoker_fun)):
			print(i)
			new_key = ast.Constant()
			new_key.value = i[0]
			new_key.kind = None
			new_value = ast.Constant()
			new_value.value = i[1]
			new_value.kind = None
			thread_dict.keys.append(new_key)
			thread_dict.values.append(new_value)

		new_key = ast.Constant()
		new_key.value = 'params'
		new_key.kind = None
		thread_dict.keys.append(new_key)
		params_dict = ast.Dict()
		params_dict.keys = []
		params_dict.values = []
		#args
		args_const = ast.Constant()
		args_const.value = ('args')
		args_const.kind = None
		params_dict.keys.append(args_const)
		args_value = ast.Constant()
		args_value.value = ['--']
		args_value.kind = None
		params_dict.values.append(args_value)
		#kwargs
		args_const = ast.Constant()
		args_const.value = ('kwargs')
		args_const.kind = None
		params_dict.keys.append(args_const)
		args_value = ast.Dict()
		args_value.keys = []
		args_value.values = []
		params_dict.values.append(args_value)
		thread_dict.values.append(params_dict)

		thread_call.func = ast.Name()
		thread_call.func.id = 'invoker'
		thread_call.func.ctx = ast.Load()
		thread_call.args = []
		thread_call.args.append(thread_dict)
		thread_call.keywords = []

		#self.generic_visit(node)
		#ast.copy_location(thread_call,node)
		node.value = thread_call
		return node

def add_thread_counter_minus(config_dict):
	logging.debug("<<<Adding threading control")
	to_write = "invoker({'invoked_du': 'du_0', 'invoked_function': 'thread_counter', 'invoker_function': 'thread_counter', 'params': {'args': ['++'], 'kwargs': {}}})\n"

	thread_call = ast.Call()
	thread_dict = ast.Dict()
	thread_dict.keys = []
	thread_dict.values = []

	'''thread_dict.keys.append('invoked_du')
	thread_dict.values.append('du_0')
	thread_dict.keys.append('invoked_function')
	thread_dict.values.append('thread_counter')
	thread_dict.keys.append('invoker_function')
	thread_dict.values.append('thread_counter')
	#thread_dict.keys.append('params')'''

	invoked_du = 'du_0'
	invoked_fun = "thread_counter"
	invoker_fun = "thread_counter"
	for i in (("invoked_du",invoked_du), ("invoked_function",invoked_fun), ("invoker_function",invoker_fun)):
		print(i)
		new_key = ast.Constant()
		new_key.value = i[0]
		new_key.kind = None
		new_value = ast.Constant()
		new_value.value = i[1]
		new_value.kind = None
		thread_dict.keys.append(new_key)
		thread_dict.values.append(new_value)

	new_key = ast.Constant()
	new_key.value = 'params'
	new_key.kind = None
	thread_dict.keys.append(new_key)
	params_dict = ast.Dict()
	params_dict.keys = []
	params_dict.values = []
	#args
	args_const = ast.Constant()
	args_const.value = ('args')
	args_const.kind = None
	params_dict.keys.append(args_const)
	args_value = ast.Constant()
	args_value.value = ['--']
	args_value.kind = None
	params_dict.values.append(args_value)
	#kwargs
	args_const = ast.Constant()
	args_const.value = ('kwargs')
	args_const.kind = None
	params_dict.keys.append(args_const)
	args_value = ast.Dict()
	args_value.keys = []
	args_value.values = []
	params_dict.values.append(args_value)
	thread_dict.values.append(params_dict)

	thread_call.func = ast.Name()
	thread_call.func.id = 'invoker'
	thread_call.func.ctx = ast.Load()
	thread_call.args = []
	thread_call.args.append(thread_dict)
	thread_call.keywords = []

	test_const = ast.Constant()
	test_const.value = "pepe"
	test_const.kind = None

	for function in config_dict["program_data"]["functions"]:
		file = function[:function.rfind(".")]
		function_node = config_dict["program_data"]["functions"][function]
		for i in config_dict["function_translated"]: #Los nombres de funcion ya se han cambiado en los nodos
			if config_dict["function_translated"][i] == function_node.name:
				original_node_name = i
		logging.debug("	checking %s",original_node_name)
		if original_node_name in config_dict["pragmas"]["parallel"]:
			logging.debug("	Checking function %s", function)
			AddThreadBeforeReturn().visit(function_node)
			try:
				thread_call.func.id = "\n"+" "*4*function_node.body[-1].col_offset +'invoker'
				function_node.body.insert(len(function_node.body),thread_call)
			except:
				pass
			#function_node.body.insert(-1,ast.fix_missing_locations(thread_call)) #en insert, -1 es el penultimo, en [] el -1 es el ultimo
			##function_node.body.insert(-1,test_const)
			#function_node.body.insert(-1,thread_call)
			'''positions = []
			for num,node in enumerate(function_node.body):
				if isinstance(node,ast.Return):
					positions.append(num)
			for i in positions:
				function_node.body.insert(function_node.body[positions[i]-1],(thread_call,function_node.body[i]))
			positions = []'''


