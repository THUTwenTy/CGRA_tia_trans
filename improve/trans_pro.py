#!/usr bin/env python3
import base_pro

all_PE      = []
all_Op      = []
all_Route   = []
File_output = ""

def op_add_io(i_or_o, PE_no, op_no, other_PE, other_op, operand_no, br_attribute):
    single_op = all_Op[op_no]
    if single_op.op_name != "const":
        if other_PE == -1: # PE inside
            channel_no = -1
            # reg_for_task store input port info
            if i_or_o == "i" and all_Op[other_op].op_name != "const":
                single_PE = all_PE[PE_no]
                single_PE.apply_new_reg(op_no, operand_no)
        else:
            channel_no = base_pro.derive_PE_dirc(PE_no, other_PE)
        if PE_no <= 16:
            for single_task in all_PE[PE_no].task_list:
                if single_task.op_no == op_no:
                    single_task.add_br_attribute = br_attribute
                    if i_or_o == "i":
                        single_task.add_input(channel_no, other_op, operand_no)
                    elif i_or_o == "o":
                        single_task.add_output(channel_no, other_op)
                    break
    return

def find_related_neighbor_task(PE_no, this_task, output_index):
    output_channel = this_task.output_channel[output_index]
    neighbor_PE_no = base_pro.derive_PE_neighbor(PE_no, output_channel)
    #print(" next_PE: ", neighbor_PE_no)
    if neighbor_PE_no in range(16):
        for single_task in all_PE[neighbor_PE_no].task_list:
            for operand_no in range(len(single_task.input_op_no)):
                if single_task.input_op_no[operand_no] == this_task.op_no and \
                    single_task.input_channel_tag[operand_no] == -2:
                    #print(" find ", this_task.task_type, this_task.op_no, " to ", single_task.op_no)
                    return [neighbor_PE_no, single_task, operand_no]
    return [neighbor_PE_no, -1, -1] # error or out of PE range

def derive_input_operand(single_PE, single_task, operand_no):
    if [single_task.op_no, operand_no] in single_PE.reg_for_task:
        return ["r", single_PE.reg_for_task.index([single_task.op_no, operand_no]), -1]
    if single_task.input_channel[operand_no] < 0: # data from inside PE
        if all_Op[single_task.input_op_no[operand_no]].op_name == "const":
            return ["const", int(all_Op[single_task.input_op_no[operand_no]].corresponding_operation), -1]
    else: # data from outside
        return ["i", single_task.input_channel[operand_no],-1]

def derive_trigger_operand_no(single_PE, single_task):
    # derive the most crowded channel as trigger_input
    trigger_operand_no = -1
    channel_task_amount = -1
    for i in range(3): 
        input_channel_no = single_task.input_channel[i]
        if input_channel_no >= 0:
            print("test")
            this_channel_task_amount = len(single_PE.input_channel[input_channel_no].tag_for_task)
            if this_channel_task_amount > channel_task_amount:
                trigger_operand_no = i
                channel_task_amount = this_channel_task_amount
    print(trigger_operand_no)
    return trigger_operand_no

def derive_output_operand(single_PE, single_task, output_index):
    if single_task.output_channel[output_index] < 0: # data to inside PE
        for single_other_task in single_PE.task_list:
            if single_task.output_op_no[output_index] == single_other_task.op_no:
                input_index = single_other_task.input_op_no.index(single_task.op_no)
                return ["r", single_PE.reg_for_task.index([single_other_task.op_no, input_index]), -1]
    else: # data to outside
        return ["o", single_task.output_channel[output_index], single_task.output_channel_tag[output_index]]

def derive_trigger_predicate(single_PE, operand_type_0, operand_type_1="i"):
    if operand_type_0 == "r" or operand_type_1 == "r":
        return base_pro.predicate_list_to_str_trans(single_PE.last_predicate)
    else:
        return base_pro.predicate_list_to_str_trans(single_PE.base_predicate)

# deal with op_a->op_b->op_c in one PE situation, not capable of op_a->op_b op_a->op_c
def derive_next_predicate(single_PE, output_type):
    if output_type == "r":
        next_predicate = single_PE.apply_new_predicate()
        single_PE.save_last_predicate(next_predicate)
        return next_predicate
    else:
        return base_pro.predicate_list_to_str_trans(single_PE.base_predicate)

