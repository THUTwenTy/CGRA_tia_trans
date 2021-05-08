#!/usr bin/env python3

import base

all_PE = []                 # store all PEs info
all_Op = []                 # store all Ops info
all_Route = []              # store all routes info
File_output = ""            # store output total str

File_log = open("log", mode = "r")
raw_log_lines = File_log.readlines()
File_log.close()

File_graph = open("graph_reg.dot", mode = "r")
raw_graph_lines = File_graph.readlines()
File_graph.close()    

# deal with raw log file
Operation_Mapping_Result = []
Operation_Mapping_Result_tag = 0
Connection_Mapping_Result = {}
Connection_Mapping_Result_tag = 0
temp_val_name = ""
temp_val_route = ""
for line in raw_log_lines:
    if line == "Operation Mapping Result:\n":
        Operation_Mapping_Result_tag = 1
        continue
    if line == "Connection Mapping Result:\n":
        Operation_Mapping_Result_tag = 0
        Connection_Mapping_Result_tag = 1
        continue
    if Operation_Mapping_Result_tag == 1:
        if line != "\n":
            Operation_Mapping_Result.append(line)
    if Connection_Mapping_Result_tag == 1:
        if "output:" in line:
            Connection_Mapping_Result[temp_val_name] = temp_val_route
            temp_val_route = ""
            temp_val_name = line
        if "0:" in line:
            temp_val_route = temp_val_route + line
Connection_Mapping_Result[temp_val_name] = temp_val_route
del Connection_Mapping_Result[""]

# deal with raw graph
graph_size = 0  
OpName_to_OpNo_dir = {}      # eg: "comb16":16
for line in raw_graph_lines:
    if ";" in line:
        # Ops info
        if "->" not in line:
            graph_size = graph_size + 1
            line_split_1 = line.split("[opcode=")
            for i in range(len(line_split_1[0])):
                if line_split_1[0][i] in base.base_number:
                    Op_name = line_split_1[0][0:i]
                    Op_no = int(line_split_1[0][i:])
                    all_Op.append(base.Op(Op_no, Op_name))
                    OpName_to_OpNo_dir[line_split_1[0]] = Op_no
                    break
            if "][" in line_split_1[1]:
                line_split_2 = line_split_1[1].split("=")
                line_split_3 = line_split_2[1].split("]")
                all_Op[graph_size-1].add_attribute(line_split_3[0])
            all_Op[-1].derive_operation()
            print("op_", all_Op[-1].Op_No, ": ", all_Op[-1].corresponding_operation)
OpNo_to_OpNane_dir = {v:k for k,v in OpName_to_OpNo_dir.items()}

# initial graph_matrix
Graph_Matrix = []
for i in range(graph_size):
    temp_Matrix = []
    for j in range(graph_size):
        temp_Matrix.append(0)
    Graph_Matrix.append(temp_Matrix)

# produce graph
for line in raw_graph_lines:
    if ";" in line:
        # connections info
        if "->" in line:
            edge_attribute_list = []
            line_split_4 = line.split("->", 1)
            edge_input_no = OpName_to_OpNo_dir[line_split_4[0]]
            line_split_5 = line_split_4[1].split("[operand=")
            edge_output_no = OpName_to_OpNo_dir[line_split_5[0]]
            edge_attribute_list.append(int(line_split_5[1][0]))
            Graph_Matrix[edge_input_no][edge_output_no] = 1
            if "][" in line_split_5[1]:
                line_split_6 = line_split_5[1].split("=")
                edge_attribute_list.append(line_split_6[1][0])
            all_Op[edge_input_no].add_edge("out", edge_output_no, edge_attribute_list)
            all_Op[edge_output_no].add_edge("in", edge_input_no, edge_attribute_list)

for i in Graph_Matrix:
    print(i)

# initial all PEs
for i in range(16):
    all_PE.append(base.PE(i))

