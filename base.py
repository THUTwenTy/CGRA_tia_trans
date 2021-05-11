#!/usr bin/env python3

import numpy as np

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
# load, store, comb, phi operation needs extra transform function

operation_no_dir = {"mov": 2,
                    "add": 3,
                    "sub": 3,
                    "sl": 3,
                    "asr": 3,
                    "lsr": 3,
                    "eq": 3,
                    "ne": 3,
                    "sgt": 3,
                    "ugt": 3,
                    "slt": 3,
                    "ult": 3,
                    "sge": 3,
                    "uge": 3,
                    "sle": 3,
                    "ule": 3,
                    "band": 3,
                    "bnand": 3,
                    "bor": 3,
                    "bnor": 3,
                    "bxor": 3,
                    "bxnor": 3,
                    "land": 3,
                    "lnand": 3,
                    "lor": 3,
                    "lnor": 3,
                    "lxor": 3,
                    "lxnor": 3,
                    "gb": 3,
                    "sb": 3,
                    "cb": 3,
                    "mb": 3,
                    "clz": 3,
                    "ctz": 3,
                    "lsw": 3,
                    "ssw": 3,
                    "lmul": 3,
                    "shmul": 3,
                    "uhmul": 3,
                    "nop": 0
                    }

base_number = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}

# input match to output channel
channel_match = {   0:2,
                    1:3,
                    2:0,
                    3:1}

# channels in PE
class PE_channel:

    def __init__(self, PE_index, PE_NESW, in_or_out):
        self.PE_NESW = PE_NESW
        self.PE_index = PE_index
        self.tag_for_task = []
        self.halt_tag_in = 1
        self.in_or_out = in_or_out
        #self.halt_tag_out = len(self.tag_for_state) + 1
        #print("PE_" + str(PE_index) + "_channel_" + str(PE_NESW), "initialized")

    # if add for output_channel, return new tag; if for input_channel, means nothing
    def assign_channel_tag(self, task_no, operand_no):
        self.tag_for_task.append([task_no, operand_no])
        #self.halt_state_out = len(self.tag_for_state) + 1
        return len(self.tag_for_task) - 1
    
    def add_halt_tag_in(self, halt_tag_in):
        self.halt_tag_in = halt_tag_in

class PE():

    def __init__(self, PE_index):
        self.index = PE_index
        self.channel_in = []
        self.channel_out = []
        self.data_reg_used_for = []
        for i in range(4):
            self.channel_in.append(PE_channel(PE_index, i, "in"))
            self.channel_out.append(PE_channel(PE_index, i, "out"))
        self.predicate_reg_unused = [1,0,0,0,0,0,0,0]
        self.base_predicate = [0,0,0,0,0,0,0,0]
        self.halt_state = 0
        self.inside_ops = []
        self.inside_route = []
        self.op_num = 0
        self.task_list = []
        self.state_list = []
        self.base_state = 0

    def add_data_reg(self, task_no, operand_no):
        self.data_reg_used_for.append([task_no, operand_no])

    def update_base_predicate(self, special_predicate):
        if special_predicate == "0": # base_predicate++
            self.base_predicate = self.list_8bit_next(self.base_predicate)
        else: 
            self.base_predicate = special_predicate

    def base_return(self):
        self.base_predicate = self.list_8bit_before(self.base_predicate)

    def add_ops_to_PE(self, op_no):
        self.inside_ops.append(op_no)
        self.op_num = len(self.inside_ops)

    def add_inside_map(self, inside_map):
        self.inside_map = inside_map

    def add_task(self, op_no, task_type):
        self.task_list.append(PE_task(op_no, len(self.task_list), task_type))

    def add_state(self, halt_flag, special_predicate):
        state_no = len(self.state_list)
        if special_predicate == "0": # means normal predicate
            trigger_predicate = self.predicate_list_to_str_trans(self.predicate_reg_unused)
            self.state_list.append(PE_state(state_no, trigger_predicate, halt_flag))
        else:
            self.state_list.append(PE_state(state_no, special_predicate, halt_flag))
        return self.state_list[-1]
    
    def get_new_predicate_unused(self):
        self.predicate_reg_unused = self.list_8bit_next(self.predicate_reg_unused)

    def File_PE_name(self):
        return "<processing_element_" + str(self.index) + ">\n"

    def predicate_list_to_str_trans(self, predicate_list):
        File_predicate = ""
        for i in reversed(predicate_list):  # list should be reversed
            File_predicate = File_predicate + str(i)
        return File_predicate

    def predicate_str_to_list_trans(self, File_predicate):
        predicate_list = []
        for i in reversed(File_predicate):
            predicate_list.append(int(i))
        return predicate_list

    def list_8bit_next(self, list_8bit):
        now_str = "0b" + self.predicate_list_to_str_trans(list_8bit)
        next_str = bin(int(now_str, 2)+1)[2:]
        while len(next_str) < 8:
            next_str = "0" + next_str
        return self.predicate_str_to_list_trans(next_str)

    def list_8bit_before(self, list_8bit):
        now_str = "0b" + self.predicate_list_to_str_trans(list_8bit)
        next_str = bin(int(now_str, 2)-1)[2:]
        while len(next_str) < 8:
            next_str = "0" + next_str
        return self.predicate_str_to_list_trans(next_str)

    def predicate_change(self, predicate_no, predicate_list, character):
        str = self.predicate_list_to_str_trans(predicate_list)
        return str[0:(7-predicate_no)] + character + str[(8-predicate_no):]

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

    def rewirte_task_order(self):
        new_task_list = []
        for i in range(len(self.task_list)):
            new_task_list.append(0)
        i = 0
        for single_task in self.task_list:
            if single_task.task_type == "route":
                # route task arranged at last
                new_task_list[self.op_num+i] = single_task
                single_task.task_no = self.op_num+i
                i = i + 1
            else:
                target_op_position = self.inside_ops.index(single_task.op_no)
                new_task_list[target_op_position] = single_task
                single_task.task_no = target_op_position
        self.task_list = new_task_list

