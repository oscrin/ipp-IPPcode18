#!/usr/bin/env python3
"""
Faculty of Information Technology, Brno University of Technology
IPP (Principles of Programming Languages) - Project 2
Name: IPP interpret of IPPcode18 language
Date created: April 2018
Author: Jan Kubica
Login: xkubic39
Email: xkubic39@stud.fit.vutbr.cz
File: interpret.py - IPPcode18 language interpret
"""

import sys
import getopt
import xml.etree.ElementTree as ET
import xml.parsers.expat as EX
import os
import re

EXIT_CODES = {
    'OK' :                           0,
    'INVALID_PARAMETER_ERROR' :     10,
    'INPUT_FILE_ERROR' :            11,
    'OUTPUT_FILE_ERROR' :           12,
    'BAD_XML_FORMAT' :              31, # well-formated, structure of XML
    'LEXYCAL_OR_SYNTACTIC_ERROR' :  32, # invalid lexem for string literal, invalid operate code
    'SEMANTIC_ERROR' :              52,
    'RUNTIME_ERROR_OPERANDS' :      53, # bad types according to operation
    'RUNTIME_ERROR_VARIABLE' :      54,
    'RUNTIME_ERROR_FRAME' :         55, # GF, LF, TF
    'RUNTIME_ERROR_VALUE' :         56, # not initialized
    'RUNTIME_ERROR_ZERO' :          57,
    'RUNTIME_ERROR_STRING' :        58,
    'RUNTIME_ERROR_REDEFINITION' :  59,
    'UNDEFINED_INSTRUCTION' :       60,
    'INTERNAL_ERROR' :              99

}

# FRAMES
"""
GF - empty at start
LF - undefined at start, according to local frame stack
TF - preparation of new or removing old frame ( finishing function, calling dunction ),
then moved to local frame stack, undefined at start
"""
# DATA TYPES
"""
- no implicit conversion
- int, bool, string (compatible with Python 3)
"""

def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False
    except TypeError:
        return False

def dict_find(d, key):
    try:
        v = d[key]
        return v
    except KeyError:
        return False
    except NameError:
        return False

# Represents parameter taken from xml code
class Parameter:
    def __init__(self, tag, text, ptype):
        self.par_type = ptype # type
        self.text = text # value
        self.tag = tag # (arg1, arg2, arg3)

    # checks valitity of type, returns true or false
    def check_type(self):
        if self.par_type == "bool":
            if self.text == "true" or self.text == "false":
                return True
            return False
        elif self.par_type == "int":
            if is_int(self.text):
                return True
        elif self.par_type == "type":
            if self.text == "bool" or self.text == "string" or self.text == "int":
                return True
            return False
        elif self.par_type == "string":
            return True
        elif self.par_type == "label":
            return True
        elif self.par_type == "var":
            if self.text[:3] == "LF@" or self.text[:3] == "GF@" or self.text[:3] == "TF@":
                return True
        return False
        # believe strings, labels and variable names are corrected in parser

# Represents one variable stored in a frame
class Variable:
    def __init__(self, name, value = None, vtype = None):
        self.name = name
        self.value = value
        self.var_type = vtype

    # modifies given variable with new type and value
    def modify(self, value, vtype):
        self.value = value
        self.var_type = vtype
# Frame represents table of current available variables
class Frame:
    def __init__(self):
        self.table = []

    # creates Variable instance and adds it to Frame, raises ERROR if variable already defined
    def add_var(self, name):
        if name in self.table:
            sys.stderr.write('ERROR: Variable already exists: ' + str(name) + '\n')
            sys.exit(EXIT_CODES['RUNTIME_ERROR_REDEFINITION'])
        else:
            var = Variable(name) # creates variable
            self.table.append(var)

    # modifies Variable according to given name, value and type, raises ERROR if variable not found
    def mod_var(self, name, value, var_type):
        for var in self.table:
            if var.name == name:
                var.value = value
                var.var_type = var_type
                return True
        sys.stderr.write('ERROR: Variable not defined: ' + str(name) + '\n')
        sys.exit(EXIT_CODES['RUNTIME_ERROR_VARIABLE'])

    def find_var(self, name):
        for var in self.table:
            if var.name == name:
                return var
        return False # variable not defined
# local frame
class LocalFrame(Frame):
    ...
# global frame - singleton
class GlobalFrame(Frame):
    ...
# stack for switching frames
class FrameStack:

    def __init__(self):
        self.frame_arr = []

    # checks if Stack is empty, returns True x False
    def empty(self):
        if len(self.frame_arr) == 0:
            return True
        else:
            return False

    # pushes Frame to stack, no return
    def push(self, f: Frame):
        self.frame_arr.append(f)

    # pops Frame from stack, returns Frame or False
    def pop(self):
        if (len(self.frame_arr) > 0):
            p_frame = self.frame_arr.pop()
            return p_frame
        else:
            return False
    def get_lFrame(self):
        if (len(self.frame_arr) > 0):
            return self.frame_arr[-1]
        else:
            return None
# stack for jumping
class CallStack:

    def __init__(self):
        self.call_arr = []

    # checks if Stack is empty, returns True x False
    def empty(self):
        if len(self.call_arr) == 0:
            return True
        else:
            return False

    # pushes Ord number of instruction for return after JUMP
    def push(self, o):
        self.call_arr.append(o)

    # pops Ord number of instruction to correct return, returns Ord number or False when empty
    def pop(self):
        if (len(self.call_arr) > 0):
            o = self.call_arr.pop()
            return o
        else:
            return False