# in output_list, if "r" exists, next predicate not the base one
def consistency_check(consistency_flag, new_type):
    if consistency_flag == 1 or new_type == "r":
        consistency_flag = 1
        return 1
    else:
        return 0

File_log = open("log", mode = "r")
raw_log_lines = File_log.readlines()
File_log.close()
File_graph = open("graph_reg.dot", mode = "r")
raw_graph_lines = File_graph.readlines()
File_graph.close()

# deal with raw log file
Operation_Mapping_Result = []
Operation_Mapping_Result_tag = 0
Route_Mapping_Result = []
Route_Mapping_Result_tag = 0
temp_route = ""
for line in raw_log_lines:
    if line == "Operation Mapping Result:\n":
        Operation_Mapping_Result_tag = 1
        continue
    if line == "Connection Mapping Result:\n":
        Operation_Mapping_Result_tag = 0
        Route_Mapping_Result_tag = 1
    if Operation_Mapping_Result_tag == 1:
        if line != "\n":
            Operation_Mapping_Result.append(line)
    if Route_Mapping_Result_tag >= 1:
        if "[INFO]" in line:
            Route_Mapping_Result_tag = 0
            Route_Mapping_Result.append(temp_route)
        elif "->" in line:
            temp_route = line
        elif line == "\n":
            Route_Mapping_Result.append(temp_route)
        else:
            temp_route = temp_route + line

# deal with raw graph file
graph_size = 0
OpName_to_OpNo_dir = {} # eg: "comb16":16
rest_line = ""
i = 0
for line in raw_graph_lines:
    if "loopTag" in line: 
        graph_size = graph_size + 1
        line_split_1 = line.split("[opcode=")
        for i in range(len(line_split_1[0])):
            if line_split_1[0][i] in base_pro.base_number:
                Op_name = line_split_1[0][0:i]
                Op_no = int(line_split_1[0][i:])
                OpName_to_OpNo_dir[line_split_1[0]] = Op_no
                break
        rest_line = line_split_1[1]
        op_attribute = ""
        if "value" in rest_line:
            line_split_2 = rest_line.split("value=")
            line_split_3 = line_split_2[1].split("][",1)
            op_attribute = line_split_3[0]
            rest_line = line_split_3[1]
        elif "predicate" in rest_line:
            line_split_2 = rest_line.split("predicate=")
            line_split_3 = line_split_2[1].split("][",1)
            op_attribute = line_split_3[0]
            rest_line = line_split_3[1]
        line_split_4 = rest_line.split("loopTag=")
        op_loop_info = line_split_4[1].split("]")[0]
        all_Op.append(base_pro.Op(Op_no, Op_name, op_loop_info, op_attribute))
    if "->" in line:
        line_split_5 = line.split("->",1)
        op_from = OpName_to_OpNo_dir[line_split_5[0]]
        line_split_6 = line_split_5[1].split("[operand=")
        op_to = OpName_to_OpNo_dir[line_split_6[0]]
        operand_no = int(line_split_6[1][0])
        if "br" in line_split_6[1]:
            edge_attribute = line_split_6[1].split("br=")[1][0]
        else:
            edge_attribute = ""
        all_Op[op_from].add_output(op_to, edge_attribute)
        all_Op[op_to].add_input(operand_no, op_from, edge_attribute)

# initial graph_matrix
Graph_Matrix = []
for i in range(graph_size):
    temp_Matrix = []
    for j in range(graph_size):
        temp_Matrix.append(0)
    Graph_Matrix.append(temp_Matrix)
# initial all PEs
for i in range(16):
    all_PE.append(base_pro.PE(i))

# store op info
for line in Operation_Mapping_Result:
    line_split_6 = line.split("(")
    op_no = OpName_to_OpNo_dir[line_split_6[0]]
    line_split_7 = line_split_6[1].split("block_")
    block_str = line_split_7[1].split(".",1)[0]
    PE_no = base_pro.block_str_to_num(block_str)
    if PE_no < 16:
        all_PE[PE_no].add_inside_op(op_no)

# fullfil graph_matrix
for single_Op in all_Op:
    op_from = single_Op.op_no
    for single_output_edge in single_Op.output_edge:
        op_to = single_output_edge.op_to
        Graph_Matrix[op_from][op_to] = 1
for i in Graph_Matrix:
    print(i)