class PE_state():

    def __init__(self, state_no, trigger_predicate, halt_flag):
        self.trigger_predicate = trigger_predicate
        self.state_no = state_no
        # [0] -> channel_no, [1] -> trigger_tag, -1 stands for default
        self.trigger_input = [-1, -1]
        # [0] -> "unused" "i" "o" "r" "p" "const"
        # [1] -> channel_no
        # [2] -> channel_tag 
        self.operand = [["unused", -1, -1], ["unused", -1, -1], ["unused", -1, -1]]
        self.state_operation = ""
        self.next_state_no = -1     # default means no next state
        self.next_state_predicate = ""
        self.operand_num = 0
        self.halt_flag = halt_flag  # means halt_state or not
        self.deq_channel = -1       # default means no deq statement
        self.corresponding_task_no = -1
        self.state_note = "# "

    def add_state_note(self, note):
        self.state_note = self.state_note + note

    def add_corresponding_task_no(self, task_no):
        self.corresponding_task_no = task_no

    def add_next_state_no(self, next_state_no, next_state_predicate):
        self.next_state_no = next_state_no
        self.next_state_predicate = next_state_predicate
    
    def add_state_operation(self, state_operation):
        self.state_operation = state_operation
        self.operand_num = operation_no_dir[state_operation]
    
    def add_trigger_input(self, trigger_input):
        self.trigger_input = trigger_input
    
    def add_operand(self, operand, operand_no):
        self.operand[operand_no] = operand
    
    def add_deq_channel(self, channel_no):
        self.deq_channel = channel_no
    
    def modify_channel_tag(self, operand_no, tag):
        self.operand[operand_no][2] = tag

    def output_str(self):
        File_str = "    " + self.state_note + "\n"
        File_str = File_str + "    when %p == "
        File_str = File_str + self.trigger_predicate
        if self.trigger_input[0] >= 0: # with tag trigger
            File_str = File_str + " with %i" + str(self.trigger_input[0])
            if self.trigger_input[1] >= 0:
                File_str = File_str + "." + str(self.trigger_input[1]) + ":\n"
        else:
            File_str = File_str + ":\n"
        if self.state_operation == "nop":
            File_str = File_str + "        "
        else:
            File_str = File_str + "        " + self.state_operation + " "
            for i in range(self.operand_num):
                single_operand = self.operand[i]
                if single_operand[0] in ["i", "o", "p", "r"]:
                    File_str = File_str + \
                        "%" + single_operand[0] + str(single_operand[1])
                    if single_operand[2] >= 0: # with tag
                        File_str = File_str + \
                            "." + str(single_operand[2])
                elif single_operand[0] in ["const"]:
                    File_str = File_str + "$" + str(single_operand[1])
                elif single_operand[0] in ["unused"]:
                    print("error: port needs definition")
                if i == self.operand_num-1:
                    File_str = File_str + ";"
                    break
                else:
                    File_str = File_str + ", "
        if self.deq_channel >= 0: # with deq statement
            File_str = File_str + " deq %i" + str(self.deq_channel) + ";"
        if self.next_state_no >= 0: # with next state 
            File_str = File_str + " set %p = " + self.next_state_predicate + ";"
        File_str = File_str + "\n"
        return File_str