# stack to store data
class DataStack:

    def __init__(self):
        self.data_arr = []

    # checks if Stack is empty, returns True x False
    def empty(self):
        if len(self.data_arr) == 0:
            return True
        else:
            return False

    # pushes variable (or symbol), no return
    def push(self, var):
        self.data_arr.append(var)

    # pops variable (or symbol), returns variable (or symbol) or False when empty
    def pop(self):
        if (len(self.data_arr) > 0):
            var = self.data_arr.pop()
            return var
        else:
            return False

# definition of one global frame
gFrame = GlobalFrame()
# definition of one local frame
lFrame = None
# definition of one temporary frame
tFrame = None
# definition of local frame stack
fStack = FrameStack()
# definition of call stack
cStack = CallStack()
# definition of data stack
dStack = DataStack()
# labels dictionary prepared for jumps
labels = {}

def print_help():
    print("INTERPRET for IPPcode18 - interprets xml file given from parse.php script")
    print("-------------------------------------------------------------------------")
    print("Parameters: ./interpret.py --source=<xml_source_file>")
    print("            ./interpret.py --help")
    print("Project to IPP - Brno University of Technology, Faculty of Information Technology")
    print("---------------------------------------------------------------------------------")
    print("(c) Jan Kubica, xkubic39@stud.fit.vutbr.cz, April 2018")

def MOVE(order, arg_list):
    var = resolve_parameter_var(order, "MOVE", arg_list[0])
    s_val, s_type = resolve_parameter_symb(order, "MOVE", arg_list[1])
    if s_val == None:
        s_val = ""
    var.modify(s_val, s_type)
#
def CREATEFRAME(order, arg_list):
    global tFrame
    tFrame = Frame()
#
def PUSHFRAME(order, arg_list):
    global fStack, tFrame, lFrame
    if tFrame != None:
        fStack.push(tFrame)
    else:
        sys.stderr.write('ERROR: PUSHFRAME (order ' + str(order) + ') tries to push nonallocated Frame\n')
        sys.exit(EXIT_CODES['RUNTIME_ERROR_FRAME']) 
    lFrame = tFrame
    tFrame = None
#
def POPFRAME(order, arg_list):
    global tFrame, fStack, lFrame
    tFrame = fStack.pop()
    if tFrame == False:
        sys.stderr.write('ERROR: POPFRAME (order ' + str(order) + ') reaches empty Frame Stack\n')
        sys.exit(EXIT_CODES['RUNTIME_ERROR_FRAME'])
    lFrame = fStack.get_lFrame()
# var
def DEFVAR(order, arg_list):
    global lFrame, gFrame, tFrame
    var = arg_list[0]
    if var.text[:3] == 'GF@':
        gFrame.add_var(var.text[3:])
    if var.text[:3] == 'LF@':
        if lFrame != None:
            lFrame.add_var(var.text[3:])
        else:
            sys.stderr.write('ERROR: DEFVAR (order ' + order + ') tries to save variable ' + str(var.text) + ' to nonallocated Local Frame\n')
            sys.exit(EXIT_CODES['RUNTIME_ERROR_FRAME'])
    if var.text[:3] == 'TF@':
        if tFrame != None:
            tFrame.add_var(var.text[3:])
        else:
            sys.stderr.write('ERROR: DEFVAR (order ' + order + ') tries to save variable ' + str(var.text) + ' to nonallocated Temporary Frame\n')
            sys.exit(EXIT_CODES['RUNTIME_ERROR_FRAME'])
# label
def CALL(order, arg_list):
    global labels, cStack
    label = arg_list[0]
    cStack.push(order)
    return int(labels[label.text])
#
def RETURN(order, arg_list):
    global cStack
    if not cStack.empty():
        l = cStack.pop()
        return l
    """
    else:
        sys.stderr.write('ERROR: RETURN (order ' + str(order) + ') reaches empty Call Stack\n')
        sys.exit(EXIT_CODES['RUNTIME_ERROR_VALUE'])
    """
# symb
def PUSHS(order, arg_list):
    global dStack
    v, t = resolve_parameter_symb(order, "PUSHS", arg_list[0])
    var = Variable("none", v, t)
    dStack.push(var)
# var
def POPS(order, arg_list):
    global dStack, gFrame, lFrame
    pvar = dStack.pop()
    if pvar == False:
        sys.stderr.write('ERROR: POPS (order ' + str(order) + ') reaches empty Stack\n')
        sys.exit(EXIT_CODES['RUNTIME_ERROR_VALUE'])      
    var = resolve_parameter_var(order, "POPS", arg_list[0])
    var.modify(pvar.value, pvar.var_type)
