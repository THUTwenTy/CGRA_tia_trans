#!/usr bin/env python3

import numpy as np

base_number = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
tri_operand_ops = {\
    "add", "sub", "sl", "asr", "lsr", "eq", "ne", "sgt", "ugt", "slt", "ult",\
    "sge", "uge", "sle", "ule", "band", "bnand", "bor", "bnor",\
    "bxor", "bxnor", "land", "lnand", "lor", "lnor", "lxor", "lxnor",\
    "gb", "sb", "cb", "mb", "clz", "ctz", "lsw", "ssw", "lmul", "shmul", "uhmul"}

# Op : Instruction
Op_trans_dir = {"add": "add",
                "sub": "sub",
                "mul": "lmul",
                "and": "band",
                "or": "bor",
                "xor": "bxor",
                "shl": "sl",
                "shrl": "asr",
                "icmpeq": "eq",
                "icmpgt": "sgt",
                "icmplt": "slt",
                "output": "output",
                "phi": "phi",
                "comb": "comb",
                "load": "load"
                }

# input match to output channel
channel_match = {   0:2,
                    1:3,
                    2:0,
                    3:1}

class route():

    def __init__(self, op_from, op_to, route_path):
        self.op_from = op_from
        self.op_to = op_to
        self.route_path = route_path
    
    def add_attribute(self, edge_attribute, operand_no_of_dest):
        self.br = -1
        self.operand_no_of_dest = operand_no_of_dest
        if edge_attribute == "T":
            self.br = 1
        elif edge_attribute == "F":
            self.br = 0

class PE_channel():

    def __init__(self, PE_no, channel_no):
        self.PE_no = PE_no
        self.channel_no = channel_no
        self.tag_for_task = []
    
    def apply_new_tag(self, task_no, operand_no):
        self.tag_for_task.append([task_no, operand_no])
        return len(self.tag_for_task)-1

class PE():

    def __init__(self, PE_no):
        self.PE_no = PE_no
        self.inside_ops = []
        self.op_amount = len(self.inside_ops)
        self.input_channel = []
        self.output_channel = []
        for i in range(4):
            self.input_channel.append(PE_channel(PE_no, i))
            self.output_channel.append(PE_channel(PE_no, i))
        self.predicate_reg_unused = [0,0,0,0,0,0,0,0]
        self.base_predicate = [0,0,0,0,0,0,0,0]
        self.last_predicate = [0,0,0,0,0,0,0,0]
        self.inside_map = []
        self.task_list = []
        self.reg_for_task = []
        self.state_list = []
        self.reg_list = []
        self.base_state_no = 0

    def add_inside_op(self, op_no):
        self.inside_ops.append(op_no)
        self.op_amount = len(self.inside_ops)

    def add_inside_map(self, inside_map):
        self.inside_map = inside_map
    
    def apply_new_predicate(self):
        temp = list_8bit_next(self.predicate_reg_unused)
        self.predicate_reg_unused = temp
        return predicate_list_to_str_trans(self.predicate_reg_unused)

    def save_last_predicate(self, last_predicate_str):
        self.last_predicate = predicate_str_to_list_trans(last_predicate_str)

    def update_new_base_predicate(self, new_base_predicate):
        self.base_predicate = predicate_str_to_list_trans(new_base_predicate)
        return self.base_predicate

    def apply_new_reg(self, op_no, operand_no):
        self.reg_for_task.append([op_no, operand_no])

    def rewirte_op_order(self):
        # BFS to design op_order
        new_op_inside = []
        BFS_list = []
        # search for top level
        for i in range(len(self.inside_ops)):
            top_flag = 1
            for j in range(len(self.inside_ops)):
                if self.inside_map[j][i] == 1:
                    top_flag = 0
                    break
            if top_flag == 1:
                #print("top: ", self.inside_ops[i])
                new_op_inside.append(self.inside_ops[i])
                BFS_list.append(self.inside_ops[i])
        while len(BFS_list) > 0:
            old_op_position = self.inside_ops.index(BFS_list[0])
            search_target_position = new_op_inside.index(BFS_list[0])
            for i in range(len(self.inside_ops)):
                if self.inside_map[old_op_position][i] == 1:
                    if self.inside_ops[i] in new_op_inside:
                        # switch position
                        if search_target_position < new_op_inside.index(self.inside_ops[i]):
                            new_op_inside[search_target_position], new_op_inside[new_op_inside.index(self.inside_ops[i])] = \
                            self.inside_ops[i], BFS_list[0]
                    else:
                        new_op_inside.append(self.inside_ops[i])
                    BFS_list.append(self.inside_ops[i])
            del BFS_list[0]
        self.inside_ops = new_op_inside

    def add_task(self, task_type, op_no):
        task_no = len(self.task_list)
        self.task_list.append(PE_task(self.PE_no, task_no, task_type, op_no))

    def add_route_task(self, op_from, op_to, input_channel, output_channel):
        self.add_task("route", op_from)
        single_task = self.task_list[-1]
        single_task.add_input(input_channel, op_from, 0)
        single_task.add_output(output_channel, op_to)
    
    def add_state(self, new_state):
        self.state_list.append(new_state)

    def File_PE_name(self):
        return "<processing_element_" + str(self.PE_no) + ">\n"

