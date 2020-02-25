
# This module collapse the matrix using the selected 2 functions 
from __future__ import print_function
import json

def collapse(matrix, f1_row,f2_row):#,con):
	#print (">>>ENTER in collapse()...")
	f1_col=f1_row
	f2_col=f2_row
	#collapse functions matrix[0][f1_col] and matrix[0][f1_row]
	#----------------------------------------------------------------------------
	num_cols=len(matrix[0])
	num_rows=len(matrix)
	matrix_new= [[None] * (num_cols) for i in range(num_rows)]


	#copy matrix
	for i in range(0,num_rows):
		for j in range(0,num_cols):
			if (matrix[i][j]==None) :
				matrix[i][j]=0
			matrix_new[i][j]=matrix[i][j]
			#print("El elemento ", matrix_new[i][j], " es de tipo: ", type(matrix_new[i][j]))
	

	#update DU identifier
	#---------------------

	##update_DU(con, matrix_new[0][f2_col],matrix_new[0][f1_col])

	# collapse titles
	# -----------------
	# new function is a list of two functions ( f1 and f2 may be lists of functions)
	# we must create a new list composed of all items from list f1 and all intems from list f2
	# if f1 is a list, we extract items, else we simply add f1. The same for f2
	composite_list=[]
	if  isinstance(matrix_new[0][f1_col],list):
		for item in matrix_new[0][f1_col]:
			composite_list.append(item)
	else:
		composite_list.append(matrix_new[0][f1_col])

	if  isinstance(matrix_new[0][f2_col],list):
		for item in matrix_new[0][f2_col]:
			composite_list.append(item)
	else:
		composite_list.append(matrix_new[0][f2_col])


	#matrix_new[0][f1_col] = [matrix_new[0][f1_col],matrix_new[0][f2_col]]
	matrix_new[0][f1_col] = composite_list
	
	matrix_new[f1_row][0] = matrix_new[0][f1_col] 


	#collapse column and row values
	#------------------------------
	for i in range(1,num_rows):
		for j in range(1,num_cols):

			#when column = f2 column, just update f1+f2 column and set to zero f2 column
			if (j==f1_col):
				matrix_new[i][j]+=matrix[i][f2_col]
				matrix_new[i][f2_col]=0 # now f2 not invoke nothing
			if (i==f2_row):
				matrix_new[f1_row][j]+=matrix[i][j]	
				matrix[i][j]=0	
			
	
	#delete column f2 and row f2
	#----------------------------
	matrix_new2= [[None] * (num_cols-1) for i in range(num_rows-1)]
	row2=0
	col2=0
	for i in range(0,num_rows):
		if (i==f2_row):
			continue
		for j in range(0,num_cols):
			if (j==f2_col):
				continue
			matrix_new2[row2][col2]=matrix_new[i][j]
			col2+=1
		row2+=1
		col2=0

	#matrix=matrix_new2
	return matrix_new2



def update_DU(con, f2_list, f1_list):
	print (">>>ENTER in update_DU()...")
	print("Entradas:")
	print(f1_list)
	print(f2_list)
	aux_list2 = f2_list
	aux_list1 = f1_list
	
	#lets proceed with functions table
	#----------------------------------
	'''
	list2=[[]]
	list1=[[]]

	if isinstance(f2_list, str):
		list2[0]=f2_list
	else:
		list2=f2_list
	if isinstance(f1_list, str):
		list1[0]=f1_list
		print("F1_LIST ES UN STRING Y USARE: ", list1[0])
	else:
		list1=f1_list
		print("F1_LIST NO ES UN STRING Y USARE: ", list1[0])
	'''
	list1=[[]]
	list2=[[]]

	while isinstance(f1_list, str) == False:
		#En este caso f1_list es una lista, extraemos el primer elemento
		#hasta que sea un string
		list1[0] = f1_list[0]
		f1_list = list1[0]
	list1[0] = f1_list
	while isinstance(f2_list, str) == False:
		#En este caso f2_list es una lista, extraemos el primer elemento
		#hasta que sea un string
		list2[0] = f2_list[0]
		f2_list = list2[0]
	list2[0] = f2_list

	print("F1_LIST: ", f1_list, "tipo", type(f1_list))
	print("F2_LIST: ",f2_list, "tipo", type(f2_list))
	print("LIST1: ", list1, "tipo", type(list1))
	print("LIST2: ", list2, "tipo", type(list2))
	##print("La Peticion es:","SELECT DU from FUNCTIONS where ORIG_NAME='"+str(list1[0])+"'")

	##cursor = con.cursor()
	##cursor.execute("SELECT DU from FUNCTIONS where ORIG_NAME='"+list1[0]+"'")

	#for row in cursor:
	#	du=row[0]
	##du_list1=cursor.fetchone()[0]
	#Comprobamos si en la segunda lista es la du_0, de ser asi es la que se va a quedar
	##cursor.execute("SELECT DU from FUNCTIONS where ORIG_NAME='"+list2[0]+"'")
	du_list2=cursor.fetchone()[0]
	if du_list2 == 0:
		du = du_list2
		selected = 2
	else:
		du = du_list1
		selected = 1
	print("La du es: ", du)

	cursor.execute("SELECT DU from FUNCTIONS where ORIG_NAME='"+list2[0]+"'")
	du_old=cursor.fetchone()[0]

	if selected == 1:
		for i in list2:
			print("Actualizo la du de la funcion:", i)
			cursor.execute("UPDATE FUNCTIONS set DU="+str(du)+" where ORIG_NAME='"+i+"'")
		#update all list 2 dus
		if isinstance(aux_list2, list):
			pass
		else:
			aux_list2 = aux_list2.split()
		for i in aux_list2:
			print("Actualizo la du de la funcion:", i)
			cursor.execute("UPDATE FUNCTIONS set DU="+str(du)+" where ORIG_NAME='"+i+"'")
	else:
		for i in list1:
			print("Actualizo la du de la funcion:", i)
			cursor.execute("UPDATE FUNCTIONS set DU="+str(du)+" where ORIG_NAME='"+i+"'")
		#update all list 2 dus
		if isinstance(aux_list1, list):
			pass
		else:
			aux_list1 = aux_list1.split()
		for i in aux_list1:
			print("Actualizo la du de la funcion:", i)
			cursor.execute("UPDATE FUNCTIONS set DU="+str(du)+" where ORIG_NAME='"+i+"'")
	#now proceed with modules table
	#--------------------------------
	cursor.execute("SELECT ORIG_NAME,FINAL_IMPORTS from MODULES")
	imports_list=[]
	for row in cursor:
		#print "before:-->", row[1]
		
		imports_list=row[1].replace("import du_"+str(du_old),"import du_"+str(du) )
		#print "after:-->", imports_list
		cursor2=con.cursor()
		#print "UPDATE MODULES SET FINAL_IMPORTS ='"+ imports_list+ "' WHERE ORIG_NAME='"+row[0]+"'"
		cursor2.execute("UPDATE MODULES SET FINAL_IMPORTS ='"+ imports_list+ "' WHERE ORIG_NAME='"+row[0]+"'")
	print(">>Saliendo de update_du")	