class PE_task():

    def __init__(self, op_no, task_no, task_type):
        # -2 stands for PE inside
        # -3 stands for undefined
        self.input_channel = [-3, -3]
        # when two input are all from outside_PE, needs to shift one to inside_reg first
        self.input_channel_shift = [-1, -1]
        self.output_channel = []
        self.input_from = [-3, -3]  # op
        self.output_to = []         # op
        self.input_channel_tag = [0, 0] # channel_tag, according to neighbor output channel
        self.output_channel_tag = []    # channel_tag, according to neighbor input channel
        self.op_no = op_no          # works for which op
        self.task_no = task_no
        self.if_br = ""             # help decide br
        self.task_type = task_type  # "route" or "place"
        self.corresponding_state_no = [] 
        # corresponding_state_no == -3 means haven't been transfered to PE_state
        # corresponding_state_no == -2 means no need to arrange single state
        # index of input_channel, input_from, input_channel_tag are related, output is the same

    def shift_channel(self, operand_no, reg_num):
        self.input_channel_shift[operand_no] = reg_num

    def add_input(self, NESW, operand_no, op_from):
        self.input_channel[operand_no] = NESW
        self.input_from[operand_no] = op_from
    
    def add_output(self, NESW, op_to):
        self.output_channel.append(NESW)
        self.output_to.append(op_to)
        if NESW >= 0: # means need output tag
            self.output_channel_tag.append(0)
        else:
            self.output_channel_tag.append(-1)
    
    def add_br_attribute(self, br_attribute):
        self.if_br = br_attribute
    
    def update_state_no(self, state_no):
        self.corresponding_state_no.append(state_no)

    def add_input_tag(self, input_index, tag):
        self.input_channel_tag[input_index] = tag
    
    def add_output_tag(self, output_index, tag):
        self.output_channel_tag[output_index] = tag

class Op_io():

    def __init__(self, Op, i_or_o, PE_index, channel_index, io_attribute):
        self.Op_master = Op
        self.in_or_out = i_or_o
        self.PE_place = PE_index
        self.channel_place = channel_index
        self.io_attribute = io_attribute

class Op_edge():

    def __init__(self, edge_op_in, edge_op_out, edge_attribute):
        self.input = edge_op_in
        self.output = edge_op_out
        self.edge_attribute = edge_attribute
        # edge_attribute[0] = operand(X)    int
        # edge_attribute[1] = br(X)         str

# all op attibutes
class Op():

    def __init__(self, Op_no, Op_name):
        self.Op_Name = Op_name
        self.Op_No = Op_no
        self.input_edge = []
        self.output_edge = []
        self.input_port = []        
        self.output_port = []
        self.route_dest = []
        self.attribute = ""         # eg: predicate == eq
        self.inside_PE_dirc = -1    # output dirction in its PE
        self.corresponding_operation = ""

    def add_attribute(self, op_attribute):
        self.attribute = op_attribute
    
    def add_edge(self, in_or_out, op_other_end, edge_attribute):
        if in_or_out == "in":   
            self.input_edge.append(Op_edge(op_other_end, self.Op_No, edge_attribute))
        else:
            self.output_edge.append(Op_edge(self.Op_No, op_other_end, edge_attribute))

    def add_dest(self, route_dest):
        self.route_dest = route_dest

    def Op_place_to_PE(self, PE_index):
        self.PE_place = PE_index

    def add_inside_PE_dirc(self, NESW):
        self.inside_PE_dirc = NESW
    
    def derive_operation(self):
        if self.Op_Name == "const":
            self.corresponding_operation = self.attribute
        elif self.Op_Name == "icmp":
            self.corresponding_operation = Op_trans_dir[self.Op_Name+self.attribute]
        else:
            self.corresponding_operation = Op_trans_dir[self.Op_Name]

class route():
    
    def __init__(self, op_from, start_PE_no):
        self.op_from = op_from
        self.start_PE_no = start_PE_no
        self.op_to = -1
        self.route_path = []
    
    def add_route_pass(self, PE_no):
        self.route_pass.append(PE_no)

    def add_op_to(self, op_no):
        self.op_to = op_no
    
    def add_edge(self, edge):
        self.edge = edge

def derive_PE_no(block_str):
    no_location = block_str.find("block_")
    if no_location != -1:
        PE_place_row = int(block_str[no_location+6]) - 1
        PE_place_col = int(block_str[no_location+8])
        return PE_place_row * 4 + PE_place_col

def derive_PE_place(PE_no):
    return "block_" + str(PE_no//4+1) + "_" + str(PE_no%4)

def derive_PE_dirc(PE_base, PE_relative):
    if PE_relative - PE_base == -4:
        return 0
    elif PE_relative - PE_base == 1:
        return 1
    elif PE_relative - PE_base == 4:
        return 2
    elif PE_relative - PE_base == -1:
        return 3

def derive_PE_neighbor(PE_now, channel_no):
    if channel_no == 0:
        return PE_now - 4
    elif channel_no == 1:
        return PE_now + 1
    elif channel_no == 2:
        return PE_now + 4
    elif channel_no == 3:
        return PE_now - 1
