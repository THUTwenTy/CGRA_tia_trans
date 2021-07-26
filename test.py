#!/usr bin/env python3

def predicate_list_to_str_trans(predicate_list):
    File_predicate = ""
    for i in reversed(predicate_list):  # list should be reversed
        File_predicate = File_predicate + str(i)
    return File_predicate

def predicate_str_to_list_trans(File_predicate):
    predicate_list = []
    for i in reversed(File_predicate):
        predicate_list.append(int(i))
    return predicate_list

def list_8bit_next(list_8bit):
    now_str = "0b" + predicate_list_to_str_trans(list_8bit)
    next_str = bin(int(now_str, 2)+1)[2:]
    while len(next_str) < 8:
        next_str = "0" + next_str
    return predicate_str_to_list_trans(next_str)

def predicate_change(predicate_no, predicate_list, character):
    str = predicate_list_to_str_trans(predicate_list)
    return str[0:(7-predicate_no)] + character + str[(8-predicate_no):]

def test(a, b=1, c=2):
    print(a+b+2*c)

predicate_reg_unused = list_8bit_next([0,0,0,0,0,0,0,0])
#print(predicate_list_to_str_trans(predicate_reg_unused))

def test(a, b):
    a = 1
a = 2
test(a, 3)
print(a)
#print(predicate_change(5, [1,0,0,0,0,0,0,0], "X"))