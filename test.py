#!/usr bin/env python3

test = "00000000"
dest = 6
test1 = test[0:(7-dest)]+"Z"+test[(8-dest):]
print(test1)

#print(predicate_list[-1])