# place ops to PEs in order
for single_PE in all_PE:
    PE_inside_map = []
    for i in range(single_PE.op_amount):
        temp_Matrix = []
        for j in range(single_PE.op_amount):
            temp_Matrix.append(Graph_Matrix[single_PE.inside_ops[i]][single_PE.inside_ops[j]])
        PE_inside_map.append(temp_Matrix)
    single_PE.add_inside_map(PE_inside_map)
    PE_inside_map = []
    single_PE.rewirte_op_order()
    for i in range(single_PE.op_amount):
        temp_Matrix = []
        for j in range(single_PE.op_amount):
            temp_Matrix.append(Graph_Matrix[single_PE.inside_ops[i]][single_PE.inside_ops[j]])
        PE_inside_map.append(temp_Matrix)
    single_PE.add_inside_map(PE_inside_map)
    # initial task
    for op_no in single_PE.inside_ops:
        single_op = all_Op[op_no]
        if single_op.op_name == "const":
            continue
        else:
            single_PE.add_task("place", op_no)
            single_task = single_PE.task_list[-1]
    print(single_PE.PE_no, " ops:", single_PE.inside_ops, " :", single_PE.inside_map)
'''
for single_op in all_Op:
    print("op_no: ", single_op.op_no)
    print("op_name: ", single_op.op_name)
    print("input_edge: ")
    for single_input_edge in single_op.input_edge:
        print(" "+str(single_input_edge.op_from)+" "+single_input_edge.edge_attribute)
    print("output_edge: ")
    for single_output_edge in single_op.output_edge:
        print(" "+str(single_output_edge.op_to)+" "+single_output_edge.edge_attribute)
'''
# store route info
for route in Route_Mapping_Result:
    line_split_8 = route.split("\n",1)
    line_split_9 = line_split_8[0].split("_val_output->")
    op_from = OpName_to_OpNo_dir[line_split_9[0]]
    op_to = OpName_to_OpNo_dir[line_split_9[1].split("(")[0]]
    route_PE_list = []
    path = line_split_8[1].split("\n")
    for line in path:
        if "block" in line:
            line_split_10 = line.split("block_")
            block_str = line_split_10[1].split(".",1)[0]
            PE_pass = base_pro.block_str_to_num(block_str)
            if PE_pass not in route_PE_list:
                route_PE_list.append(PE_pass)
    all_Route.append(base_pro.route(op_from, op_to, route_PE_list))

# transform routes to tasks
for single_route in all_Route:
    print("route from op_", single_route.op_from, " to op_", single_route.op_to)
    print("route_path:", single_route.route_path)
    i = 0
    path_len = len(single_route.route_path)
    op_from = single_route.op_from
    op_to = single_route.op_to
    # print("deal with op from ", op_from, " to ", op_to)
    # add attribute to route from graph file
    for single_dest_input_edge in all_Op[single_route.op_to].input_edge:
        if single_dest_input_edge.op_from == single_route.op_from:
            single_route.add_attribute(single_dest_input_edge.edge_attribute, i)
            break
        i = i + 1
    op_operand = single_route.operand_no_of_dest
    br_attribute = single_route.br
    if path_len == 1: # route inside single PE
        PE_no = single_route.route_path[0]
        op_add_io("o", PE_no, op_from, -1, op_to, 0, br_attribute)
        op_add_io("i", PE_no, op_to, -1, op_from, op_operand, br_attribute)
    elif path_len >= 2: # route from one PE to neighbor
        PE_start_from = single_route.route_path[0]
        PE_start_to = single_route.route_path[1]
        PE_end_from = single_route.route_path[-2]
        PE_end_to = single_route.route_path[-1]
        op_add_io("o", PE_start_from, op_from, PE_start_to, op_to, 0, br_attribute)
        op_add_io("i", PE_end_to, op_to, PE_end_from, op_from, op_operand, br_attribute)
        for i in range(path_len-2):
            PE_no = single_route.route_path[i+1]
            input_channel = base_pro.derive_PE_dirc(PE_no, single_route.route_path[i])
            output_channel = base_pro.derive_PE_dirc(PE_no, single_route.route_path[i+2])
            all_PE[PE_no].add_route_task(op_from, op_to, input_channel, output_channel)
for single_PE in all_PE:
    print("PE_no", single_PE.PE_no)
    for single_task in single_PE.task_list:
        # go through every output to find related channel, and set channel tag for both
        for output_index in range(len(single_task.output_channel)):
            single_channel = single_PE.output_channel[single_task.output_channel[output_index]]
            [PE_dest_no, dest_task, operand_no] = find_related_neighbor_task(single_PE.PE_no, single_task, output_index)
            channel_tag = single_channel.apply_new_tag(single_task.task_no, operand_no)
            single_task.output_channel_tag[output_index] = channel_tag 
            if operand_no >= 0:
                dest_task.input_channel_tag[operand_no] = channel_tag