class PE_state():

    def __init__(self, state_no, state_operation,\
            trigger_predicate="XXXXXXXX", trigger_channel=-1, trigger_tag=-1, \
            deq_channel=-1, next_predicate="", state_note="PE unused"):
        self.state_no = state_no
        self.state_operation = state_operation # "mov", "add"...
        self.trigger_predicate = trigger_predicate
        self.trigger_channel = trigger_channel
        self.trigger_tag = trigger_tag
        # [0] -> "unused" "i" "o" "r" "p" "const"
        # [1] -> channel_no
        # [2] -> channel_tag 
        self.operand = [["unused", -1, -1], ["unused", -1, -1], ["unused", -1, -1]]
        self.deq_channel = deq_channel
        self.next_predicate = next_predicate
        self.state_note = "# " + state_note
        self.operand_amount = 0

    def add_operand(self, operand, operand_no):
        self.operand[operand_no] = operand # eg: operand[0] = ["i", 1, 0]
        self.operand_amount = self.operand_amount + 1

    def output_str(self):
        File_str = "    " + self.state_note + "\n    when %p == "\
            + self.trigger_predicate
        if self.trigger_channel >= 0:
            File_str = File_str + " with %i" + str(self.trigger_channel)
            if self.trigger_tag >= 0:
                File_str = File_str + "." + str(self.trigger_tag)
        File_str = File_str + ":\n"
        if self.state_operation == "halt":
            File_str = File_str + "        halt;"
        else:
            File_str = File_str + "        " + self.state_operation + " "
            for i in range(self.operand_amount):
                single_operand = self.operand[i]
                if single_operand[0] in ["i", "o", "p", "r"]:
                    File_str = File_str + \
                        "%" + single_operand[0] + str(single_operand[1])
                if single_operand[2] >= 0: # with tag
                    File_str = File_str + \
                            "." + str(single_operand[2])
                elif single_operand[0] in ["const"]:
                    File_str = File_str + "$" + str(single_operand[1])
                if i == self.operand_amount - 1:
                    File_str = File_str + ";"
                    break
                else:
                    File_str = File_str + ", "
        if self.deq_channel >= 0:
            File_str = File_str + " deq %i" + str(self.deq_channel) + ";"
        if self.next_predicate != "": # with next state 
            File_str = File_str + " set %p = " + str(self.next_predicate) + ";"
        File_str = File_str + "\n"
        return File_str