# place ops to PEs
for i in Operation_Mapping_Result:
    line_split_7 = i.split("(")
    Op_no = OpName_to_OpNo_dir[line_split_7[0]]
    line_split_8 = line_split_7[1].split("block_")
    PE_place_row = int(line_split_8[1][0]) - 1
    PE_place_col = int(line_split_8[1][2])
    PE_place = PE_place_row * 4 + PE_place_col
    if PE_place < 16:
        #print("place op_no."+str(Op_no)+" in PE_"+str(PE_place))
        all_PE[PE_place].add_ops_to_PE(Op_no)
    all_Op[Op_no].Op_place_to_PE(PE_place)
for single_PE in all_PE:
    PE_inside_map = []
    for i in range(single_PE.op_num):
        temp_Matrix = []
        for j in range(single_PE.op_num):
            temp_Matrix.append(Graph_Matrix[single_PE.inside_ops[i]][single_PE.inside_ops[j]])
        PE_inside_map.append(temp_Matrix)
    single_PE.add_inside_map(PE_inside_map)
    PE_inside_map = []
    single_PE.rewirte_op_order()
    for i in range(single_PE.op_num):
        temp_Matrix = []
        for j in range(single_PE.op_num):
            temp_Matrix.append(Graph_Matrix[single_PE.inside_ops[i]][single_PE.inside_ops[j]])
        PE_inside_map.append(temp_Matrix)
    single_PE.add_inside_map(PE_inside_map)
    print(single_PE.index, " ops:", single_PE.inside_ops, single_PE.inside_map)

# deal with route
for single_output_route in Connection_Mapping_Result.keys():
    line_split_9 = single_output_route.split("_val_output:")
    route_from = OpName_to_OpNo_dir[line_split_9[0]]
    route_path_raw = Connection_Mapping_Result[single_output_route].split("\n")
    route_dest = []
    for i in range(graph_size):
        if Graph_Matrix[route_from][i] == 1:
            route_dest.append(all_Op[i].PE_place)
    all_Route.append(base.route(route_from, all_Op[route_from].PE_place))
    last_route_path = ""
    all_Route[-1].route_path.append(all_Op[route_from].PE_place)
    for single_route_path in route_path_raw:
        if "block_" in single_route_path:
            PE_route_pass_before = base.derive_PE_no(last_route_path)
            PE_route_pass = base.derive_PE_no(single_route_path)
            if all_Op[route_from].PE_place != PE_route_pass: # not start PE
                if PE_route_pass != PE_route_pass_before: # pass a new PE
                    if ".out" in last_route_path: # from a PE_out, means path go on
                        all_Route[-1].route_path.append(PE_route_pass)
                    else: # means last path is over, needs to create a new path
                        route_last_PE = base.derive_PE_neighbor(PE_route_pass, int(single_route_path[-1]))
                        all_Route.append(base.route(route_from, all_Op[route_from].PE_place))
                        for single_route_before in all_Route[-2].route_path:
                            if single_route_before != route_last_PE:
                                all_Route[-1].route_path.append(single_route_before)
                            else:
                                all_Route[-1].route_path.append(single_route_before)
                                break
                        all_Route[-1].route_path.append(PE_route_pass)
        last_route_path = single_route_path