# var, symb1, symb2
def ADD(order, arg_list):
    var = resolve_parameter_var(order, "ADD", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "ADD", arg_list[1])
    symb2_v, symb2_t = resolve_parameter_symb(order, "ADD", arg_list[2])
    if symb1_t == "int" and symb2_t == "int":
        result = int(symb1_v) + int(symb2_v)
        var.modify(result, "int")
    else:
        sys.stderr.write("ERROR: ADD (order " + str(order) + ") has incompatible argument types '" + str(symb1_t) + "' and '" + str(symb2_t) + "'\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
# var, symb1, symb2
def SUB(order, arg_list):
    var = resolve_parameter_var(order, "SUB", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "SUB", arg_list[1])
    symb2_v, symb2_t = resolve_parameter_symb(order, "SUB", arg_list[2])
    if symb1_t == "int" and symb2_t == "int":
        result = int(symb1_v) - int(symb2_v)
        var.modify(result, "int")
    else:
        sys.stderr.write("ERROR: SUB (order " + str(order) + ") has incompatible argument types '" + str(symb1_t) + "' and '" + str(symb2_t) + "'\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
# var, symb1, symb2
def MUL(order, arg_list):
    var = resolve_parameter_var(order, "MUL", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "MUL", arg_list[1])
    symb2_v, symb2_t = resolve_parameter_symb(order, "MUL", arg_list[2])
    if symb1_t == "int" and symb2_t == "int":
        result = int(symb1_v) * int(symb2_v)
        var.modify(result, "int")
    else:
        sys.stderr.write("ERROR: MUL (order " + str(order) + ") has incompatible argument types '" + str(symb1_t) + "' and '" + str(symb2_t) + "'\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
# var, symb1, symb2
def IDIV(order, arg_list):
    var = resolve_parameter_var(order, "IDIV", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "IDIV", arg_list[1])
    symb2_v, symb2_t = resolve_parameter_symb(order, "IDIV", arg_list[2])
    if symb1_t == "int" and symb2_t == "int":
        try:
            result = int(symb1_v) // int(symb2_v)
            var.modify(result, "int")
        except ZeroDivisionError:
            sys.stderr.write("ERROR: IDIV (order " + str(order) + ") Division by zero!\n")
            sys.exit(EXIT_CODES['RUNTIME_ERROR_ZERO'])
    else:
        sys.stderr.write("ERROR: IDIV (order " + str(order) + ") has incompatible argument types '" + str(symb1_t) + "' and '" + str(symb2_t) + "'\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
# var, symb1, symb2
def LT(order, arg_list):
    var = resolve_parameter_var(order, "LT", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "LT", arg_list[1])
    symb2_v, symb2_t = resolve_parameter_symb(order, "LT", arg_list[2])

    # --- COMPARATION
    if symb1_t == symb2_t: # same types
        if symb1_t == "int":
            var.modify("true", "bool") if int(symb1_v) < int(symb2_v) else var.modify("false", "bool")
        if symb1_t == "bool":
            var.modify("true", "bool") if symb1_v < symb2_v else var.modify("false", "bool")
        if symb1_t == "string":
            var.modify("true", "bool") if symb1_v < symb2_v else var.modify("false", "bool")
    else:
        sys.stderr.write("ERROR: LT (order " + str(order) + ") has incompatible argument types '" + str(symb1_t) + "' and '" + str(symb2_t) + "'\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
# var, symb1, symb2
def GT(order, arg_list):
    var = resolve_parameter_var(order, "GT", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "GT", arg_list[1])
    symb2_v, symb2_t = resolve_parameter_symb(order, "GT", arg_list[2])

    # --- COMPARATION
    if symb1_t == symb2_t: # same types
        if symb1_t == "int":
            var.modify("true", "bool") if int(symb1_v) > int(symb2_v) else var.modify("false", "bool")
        if symb1_t == "bool":
            var.modify("true", "bool") if symb1_v > symb2_v else var.modify("false", "bool")
        if symb1_t == "string":
            var.modify("true", "bool") if symb1_v > symb2_v else var.modify("false", "bool")
    else:
        sys.stderr.write("ERROR: GT (order " + str(order) + ") has incompatible argument types '" + str(symb1_t) + "' and '" + str(symb2_t) + "'\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
# var, symb1, symb2
def EQ(order, arg_list):
    var = resolve_parameter_var(order, "EQ", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "EQ", arg_list[1])
    symb2_v, symb2_t = resolve_parameter_symb(order, "EQ", arg_list[2])

    # --- COMPARATION
    if symb1_t == symb2_t: # same types
        if symb1_t == "int":
            var.modify("true", "bool") if int(symb1_v) == int(symb2_v) else var.modify("false", "bool")
        if symb1_t == "bool":
            var.modify("true", "bool") if symb1_v == symb2_v else var.modify("false", "bool")
        if symb1_t == "string":
            var.modify("true", "bool") if symb1_v == symb2_v else var.modify("false", "bool")
    else:
        sys.stderr.write("ERROR: EQ (order " + str(order) + ") has incompatible argument types '" + str(symb1_t) + "' and '" + str(symb2_t) + "'\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
# var, symb1, symb2
def AND(order, arg_list):
    var = resolve_parameter_var(order, "AND", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "AND", arg_list[1])
    symb2_v, symb2_t = resolve_parameter_symb(order, "AND", arg_list[2])
    # --- COMPARATION
    if symb1_t == "bool" and symb2_t == "bool":
        if symb1_v == "true" and symb2_v == "true":
            var.modify("true", "bool")
        else:
            var.modify("false", "bool")
    else:
        sys.stderr.write("ERROR: AND (order " + str(order) + ") has incompatible argument types '" + str(symb1_t) + "' and '" + str(symb2_t) + "'\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
# var, symb1, symb2
def OR(order, arg_list):
    var = resolve_parameter_var(order, "OR", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "OR", arg_list[1])
    symb2_v, symb2_t = resolve_parameter_symb(order, "OR", arg_list[2])
    # --- COMPARATION
    if symb1_t == "bool" and symb2_t == "bool":
        if symb1_v == "true" or symb2_v == "true":
            var.modify("true", "bool")
        else:
            var.modify("false", "bool")
    else:
        sys.stderr.write("ERROR: OR (order " + str(order) + ") has incompatible argument types '" + str(symb1_t) + "' and '" + str(symb2_t) + "'\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
# var, symb
def NOT(order, arg_list):
    var = resolve_parameter_var(order, "NOT", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "NOT", arg_list[1])
    # --- COMPARATION
    if symb1_t == "bool":
        if symb1_v == "true":
            var.modify("false", "bool")
        else:
            var.modify("true", "bool")
    else:
        sys.stderr.write("ERROR: NOT (order " + str(order) + ") has incompatible argument type '" + str(symb1_t) + "'\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
# var, symb
def INT2CHAR(order, arg_list):
    var = resolve_parameter_var(order, "INT2CHAR", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "INT2CHAR", arg_list[1])
    if symb1_t != "int":
        sys.stderr.write("ERROR: INT2CHAR (order " + str(order) + ") second argument '" + str(arg_list[1].text) + "' is not integer type\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
    try:
        c = chr(int(symb1_v))
        var.modify(c, "string")
    except ValueError:
        sys.stderr.write("ERROR: INT2CHAR (order " + str(order) + ") second argument '" + str(arg_list[1].text) + "' - index out of range\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_STRING'])
# var, symb1, symb2
def STRI2INT(order, arg_list):
    var = resolve_parameter_var(order, "STRI2INT", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "STRI2INT", arg_list[1])
    symb2_v, symb2_t = resolve_parameter_symb(order, "STRI2INT", arg_list[2])
    if symb1_t != "string":
        sys.stderr.write("ERROR: STRI2INT (order " + str(order) + ") second argument '" + str(arg_list[1].text) + "' is not string type\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
    if symb2_t != "int":
        sys.stderr.write("ERROR: STRI2INT (order " + str(order) + ") third argument '" + str(arg_list[2].text) + "' is not integer type\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
    try:
        s2 = list(symb1_v)
        c = s2[int(symb2_v)]
        result = ord(c)
        var.modify(result, "int")
    except IndexError:
        sys.stderr.write("ERROR: STRI2INT (order " + str(order) + ") second argument '" + str(arg_list[2].text) + "' - index " + str(symb2_v) + " out of range\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_STRING'])
# var, type
def READ(order, arg_list):
    var = resolve_parameter_var(order, "READ", arg_list[0])
    typ = arg_list[1]
    try:
        s = input()
    except EOFError:
        s = ""
        if typ == "int":
            s = 0

    if typ.text == "int":
        if is_int(s):
            var.modify(int(s), "int")
        else:
            var.modify(int(0), "int")
    elif typ.text == "string":
        var.modify(s, "string")
    elif typ.text == "bool":
        if s.lower() == "true":
            var.modify("true", "bool")
        else:
            var.modify("false", "bool")
    else:
        sys.stderr.write("ERROR: READ (order " + str(order) + ") type not recognized\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
# symb
def WRITE(order, arg_list):
    symb1_v, symb1_t = resolve_parameter_symb(order, "WRITE", arg_list[0])
    if symb1_v != None:
        if symb1_t == "int":
            print(int(symb1_v))
        else:
            print(symb1_v)
    else:
        print("")
# var, symb1, symb2
def CONCAT(order, arg_list):
    var = resolve_parameter_var(order, "CONCAT", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "CONCAT", arg_list[1])
    symb2_v, symb2_t = resolve_parameter_symb(order, "CONCAT", arg_list[2])
    if symb1_t != "string":
        sys.stderr.write("ERROR: CONCAT (order " + str(order) + ") second argument '" + str(arg_list[1].text) + "' is not string type\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
    if symb2_t != "string":
        sys.stderr.write("ERROR: CONCAT (order " + str(order) + ") third argument '" + str(arg_list[2].text) + "' is not string type\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
    result = symb1_v + symb2_v
    var.modify(result, "string")
# var, symb
def STRLEN(order, arg_list):
    var = resolve_parameter_var(order, "STRLEN", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "STRLEN", arg_list[1])
    if symb1_t != "string":
        sys.stderr.write("ERROR: STRLEN (order " + str(order) + ") second argument '" + str(arg_list[1].text) + "' is not string type\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
    result = len(symb1_v)
    var.modify(result,"int")
# var, symb1, symb2
def GETCHAR(order, arg_list):
    var = resolve_parameter_var(order, "GETCHAR", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "GETCHAR", arg_list[1])
    symb2_v, symb2_t = resolve_parameter_symb(order, "GETCHAR", arg_list[2])
    if symb1_t != "string":
        sys.stderr.write("ERROR: GETCHAR (order " + str(order) + ") second argument '" + str(arg_list[1].text) + "' is not string type\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
    if symb2_t != "int":
        sys.stderr.write("ERROR: GETCHAR (order " + str(order) + ") third argument '" + str(arg_list[2].text) + "' is not integer type\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
    result = var.value
    try:
        result = list(symb1_v)
        c = result[int(symb2_v)]
        var.modify(c, "string")
    except IndexError:
        sys.stderr.write("ERROR: GETCHAR (order " + str(order) + ") second argument '" + str(arg_list[2].text) + "' - index " + str(symb2_v) + " out of range\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_STRING'])
# var, symb1, symb2
def SETCHAR(order, arg_list):
    var = resolve_parameter_var(order, "SETCHAR", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "SETCHAR", arg_list[1])
    symb2_v, symb2_t = resolve_parameter_symb(order, "SETCHAR", arg_list[2])
    if var.var_type != "string":
        sys.stderr.write("ERROR: SETCHAR (order " + str(order) + ") first argument '" + str(arg_list[0].text) + "' (" + str(var.var_type) + ") is not string type\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
    if symb1_t != "int":
        sys.stderr.write("ERROR: SETCHAR (order " + str(order) + ") second argument '" + str(arg_list[1].text) + "' is not integer type\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
    if symb2_t != "string":
        sys.stderr.write("ERROR: SETCHAR (order " + str(order) + ") third argument '" + str(arg_list[2].text) + "' is not string type\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
    if len(symb2_v) < 1:
        sys.stderr.write("ERROR: SETCHAR (order " + str(order) + ") third argument '" + str(arg_list[2].text) + "' is empty string\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_STRING'])
    c = symb2_v[0]
    result = var.value
    try:
        result = list(result)
        result[int(symb1_v)] = c
        result = "".join(result)
        var.modify(result, var.var_type)
    except IndexError:
        sys.stderr.write("ERROR: SETCHAR (order " + str(order) + ") second argument '" + str(arg_list[2].text) + "' - index " + str(symb2_v) + " out of range\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_STRING'])
# var, symb
def TYPE(order, arg_list):
    var = resolve_parameter_var(order, "TYPE", arg_list[0])
    symb1_v, symb1_t = resolve_parameter_symb(order, "TYPE", arg_list[1])
    var.modify(symb1_t, "string")
# label
def LABEL(order, arg_list):
    ...
# label
def JUMP(order, arg_list):
    global labels
    label = arg_list[0]
    return int(labels[label.text])
# label, symb1, symb2
def JUMPIFEQ(order, arg_list):
    global labels
    symb1_v, symb1_t = resolve_parameter_symb(order, "JUMPIFEQ", arg_list[1])
    symb2_v, symb2_t = resolve_parameter_symb(order, "JUMPIFEQ", arg_list[2])
    # --- RESOLVE label
    label = arg_list[0].text
    # --- COMPARATION
    if symb1_t == symb2_t: # same types
        if symb1_t == "int":
            if int(symb1_v) == int(symb2_v):
                return int(labels[label])
        if symb1_t == "bool":
            if symb1_v == symb2_v:
                return int(labels[label])
        if symb1_t == "string":
            if symb1_v == symb2_v:
                return int(labels[label])
    else:
        sys.stderr.write("ERROR: JUMPIFEQ (order " + str(order) + ") has incompatible argument types '" + str(arg_list[1].text) + "' (" + str(symb1_t) + ") and '" + str(arg_list[2].text) + "' (" + str(symb2_t) + ")\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
# label, symb1, symb2
def JUMPIFNEQ(order, arg_list):
    global labels
    symb1_v, symb1_t = resolve_parameter_symb(order, "JUMPIFEQ", arg_list[1])
    symb2_v, symb2_t = resolve_parameter_symb(order, "JUMPIFEQ", arg_list[2])
    # --- RESOLVE label
    label = arg_list[0].text
    # --- COMPARATION
    if symb1_t == symb2_t: # same types
        if symb1_t == "int":
            if int(symb1_v) != int(symb2_v):
                return int(labels[label])
        if symb1_t == "bool":
            if symb1_v != symb2_v:
                return int(labels[label])
        if symb1_t == "string":
            if symb1_v != symb2_v:
                return int(labels[label])
    else:
        sys.stderr.write("ERROR: JUMPIFNEQ (order " + str(order) + ") has incompatible argument types '" + str(arg_list[1].text) + "' (" + str(symb1_t) + ") and '" + str(arg_list[2].text) + "' (" + str(symb2_t) + ")\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_OPERANDS'])
# symb
def DPRINT(order, arg_list):
    global tFrame, gFrame, lFrame
    symb = arg_list[0]
    var = False
    if '@' in symb.text:
        if (symb.text[:3] == 'LF@'):
            if lFrame != None:
                var = lFrame.find_var(symb.text[3:])
            else:
                sys.stderr.write("Frame for variable " + str(symb.text) + " not initialized.\n")
        elif (symb.text[:3] == 'GF@'):
            var = gFrame.find_var(symb.text[3:])
        elif (symb.text[:3] == 'TF@'):
            if tFrame != None:
                var = tFrame.find_var(symb.text[3:])
            else:
                sys.stderr.write("Frame for variable " + str(symb.text) + " not initialized.\n")
        if var == False:
            sys.stderr.write("Variable " + str(symb.text) + " not found.\n")
        elif var.value == None:
            sys.stderr.write("Variable " + str(symb.text) + " not initialized.\n")
        else:
            sys.stderr.write(str(var.value) + "\n")
    else:
        sys.stderr.write(symb.text)
#
def BREAK(order, arg_list):
    sys.stderr.write("-----------------------------------------------\n")
    sys.stderr.write("| BREAK | Order (" + str(order) + ") | Instruction count (" + str(Instruction.processed) + ") |\n")
    sys.stderr.write("-----------------------------------------------\n")
    sys.stderr.write("$ GF as (NAME,VALUE,TYPE): \n")
    for var in gFrame.table:
        sys.stderr.write("-> ('" + str(var.name) + "','" + str(var.value) + "','" + str(var.var_type) + "')\n")
    try:
        sys.stderr.write("$ LF as (NAME,VALUE,TYPE): \n")
        for var in lFrame.table:
            sys.stderr.write("-> ('" + str(var.name) + "','" + str(var.value) + "','" + str(var.var_type) + "')\n")
    except NameError:
        ...
    except AttributeError:
        ...
    try:
        sys.stderr.write("$ TF as (NAME,VALUE,TYPE): \n")
        for var in tFrame.table:
            sys.stderr.write("-> ('" + str(var.name) + "','" + str(var.value) + "','" + str(var.var_type) + "')\n")
    except NameError:
        ...
    except AttributeError:
        ...
    try:
        sys.stderr.write("$ DSTACK as (VALUE,TYPE): \n")
        for var in dStack.data_arr:
            sys.stderr.write("-> ('" + str(var.value) + "','" + str(var.var_type) + "')\n")
    except NameError:
        ...
    except AttributeError:
        ...

# class representing one instruction with parameter list, enables calling
class Instruction:
    # list of valid instructions
    inst_list = {
        'MOVE': MOVE,
        'CREATEFRAME': CREATEFRAME,
        'PUSHFRAME': PUSHFRAME,
        'POPFRAME': POPFRAME,
        'DEFVAR': DEFVAR,
        'CALL': CALL,
        'RETURN': RETURN,
        'PUSHS': PUSHS,
        'POPS': POPS,
        'ADD': ADD,
        'SUB': SUB,
        'MUL': MUL,
        'IDIV': IDIV,
        'LT': LT,
        'GT': GT,
        'EQ': EQ,
        'AND': AND,
        'OR': OR,
        'NOT': NOT,
        'INT2CHAR': INT2CHAR,
        'STRI2INT': STRI2INT,
        'READ': READ,
        'WRITE': WRITE,
        'CONCAT': CONCAT,
        'STRLEN': STRLEN,
        'GETCHAR': GETCHAR,
        'SETCHAR': SETCHAR,
        'TYPE': TYPE,
        'LABEL': LABEL,
        'JUMP': JUMP,
        'JUMPIFEQ': JUMPIFEQ,
        'JUMPIFNEQ': JUMPIFNEQ,
        'DPRINT': DPRINT,
        'BREAK': BREAK
    }

    # list of instruction arguments
    inst_args = {
        'MOVE': 'vs',
        'CREATEFRAME': '',
        'PUSHFRAME': '',
        'POPFRAME': '',
        'DEFVAR': 'v',
        'CALL': 'l',
        'RETURN': '',
        'PUSHS': 's',
        'POPS': 'v',
        'ADD': 'vss',
        'SUB': 'vss',
        'MUL': 'vss',
        'IDIV': 'vss',
        'LT': 'vss',
        'GT': 'vss',
        'EQ': 'vss',
        'AND': 'vss',
        'OR': 'vss',
        'NOT': 'vs',
        'INT2CHAR': 'vs',
        'STRI2INT': 'vss',
        'READ': 'vt',
        'WRITE': 's',
        'CONCAT': 'vss',
        'STRLEN': 'vs',
        'GETCHAR': 'vss',
        'SETCHAR': 'vss',
        'TYPE': 'vs',
        'LABEL': 'l',
        'JUMP': 'l',
        'JUMPIFEQ': 'lss',
        'JUMPIFNEQ': 'lss',
        'DPRINT': 's',
        'BREAK': ''
    }

    processed = 0

    def __init__(self, order, name, parameter_list):
        self.order = order
        self.name = name
        self.parameter_list = parameter_list

    def call(self):
        Instruction.processed += 1
        inst_func = Instruction.inst_list[self.name]
        r_val = inst_func(self.order, self.parameter_list)
        if is_int(r_val):
            return int(r_val)

# checks number of attributes in element tag
def check_attributes(tag, attr_list_given, attr_list_req):
    if len(attr_list_given) > len(attr_list_req):
        sys.stderr.write("ERROR: Invalid XML file - too many arguments in '" + str(tag) + "' element tag\n")
        sys.exit(EXIT_CODES['BAD_XML_FORMAT'])
    else:
        for attr in attr_list_given:
            if attr not in attr_list_req:
                sys.stderr.write("ERROR: Invalid XML file - attribute '" + str(attr) + "' in '" + str(tag) + "' not supported\n")
                sys.exit(EXIT_CODES['BAD_XML_FORMAT'])

# looking for variable in all frames, raises error if frame not allocated, false if variable not found
def look_up_variable(name: str):
    global lFrame, gFrame, tFrame
    if name[:3] == "LF@":
        if lFrame != None:
            var = lFrame.find_var(name[3:])
        else:
            sys.stderr.write('ERROR: Nonallocated Local Stack\n')
            sys.exit(EXIT_CODES['RUNTIME_ERROR_FRAME'])
    if name[:3] == "GF@":
        var = gFrame.find_var(name[3:])
    if name[:3] == "TF@":
        if tFrame != None:
            var = tFrame.find_var(name[3:])
        else:
            sys.stderr.write('ERROR: Nonallocated Temporary Stack\n')
            sys.exit(EXIT_CODES['RUNTIME_ERROR_FRAME'])
    return var # Variable Instance or False

# resolves given variable in parameter, if not found, raises Error
def resolve_parameter_var(order, f_name, param):
    var = look_up_variable(param.text)
    if var == False:
        sys.stderr.write("ERROR: " + str(f_name) + " (order " + str(order) + ") reaches uninitialized variable '" + str(param.text) + "'\n")
        sys.exit(EXIT_CODES['RUNTIME_ERROR_VARIABLE'])

    return var

# resolves given symbol in parameter, if not found, raises Error
def resolve_parameter_symb(order, f_name, param):
    if param.par_type == "var":
        var = look_up_variable(param.text)
        if var == False:
            sys.stderr.write("ERROR: " + str(f_name) + " (order " + str(order) + ") reaches uninitialized variable '" + str(param.text) + "'\n")
            sys.exit(EXIT_CODES['RUNTIME_ERROR_VARIABLE'])
        else:
            v = var.value
            t = var.var_type
    else:
        v = param.text
        t = param.par_type

    return v, t

# checks string for nonallowed chars and corrects < > &, return string or raises Error
def correct_string(s):
    if s != None:
        no_ws = ''.join(s.split())
        if len(no_ws) != len(s):
            sys.stderr.write("ERROR: Incompatible string format in XML file\n")
            sys.exit(EXIT_CODES['LEXYCAL_OR_SYNTACTIC_ERROR'])
        ls_o = list(s)
        ls_n = []
        o_code = []
        i = 0
        while i < (len(ls_o)):
            if ls_o[i] == "\\":
                try:
                    o_code.append(ls_o[i+1])
                    o_code.append(ls_o[i+2])
                    o_code.append(ls_o[i+3])
                    j = "".join(o_code)
                    o_code = []
                    c = chr(int(j))
                    ls_n.append(c)
                    i = i + 4
                except IndexError:
                    sys.stderr.write("ERROR: Incompatible string format in XML file\n")
                    sys.exit(EXIT_CODES['LEXYCAL_OR_SYNTACTIC_ERROR'])
            elif ls_o[i] == "&":
                try:
                    if ls_o[i+1] == "g" and ls_o[i+2] == "t" and ls_o[i+2] == ";":
                        ls_n.append(">")
                        i = i+3
                    elif ls_o[i+1] == "l" and ls_o[i+2] == "t" and ls_o[i+2] == ";":
                        ls_n.append("<")
                        i = i + 3
                    elif ls_o[i+1] == "a" and ls_o[i+2] == "m" and ls_o[i+2] == "p" and ls_o[i+3] == ";":
                        ls_n.append("&")
                        i = i + 4
                except IndexError:
                    sys.stderr.write("ERROR: Incompatible string format in XML file\n")
                    sys.exit(EXIT_CODES['LEXYCAL_OR_SYNTACTIC_ERROR'])
            else:
                ls_n.append(ls_o[i])
                i = i+1
        s_n = "".join(ls_n)
        return s_n
    else:
        return ""

# begin of the program
def main(argv):
    global labels
    xml_file = ""
    long_opt = ["help", "source="]
    try:
        opts, args = getopt.getopt(argv, "hs:", long_opt)
    except getopt.GetoptError:
        print_help()
        sys.exit(EXIT_CODES['INVALID_PARAMETER_ERROR'])
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print_help()
            sys.exit(EXIT_CODES['OK'])
        elif opt in ("-s", "--source"):
            xml_file = arg
            if len(arg) == 0:
                print('ERROR: No input file given')
                sys.exit(EXIT_CODES['INPUT_FILE_ERROR'])

    # addinational arguments not supported
    if args:
        sys.stderr.write('ERROR: Invalid parameters: ' + str(args) + "\n")
        sys.exit(EXIT_CODES['INVALID_PARAMETER_ERROR'])

    # verify xml file access
    if os.path.exists(xml_file): # exists
        if os.access(xml_file, os.R_OK): # is readable
            try:
                #dom = parse(xml_file)
                tree = ET.parse(xml_file)
            except ET.ParseError:
                sys.stderr.write('ERROR: Invalid XML file: ' + str(xml_file) + "\n")
                sys.exit(EXIT_CODES['BAD_XML_FORMAT'])
            except EX.ExpatError:
                sys.stderr.write('ERROR: Invalid XML file: ' + str(xml_file) + "\n")
                sys.exit(EXIT_CODES['BAD_XML_FORMAT'])
        else: # not readable
            sys.stderr.write('ERROR: File is not readable: ' + str(xml_file) + "\n")
            sys.exit(EXIT_CODES['INPUT_FILE_ERROR'])
    else: # doesn't exist
        sys.stderr.write('ERROR: File does not exist: ' + str(xml_file) + "\n")
        sys.exit(EXIT_CODES['INPUT_FILE_ERROR'])

    # ------ HEADER -------
    # check valid xml header (mandatory in this project)
    # <?xml version="1.0" encoding="UTF-8"?>
    with open(xml_file) as f:
        xml_header = f.readline()
    match = re.match(r"<\?xml.*\?>",xml_header)
    if not match:
        sys.stderr.write('ERROR: Invalid XML file - no header found: ' + str(xml_file) + "\n")
        sys.exit(EXIT_CODES['BAD_XML_FORMAT'])

    # root of XML
    root = tree.getroot()

    #------ MAKING AST -------
    xml_len = len(list(root))
    AST = ['x'] * xml_len

    labels = {}  # list of acessible labels in source code
    label_names = []  # label names
    l = ""  # current label
    lb = False

    arg_tags = ["arg1", "arg2", "arg3"]
    program_attrib = ["language", "name", "description"]
    inst_attrib = ["order", "opcode"]
    arg_attrib = ["type"]

    # ------ XML VERIFICATION -------
    # root = program tag (attributes name and description allowed as optonal)
    # inst = instruction tag (attributes order and opcode requested as mandatory)
    # arg = artument tag (attributes type requested as mandatory)

    check_attributes(root.tag,root.attrib,program_attrib)
    for inst in root:
        if inst.tag == "instruction":
            check_attributes(inst.tag, inst.attrib, inst_attrib)
            f_ord = inst.get('order') # tag has order attribute
            if not f_ord: # instruction without order attribute
                sys.stderr.write('ERROR: Invalid XML file ' + str(xml_file) + ' - order attribute missing\n')
                sys.exit(EXIT_CODES['BAD_XML_FORMAT'])
            if not is_int(f_ord): # order attribute valid integer
                sys.stderr.write('ERROR: Invalid XML file ' + str(xml_file) + ' - order attribute is not integer\n')
                sys.exit(EXIT_CODES['BAD_XML_FORMAT'])
            if int(f_ord) < 1 or int(f_ord) > xml_len: # order in interval
                # order out of range
                sys.stderr.write('ERROR: Invalid instruction order: ' + str(f_ord) + "\n")
                sys.exit(EXIT_CODES['BAD_XML_FORMAT'])
            f_name = inst.get('opcode')
            if f_name:  # tag has opcode attribute
                if f_name == "LABEL":
                    lb = True
                # check for valid instruction name
                f_match = dict_find(Instruction.inst_args, f_name)
                if f_match or f_match == "": # valid function
                    arg_num = len(f_match) # gets number of arguments
                    if len(list(inst)) == arg_num: # correct number of arguments
                        tmp_arg_sheme = arg_tags[:arg_num] # allowed arg tags
                        parameter_list = ['x'] * arg_num
                        for arg in inst:
                            if arg.tag in arg_tags: # arg1, arg2, arg3
                                check_attributes(arg.tag, arg.attrib, arg_attrib)
                                try:
                                    tmp_arg_sheme.remove(arg.tag)
                                except ValueError:
                                    sys.stderr.write('ERROR: Instruction: ' + str(f_name) + ' at order: ' + str(f_ord) + ' has invalid argument tag.\n')
                                    sys.exit(EXIT_CODES['BAD_XML_FORMAT'])
                                if arg.get('type') == 'string':
                                    arg.text = correct_string(arg.text)
                                p = Parameter(arg.tag,arg.text,arg.get('type'))
                                if p.check_type(): # checks only according to given type
                                    parameter_list[int(arg.tag[-1]) - 1] = p # index already checked
                                else:
                                    sys.stderr.write('ERROR: Instruction: ' + str(f_name) + ' at order: ' + str(f_ord) + ' argument: ' + str(arg.tag) +' has incompatible type: ' + str(arg.get('type')) + ' with given value: ' + str(arg.text) + "\n")
                                    sys.exit(EXIT_CODES['LEXYCAL_OR_SYNTACTIC_ERROR'])
                            else:
                                sys.stderr.write('ERROR: Instruction: ' + str(f_name) +' at order: ' + str(f_ord) + ' has invalid argument tag.\n')
                                sys.exit(EXIT_CODES['BAD_XML_FORMAT'])
                        # final save to AST as object Instruction (order, function_name, parameter_list)
                        i = Instruction(f_ord, f_name, parameter_list)
                        AST[int(f_ord)-1] = i # index already checked
                        if lb: # save label for jumps
                            l = parameter_list[0].text
                            if l not in label_names:
                                label_names.append(l)
                            else:
                                sys.stderr.write("ERROR: Label '" + str(l) + "' redefinition at instruction order " + str(f_ord) + "\n")
                                sys.exit(EXIT_CODES['SEMANTIC_ERROR'])
                            labels[l] = f_ord
                            lb = False
                    else:
                        # incorrect number of arguments
                        sys.stderr.write('ERROR: Incorrect number of arguments in instruction: ' + str(f_name) + ' - at order: ' + str(f_ord) + " - given: " + str(len(list(inst))) + " (expected " + str(arg_num) + ")\n")
                        sys.exit(EXIT_CODES['LEXYCAL_OR_SYNTACTIC_ERROR'])
                else:
                    # invalid function (not recognized)
                    sys.stderr.write('ERROR: Not recognized instruction: ' + str(f_name) + " at order: " + str(f_ord) + "\n")
                    sys.exit(EXIT_CODES['UNDEFINED_INSTRUCTION'])
            else:
                # instruction without opcode attribute
                sys.stderr.write('ERROR: Invalid XML file: ' + str(xml_file) + ' - opcode attribute missing at order: ' + str(f_ord) + "\n")
                sys.exit(EXIT_CODES['BAD_XML_FORMAT'])
        else: # not instruction tag
            sys.stderr.write('ERROR: Invalid XML file: ' + str(xml_file) + ' - instruction tag: ' + str(inst.tag) + "\n")
            sys.exit(EXIT_CODES['BAD_XML_FORMAT'])

    if 'x' in AST:
        sys.stderr.write('ERROR: Invalid XML file: ' + str(xml_file) + ' - order attributes incorrect\n')
        sys.exit(EXIT_CODES['BAD_XML_FORMAT'])

    jumps = ["CALL", "JUMP", "JUMPIFEQ", "JUMPIFNEQ"]
    for instruction in AST:
        if instruction.name in jumps:
            label_name = instruction.parameter_list[0].text
            if label_name not in labels:
                sys.stderr.write("ERROR: : Nonexistent label'" + str(label_name) + "in instruction at order '" + str(instruction.order) + "'\n")
                sys.exit(EXIT_CODES['SEMANTIC_ERROR'])

    # calling functions
    # i one less than order
    i = 0
    while i < len(AST):
        l = AST[i].call()
        i += 1
        if is_int(str(l)):
            i = l

if __name__ == "__main__":
    main(sys.argv[1:])