class PE_task():

    def __init__(self, PE_no, task_no, task_type, op_no):
        self.task_no = task_no
        self.PE_no = PE_no
        self.op_no = op_no 
        # -2 means undefined; -1 means route; >0 refers to op_no
        self.input_op_no = [-2, -2, -2]
        self.output_op_no = []
        # -2 means undefined; -1 means from inside; 0~3 refers to channel_no
        self.input_channel = [-2, -2, -2]
        self.output_channel = []
        # -2 means undefined; -1 means from inside
        self.input_channel_tag = [-2, -2, -2] 
        self.output_channel_tag = []
        self.task_type = task_type # "route" or "place"
        self.if_br = 0
    
    def add_br_attribute(self, br_attribute):
        self.if_br = br_attribute # -1 for undefined; o for F; 1 for T
    
    def add_input(self, channel_no, op_from, operand_no):
        self.input_op_no[operand_no] = op_from
        self.input_channel[operand_no] = channel_no
    
    def add_output(self, channel_no, op_to):
        self.output_op_no.append(op_to)
        self.output_channel.append(channel_no)
        self.output_channel_tag.append(-1)

class Op():

    def __init__(self, op_no, op_name, loop_info, op_attribute):
        self.op_no = op_no
        self.op_name = op_name
        self.output_edge = []
        self.input_edge = []
        for i in range(3):
            self.input_edge.append(Op_edge(-1, self.op_no, ""))
        self.attribute = op_attribute
        self.loop_info = self.loop_trans(loop_info)
        self.corresponding_operation = ""
        self.derive_operation()
    
    def add_output(self, op_dest, edge_attribute):
        self.output_edge.append(Op_edge(self.op_no, op_dest, edge_attribute))

    def add_input(self, operand_no, op_source, edge_attribute):
        self.input_edge[operand_no].rewrite(op_source, self.op_no, edge_attribute)

    def op_place(self, PE_no):
        self.PE_place = PE_no

    def loop_trans(self, loop_info):
        if loop_info == "no_loop":
            return -1
        else:
            return int(loop_info.split("_")[1])
    
    def derive_operation(self):
        if self.op_name == "const": # store const value
            self.corresponding_operation = self.attribute
        elif self.op_name == "icmp": # store operation
            self.corresponding_operation = Op_trans_dir[self.op_name+self.attribute]
        else:
            self.corresponding_operation = Op_trans_dir[self.op_name]

class Op_edge():

    def __init__(self, op_from, op_to, edge_attribute):
        self.op_from = op_from
        self.op_to = op_to
        self.edge_attribute = edge_attribute

    def rewrite(self, op_from, op_to, edge_attribute):
        self.op_from = op_from
        self.op_to = op_to
        self.edge_attribute = edge_attribute

def block_str_to_num(block_str):
    line_split_1 = block_str.split("_")
    row_num = int(line_split_1[0]) - 1
    col_num = int(line_split_1[1])
    return 4*row_num + col_num

def derive_PE_dirc(PE_base, PE_relative):
    if PE_relative - PE_base == -4:
        return 0
    elif PE_relative - PE_base == 1:
        return 1
    elif PE_relative - PE_base == 4:
        return 2
    elif PE_relative - PE_base == -1:
        return 3

def derive_PE_neighbor(PE_no, channel_no):
    if channel_no == 0:
        return PE_no - 4
    elif channel_no == 1:
        return PE_no + 1
    elif channel_no == 2:
        return PE_no + 4
    elif channel_no == 3:
        return PE_no - 1

# [1,0,0,0,0,0,0,0] -> 00000001
def predicate_list_to_str_trans(predicate_list):
    File_predicate = ""
    for i in reversed(predicate_list):  # list should be reversed
        File_predicate = File_predicate + str(i)
    return File_predicate

# 00000001 -> [1,0,0,0,0,0,0,0]
def predicate_str_to_list_trans(File_predicate):
    predicate_list = []
    for i in reversed(File_predicate):
        predicate_list.append(int(i))
    return predicate_list

# [1,0,0,0,0,0,0,0] -> [0,1,0,0,0,0,0,0]
def list_8bit_next(list_8bit):
    now_str = "0b" + predicate_list_to_str_trans(list_8bit)
    next_str = bin(int(now_str, 2)+1)[2:]
    while len(next_str) < 8:
        next_str = "0" + next_str
    return predicate_str_to_list_trans(next_str)

# [1,0,0,0,0,0,0,0] -> 0X000001
def predicate_change(predicate_no, predicate_list, character):
    str = predicate_list_to_str_trans(predicate_list)
    return str[0:(7-predicate_no)] + character + str[(8-predicate_no):]