for single_route in all_Route:
    # add op_to & edge attribute to each route
    for single_op_output_edge in all_Op[single_route.op_from].output_edge:
        if single_route.route_path[-1] == all_Op[single_op_output_edge.output].PE_place:
            single_route.add_op_to(single_op_output_edge.output)
            single_route.add_edge(single_op_output_edge)
    # assign route to PEs
    if len(single_route.route_path) > 1: 
        single_route_start_PE_no = single_route.route_path[0]
        start_NESW = base.derive_PE_dirc(single_route.route_path[0], single_route.route_path[1])
        single_route_end_PE_no = single_route.route_path[-1]
        end_NESW = base.derive_PE_dirc(single_route.route_path[-1], single_route.route_path[-2])
        task_existed_flag = 0
        # add task to PE_start
        for single_task in all_PE[single_route_start_PE_no].task_list:
            if single_route.op_from == single_task.op_no: # task already existed, add edge
                single_task.add_output(start_NESW, single_route.op_to)
                print("PE", single_route_start_PE_no, " task", single_task.task_no, " existed, op:", single_task.op_no)
                task_existed_flag = 1
        if task_existed_flag == 0: # task not exist, create new one
            all_PE[single_route_start_PE_no].add_task(single_route.op_from, "place")
            all_PE[single_route_start_PE_no].task_list[-1].add_output(start_NESW, single_route.op_to)
            print("create PE", single_route_start_PE_no, " op:", all_PE[single_route_start_PE_no].task_list[-1].op_no)
        # add task to PE_end
        if single_route_end_PE_no > 15: # output 
            test = 1
        else:
            task_existed_flag = 0
            for single_task in all_PE[single_route_end_PE_no].task_list:
                if single_route.op_to == single_task.op_no: # task already existed, add edge
                    single_task.add_input(end_NESW, single_route.edge.edge_attribute[0], single_route.op_from)
                    if len(single_route.edge.edge_attribute) > 1: # have br attribute
                        single_task.add_br_attribute(single_route.edge.edge_attribute[1])
                    print("PE", single_route_end_PE_no, " task", single_task.task_no, " existed, op:", single_task.op_no)
                    task_existed_flag = 1
            if task_existed_flag == 0: # task not exist, create new one
                all_PE[single_route_end_PE_no].add_task(single_route.op_to, "place")
                all_PE[single_route_end_PE_no].task_list[-1].add_input(end_NESW, single_route.edge.edge_attribute[0], single_route.op_from)
                print("create PE", single_route_end_PE_no, " op:", all_PE[single_route_end_PE_no].task_list[-1].op_no)
                if len(single_route.edge.edge_attribute) > 1: # have br attribute
                    single_task.add_br_attribute(single_route.edge.edge_attribute[1])
        if len(single_route.route_path) > 2: # needs other PEs to route
            for i in range(len(single_route.route_path)-2):
                single_route_PE_from = single_route.route_path[i]
                single_route_PE_mid = single_route.route_path[i+1]
                single_route_PE_to = single_route.route_path[i+2]
                input_dirc = base.derive_PE_dirc(single_route_PE_mid, single_route_PE_from)
                output_dirc = base.derive_PE_dirc(single_route_PE_mid, single_route_PE_to)
                all_PE[single_route_PE_mid].add_task(single_route.op_from, "route")
                all_PE[single_route_PE_mid].task_list[-1].add_input(input_dirc, 0, single_route.op_from)
                all_PE[single_route_PE_mid].task_list[-1].add_output(output_dirc, single_route.op_to)
                print("create route task, PE:", single_route_PE_mid, "from ", all_PE[single_route_PE_mid].task_list[-1].input_channel, " to ", all_PE[single_route_PE_mid].task_list[-1].output_channel)
    else: # len(route_path) <= 1 means route inside one PE
        single_route_path_PE = single_route.route_path[0]
        task_from_existed_flag = 0
        task_to_existed_flag = 0
        for single_task in all_PE[single_route_path_PE].task_list:
            if single_route.op_from == single_task.op_no: 
                single_task.add_output(-2, single_route.op_to)
                task_from_existed_flag = 1
                print("PE", single_route_path_PE, " task", single_task.task_no, " existed, op:", single_task.op_no)
            if single_route.op_to == single_task.op_no:
                single_task.add_input(-2, single_route.edge.edge_attribute[0], single_route.op_from)
                task_to_existed_flag = 1
                print("PE", single_route_path_PE, " task", single_task.task_no, " existed, op:", single_task.op_no)
        if task_from_existed_flag == 0:
            all_PE[single_route_path_PE].add_task(single_route.op_from, "place")
            all_PE[single_route_path_PE].task_list[-1].add_output(-2, single_route.op_to)
            print("create PE", single_route_path_PE, " op:", all_PE[single_route_path_PE].task_list[-1].op_no)
        if task_to_existed_flag == 0:
            all_PE[single_route_path_PE].add_task(single_route.op_to, "place")
            all_PE[single_route_path_PE].task_list[-1].add_input(-2, single_route.edge.edge_attribute[0], single_route.op_from)
            print("create PE", single_route_path_PE, " op:", all_PE[single_route_path_PE].task_list[-1].op_no)
    print("from ", single_route.start_PE_no, " to ", single_route.route_path, ":", single_route.op_from, "->", single_route.op_to, "\n")