# transform tasks to states
for single_PE in all_PE:
    print("PE_no: ", single_PE.PE_no)
    print("  inside_ops: ", single_PE.inside_ops)
    print("  inside_map: ", single_PE.inside_map)
    print("  task_list:")
    if len(single_PE.task_list) == 0:
        new_state = base_pro.PE_state(0, "halt")
        single_PE.add_state(new_state)
    for single_task in single_PE.task_list:
        state_no = len(single_PE.state_list)
        print("    task_no: ", single_task.task_no)
        print("      task_op: ", single_task.op_no)
        print("      input_op_no: ", single_task.input_op_no)
        print("      output_op_no: ", single_task.output_op_no)
        print("      input_channel: ", single_task.input_channel)
        print("      output_channel: ", single_task.output_channel)
        print("      if_br: ", single_task.if_br)
        print("      input_channel_tag: ", single_task.input_channel_tag)
        print("      output_channel_tag: ", single_task.output_channel_tag)
        if single_task.task_type == "route":
            # add route state
            new_state_note = "route op_" + str(single_task.input_op_no[0]) \
                + " to op_" + str(single_task.output_op_no[0])
            new_state_operation = "mov"
            new_trigger_channel = single_task.input_channel[0]
            new_trigger_tag = single_task.input_channel_tag[0]
            new_deq_channel = single_task.input_channel[0]
            new_state = base_pro.PE_state(state_no, new_state_operation,\
                trigger_channel=new_trigger_channel, trigger_tag=new_trigger_tag, \
                deq_channel=new_deq_channel, state_note=new_state_note)
            input_operand = derive_input_operand(single_PE, single_task, 0)
            output_operand = derive_output_operand(single_PE, single_task, 0)
            new_state.add_operand(input_operand, 1)
            new_state.add_operand(output_operand, 0)
            single_PE.add_state(new_state)
        elif all_Op[single_task.op_no].corresponding_operation in base_pro.tri_operand_ops:
            single_op = all_Op[single_task.op_no]
            new_state_note = "place op_" + single_op.op_name + str(single_op.op_no)
            new_state_op = all_Op[single_task.op_no].corresponding_operation
            new_state_operation = single_op.corresponding_operation
            trigger_operand_no = derive_trigger_operand_no(single_PE, single_task)
            if trigger_operand_no >= 0: # has input from outside
                new_trigger_channel = single_task.input_channel[trigger_operand_no]
                new_trigger_tag = single_task.input_channel_tag[trigger_operand_no]
            else:
                new_trigger_channel = -1
                new_trigger_tag = -1
            input_operand_0 = derive_input_operand(single_PE, single_task, 0)
            input_operand_1 = derive_input_operand(single_PE, single_task, 1)
            new_trigger_predicate = derive_trigger_predicate(single_PE, input_operand_0[0], operand_type_1=input_operand_1[0])
            output_amount = len(single_task.output_op_no)
            if output_amount == 1: # single output means single state
                new_deq_channel = new_trigger_channel
                output_operand = derive_output_operand(single_PE, single_task, 0)
                new_next_predicate = derive_next_predicate(single_PE, output_operand[0])
                new_state = base_pro.PE_state(state_no, new_state_operation,\
                    trigger_predicate=new_trigger_predicate, trigger_channel=new_trigger_channel, trigger_tag=new_trigger_tag, \
                    deq_channel=new_deq_channel, next_predicate=new_next_predicate, state_note=new_state_note)
                new_state.add_operand(input_operand_0, 1)
                new_state.add_operand(input_operand_1, 2)
                new_state.add_operand(output_operand, 0)
                single_PE.add_state(new_state)
            else: # more than one output, needs extra states
                consistency_flag = 0
                new_state_note = "place op_" + single_op.op_name + str(single_op.op_no)
                new_next_predicate = single_PE.apply_new_predicate()
                new_state = base_pro.PE_state(state_no, new_state_operation,\
                    trigger_predicate=new_trigger_predicate, trigger_channel=new_trigger_channel, trigger_tag=new_trigger_tag, \
                    next_predicate=new_next_predicate, state_note=new_state_note)
                output_operand = derive_output_operand(single_PE, single_task, 0)
                consistency_check(consistency_flag, output_operand[0])
                new_state.add_operand(input_operand_0, 1)
                new_state.add_operand(input_operand_1, 2)
                new_state.add_operand(output_operand, 0)
                single_PE.add_state(new_state)
                for i in range(output_amount-2):
                    new_state_note = "op_" + single_op.op_name + str(single_op.op_no) + " other outputs"
                    state_no = len(single_PE.state_list)
                    new_trigger_predicate = new_next_predicate
                    new_next_predicate = single_PE.apply_new_predicate()
                    new_state = base_pro.PE_state(state_no, new_state_operation,\
                        trigger_predicate=new_trigger_predicate, next_predicate=new_next_predicate, state_note=new_state_note)
                    output_operand = derive_output_operand(single_PE, single_task, i)
                    consistency_check(consistency_flag, output_operand[0])
                    new_state.add_operand(input_operand_0, 1)
                    new_state.add_operand(input_operand_1, 2)
                    new_state.add_operand(output_operand, 0)
                    single_PE.add_state(new_state)
                new_state_note = "op_" + single_op.op_name + str(single_op.op_no) + " other outputs"
                state_no = len(single_PE.state_list)
                new_trigger_predicate = new_next_predicate
                output_operand = derive_output_operand(single_PE, single_task, output_amount-1)
                if consistency_check(consistency_flag, output_operand[0]) == 1:
                    next_predicate = single_PE.apply_new_predicate()
                    new_next_predicate = single_PE.save_last_predicate(next_predicate)
                else:
                    new_next_predicate = base_pro.predicate_list_to_str_trans(single_PE.base_predicate)
                new_deq_channel = new_trigger_channel
                new_state = base_pro.PE_state(state_no, new_state_operation,\
                    trigger_predicate=new_trigger_predicate, deq_channel=new_deq_channel, next_predicate=new_next_predicate, state_note=new_state_note)
                new_state.add_operand(input_operand_0, 1)
                new_state.add_operand(input_operand_1, 2)
                new_state.add_operand(output_operand, 0)
                single_PE.add_state(new_state)
        elif all_Op[single_task.op_no].corresponding_operation == "phi":
            single_op = all_Op[single_task.op_no]
            new_state_note = "phi" + str(single_op.op_no) + " initial"
            state_operation = "mov"
            new_trigger_predicate = base_pro.predicate_list_to_str_trans(single_PE.base_predicate)
            output_amount = len(single_task.output_op_no)
            input_operand_0 = derive_input_operand(single_PE, single_task, 0)
            input_operand_1 = derive_input_operand(single_PE, single_task, 1)
            new_trigger_channel_1 = single_task.input_channel[1]
            new_trigger_tag_1 = single_task.input_channel_tag[1]
            new_trigger_channel_0 = single_task.input_channel[0]
            new_trigger_tag_0 = single_task.input_channel_tag[0]
            new_next_predicate = single_PE.apply_new_predicate()
            output_operand = derive_output_operand(single_PE, single_task, 0)
            if output_amount <= 1: # only one output, two states
                new_deq_channel = new_trigger_channel_1
                new_state = base_pro.PE_state(state_no, state_operation,\
                    trigger_predicate=new_trigger_predicate, trigger_channel=new_trigger_channel_1, trigger_tag=new_trigger_tag_1, \
                    deq_channel=new_deq_channel, next_predicate=new_next_predicate, state_note=new_state_note)
                new_state.add_operand(input_operand_1, 1)
                new_state.add_operand(output_operand, 0)
                single_PE.add_state(new_state)
                new_state_note = "phi" + str(single_op.op_no) + " other rounds"
                state_no = len(single_PE.state_list)
                new_trigger_predicate = new_next_predicate
                new_deq_channel = new_trigger_channel_0
                new_next_predicate = derive_next_predicate(single_PE, output_operand[0])
                new_state = base_pro.PE_state(state_no, state_operation,\
                    trigger_predicate=new_trigger_predicate, trigger_channel=new_trigger_channel_0, trigger_tag=new_trigger_tag_0, \
                    deq_channel=new_trigger_channel_0, next_predicate=new_next_predicate, state_note=new_state_note)
                new_state.add_operand(input_operand_0, 1)
                new_state.add_operand(output_operand, 0)
                single_PE.add_state(new_state)
            else: # more than one output, twice states
                consistency_flag = 0
                new_state = base_pro.PE_state(state_no, state_operation,\
                    trigger_predicate=new_trigger_predicate, trigger_channel=new_trigger_channel_1, trigger_tag=new_trigger_tag_1, \
                    next_predicate=new_next_predicate, state_note=new_state_note)
                new_state.add_operand(input_operand_1, 1)
                new_state.add_operand(output_operand, 0)
                single_PE.add_state(new_state)
                for i in range(output_amount-2):
                    state_no = len(single_PE.state_list)
                    output_operand = derive_output_operand(single_PE, single_task, i+1)
                    new_trigger_predicate = new_next_predicate
                    new_next_predicate = single_PE.apply_new_predicate()
                    new_state = base_pro.PE_state(state_no, state_operation,\
                        trigger_predicate=new_trigger_predicate,\
                        next_predicate=new_next_predicate, state_note=new_state_note)
                    new_state.add_operand(input_operand_1, 1)
                    new_state.add_operand(output_operand, 0)
                    single_PE.add_state(new_state)
                state_no = len(single_PE.state_list)
                output_operand = derive_output_operand(single_PE, single_task, output_amount-1)
                new_trigger_predicate = new_next_predicate
                new_next_predicate = single_PE.apply_new_predicate()
                single_PE.update_new_base_predicate(new_next_predicate)
                new_deq_channel = new_trigger_channel_1
                new_state = base_pro.PE_state(state_no, state_operation,\
                    trigger_predicate=new_trigger_predicate,\
                    deq_channel=new_deq_channel, next_predicate=new_next_predicate, state_note=new_state_note)
                new_state.add_operand(input_operand_1, 1)
                new_state.add_operand(output_operand, 0)
                single_PE.add_state(new_state)
                # other rounds
                new_state_note = "phi" + str(single_op.op_no) + " other rounds"
                state_no = len(single_PE.state_list)
                new_trigger_predicate = new_next_predicate
                new_next_predicate = single_PE.apply_new_predicate()
                output_operand = derive_output_operand(single_PE, single_task, 0)
                consistency_check(consistency_flag, output_operand[0])
                new_state = base_pro.PE_state(state_no, state_operation,\
                    trigger_predicate=new_trigger_predicate, trigger_channel=new_trigger_channel_0, trigger_tag=new_trigger_tag_0, \
                    next_predicate=new_next_predicate, state_note=new_state_note)
                new_state.add_operand(input_operand_0, 1)
                new_state.add_operand(output_operand, 0)
                single_PE.add_state(new_state)
                for i in range(output_amount-2):
                    state_no = len(single_PE.state_list)
                    new_trigger_predicate = new_next_predicate
                    new_next_predicate = single_PE.apply_new_predicate()
                    output_operand = derive_output_operand(single_PE, single_task, i+1)
                    consistency_check(consistency_flag, output_operand[0])
                    new_state = base_pro.PE_state(state_no, state_operation,\
                        trigger_predicate=new_trigger_predicate,\
                        next_predicate=new_next_predicate, state_note=new_state_note)
                    new_state.add_operand(input_operand_0, 1)
                    new_state.add_operand(output_operand, 0)
                    single_PE.add_state(new_state)
                state_no = len(single_PE.state_list)
                output_operand = derive_output_operand(single_PE, single_task, output_amount-1)
                if consistency_check(consistency_flag, output_operand[0]) == 1:
                    next_predicate = single_PE.apply_new_predicate()
                    new_next_predicate = single_PE.save_last_predicate(next_predicate)
                else:
                    new_next_predicate = base_pro.predicate_list_to_str_trans(single_PE.base_predicate)
                single_PE.update_new_base_predicate(new_next_predicate)
                new_deq_channel = new_trigger_channel_0
                new_state = base_pro.PE_state(state_no, state_operation,\
                    trigger_predicate=new_trigger_predicate,\
                    deq_channel=new_deq_channel, next_predicate=new_next_predicate, state_note=new_state_note)
                new_state.add_operand(input_operand_0, 1)
                new_state.add_operand(output_operand, 0)
                single_PE.add_state(new_state)
        elif all_Op[single_task.op_no].corresponding_operation == "load":
            single_op = all_Op[single_task.op_no]
            new_state_note = "place op_" + single_op.op_name + str(single_op.op_no)
            state_operation = "mov"
            new_trigger_channel = derive_trigger_operand_no(single_PE, single_task)
            new_deq_channel = new_trigger_channel
            new_trigger_tag = single_task.input_channel_tag[0]
            output_amount = len(single_task.output_op_no)
            input_operand_0 = derive_input_operand(single_PE, single_task, 0)
            output_operand = derive_output_operand(single_PE, single_task, 0)    
            new_trigger_predicate = derive_trigger_predicate(single_PE, input_operand_0[0])
            new_next_predicate = base_pro.predicate_list_to_str_trans(single_PE.base_predicate)
            new_state = base_pro.PE_state(state_no, state_operation,\
                trigger_predicate=new_trigger_predicate, trigger_channel=new_trigger_channel, trigger_tag=new_trigger_tag, \
                deq_channel=new_deq_channel, next_predicate=new_next_predicate, state_note=new_state_note)
            new_state.add_operand(input_operand_0, 1)
            new_state.add_operand(output_operand, 0)
            single_PE.add_state(new_state)
            # receive data
            state_no = len(single_PE.state_list)
            input_operand_0 = ["i", 0, -1]
            new_trigger_predicate = base_pro.predicate_list_to_str_trans(single_PE.base_predicate)
            new_state_note = "receive load data"
            output_operand = derive_output_operand(single_PE, single_task, 0)
            new_next_predicate = derive_next_predicate(single_PE, output_operand[0])
            if output_amount <= 1: # only one output
                new_state = base_pro.PE_state(state_no, state_operation,\
                    trigger_channel=0, trigger_tag=0, \
                    deq_channel=0, state_note=new_state_note)
                new_state.add_operand(input_operand_0, 1)
                new_state.add_operand(output_operand, 0)
                single_PE.add_state(new_state)
            else:
                consistency_flag = 0
                consistency_check(consistency_flag, output_operand[0])
                new_next_predicate = single_PE.apply_new_predicate()
                new_state = base_pro.PE_state(state_no, state_operation,\
                    trigger_predicate=new_trigger_predicate, trigger_channel=0, trigger_tag=0, \
                    next_predicate=new_next_predicate, state_note=new_state_note)
                new_state.add_operand(input_operand_0, 1)
                new_state.add_operand(output_operand, 0)
                single_PE.add_state(new_state)
                for i in range(output_amount-2):
                    state_no = len(single_PE.state_list)
                    new_trigger_predicate = new_next_predicate
                    new_next_predicate = single_PE.apply_new_predicate()
                    output_operand = derive_output_operand(single_PE, single_task, i)
                    consistency_check(consistency_flag, output_operand[0])
                    new_state = base_pro.PE_state(state_no, state_operation,\
                        next_predicate=new_next_predicate, state_note=new_state_note)
                    new_state.add_operand(input_operand_0, 1)
                    new_state.add_operand(output_operand, 0)
                    single_PE.add_state(new_state)
                state_no = len(single_PE.state_list)
                new_trigger_predicate = new_next_predicate
                output_operand = derive_output_operand(single_PE, single_task, output_amount-1)
                if consistency_check(consistency_flag, output_operand[0]) == 1:
                    next_predicate = single_PE.apply_new_predicate()
                    new_next_predicate = single_PE.save_last_predicate(next_predicate)
                else:
                    new_next_predicate = base_pro.predicate_list_to_str_trans(single_PE.base_predicate)
                new_state = base_pro.PE_state(state_no, state_operation,\
                    trigger_predicate=new_trigger_predicate, trigger_channel=new_trigger_channel, trigger_tag=new_trigger_tag, \
                    deq_channel=new_deq_channel, next_predicate=new_next_predicate, state_note=new_state_note)
                new_state.add_operand(input_operand_0, 1)
                new_state.add_operand(output_operand, 0)
                single_PE.add_state(new_state)
        elif all_Op[single_task.op_no].corresponding_operation == "comb":
            single_op = all_Op[single_task.op_no]
            new_state_note = "place op_" + single_op.op_name + str(single_op.op_no) + str(single_Op.attribute)
            print(new_state_note)

            
                    
for single_PE in all_PE:
    print("PE:", single_PE.PE_no, " state length:", len(single_PE.state_list))
    File_output = File_output + single_PE.File_PE_name()
    for single_state in single_PE.state_list:
        File_output = File_output + single_state.output_str()
        print(" state", single_state.state_no, " is ready")
    File_output = File_output + "\n"

File_write_to = open("output_file.tia", mode="w")
File_write_to.write(File_output)
File_write_to.close()