#print(OpName_to_OpNo_dir)

for single_PE in all_PE:
    print("PE_", single_PE.index, ":")
    single_PE.rewirte_task_order()
    for single_task in single_PE.task_list:
        print("    No.", single_task.task_no, "task: ")
        print("      op: ", single_task.op_no)
        print("      task_type: ", single_task.task_type)
        print("      input_channel: ", single_task.input_channel)
        print("      input_op:", single_task.input_from)
        print("      output_channel: ", single_task.output_channel)
        print("      output_op:", single_task.output_to)
        for task_output in single_task.output_channel:
            single_PE.
        if len(single_PE.task_list) == 1: 
            if single_task.task_type == "route":
                # only one task, means predeicate = XXXXXXXX
                now_state = single_PE.add_state(0, "XXXXXXXX")
                # add route state
                now_state.add_state_operation("mov")
                trigger_input = [single_task.input_channel[0], single_task.input_channel_tag[0]]
                now_state.add_trigger_input(trigger_input)
                now_state.add_operand(["i", single_task.input_channel[0], -1], 1)
                now_state.add_operand(["o", single_task.output_channel[0], single_task.output_channel_tag[0]], 0)
                now_state.add_deq_channel(single_task.input_channel[0])
                # bind task and state
                now_state.add_corresponding_task_no(single_task.task_no)
                single_task.update_state_no(now_state.state_no)
                # update next PE's corresponding task tag
                next_PE_no = base.derive_PE_neighbor(single_PE.index, single_task.output_channel[0])
                for single_task_next_PE in all_PE[next_PE_no].task_list:
                    if (base.channel_match[single_task.output_channel[0]] in single_task_next_PE.input_channel) and \
                        ((single_task.op_no == single_task_next_PE.op_no) or (single_task.output_to[0] == single_task_next_PE.op_no)):
                        corresponding_channel_index = single_task_next_PE.input_channel.index(base.channel_match[single_task.output_channel[0]])
                        '''
                        if single_task_next_PE.add_input_tag(single_task.output_channel[0], single_task.output_channel_tag[0]) > 0
                            # needs to update corresponding state
                            all_PE[next_PE_no].state_list[single_task_next_PE.corresponding_state_no]\
                                .modify_channel_tag(single_task_next_PE.)
                        
                # add halt state
                halt_state = single_PE.add_state(1, "XXXXXXXX")
                now_state.add_state_operation("halt")
                trigger_input = [single_task.input_channel[0], single_task]
            else: # single_task.task_type == "place"
                state_operation = all_Op[single_task.op_no].corresponding_operation
                if state_operation[0] in base.base_number: # const
                    continue
                elif: state_operation == "phi": # needs two state
                    now_state = single_PE.add_state(0, "0")
                    next_state = single_PE.add_state(0, )
                    '''

                

# fprint
for single_PE in all_PE:
    File_output = File_output + single_PE.File_PE_name()
    if len(single_PE.task_list) == 0: # unused PE
        File_output = File_output + \
            "    # PE unused\n" + \
            "    when %p == XXXXXXXX:\n" + \
            "        halt;\n"
    else:
        for single_state in single_PE.state_list:
            single_task_no = single_state.corresponding_task_no
            if single_task_no >= 0: 
                single_task = single_PE.task_list[single_task_no]
                File_output = File_output + \
                    "    # task " + str(single_task.task_no) + " " + str(single_task.task_type) + " op_" + str(single_task.op_no) + "\n"
            File_output = File_output + single_state.output_str()

    File_output = File_output + "\n"

File_write_to = open("output_file.tia", mode="w")
File_write_to.write(File_output)
File_write_to.close()

print(File_output)