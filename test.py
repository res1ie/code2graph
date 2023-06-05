#!/usr/bin/python
from bigcode_astgen import ast_generator
import ast
import sys

        
if len(sys.argv) != 2:
    print("Insufficient arguments")
    sys.exit()

filename=sys.argv[1]#"view.py"

parsed=ast_generator.parse_file(filename)
assign=[]


for _ in parsed:
    #print(_)
    if "Assign" in _['type']:
        assign.append(_)

def get_inst(x):
    ans=[]
    for child in parsed[x]['children']:
        if parsed[child]['type']=='Try':
            body=parsed[child]['children'][0]
            assert parsed[body]['type']=='body'
            ans+=get_inst(body)
            #"""
            handlers=parsed[child]['children'][1]
            assert parsed[handlers]['type']=='handlers'
            for handle in parsed[handlers]['children']:
                body=parsed[handle]['children'][-1]
                assert parsed[body]['type']=='body'
                ans+=get_inst(body)
            #"""
        
        elif 'If' in parsed[child]['type']:
            ans.append(parsed[child]['children'][0])
            body=parsed[child]['children'][1]
            assert parsed[body]['type']=='body'
            ans+=get_inst(body)
        elif 'Import' in parsed[child]['type']:
            continue
        elif 'Def' in parsed[child]['type']:
            continue
        else:
            ans.append(child)
    return ans

def get_import(x):
    ans=[]
    for child in parsed[x]['children']:
        if parsed[child]['type']=='Try':
            body=parsed[child]['children'][0]
            assert parsed[body]['type']=='body'
            ans+=get_import(body)
            #"""
            handlers=parsed[child]['children'][1]
            assert parsed[handlers]['type']=='handlers'
            for handle in parsed[handlers]['children']:
                body=parsed[handle]['children'][-1]
                assert parsed[body]['type']=='body'
                ans+=get_import(body)
            #"""
        elif 'Import' in parsed[child]['type']:
            ans.append(child)
    return ans

def get_def(x):
    ans=[]
    for child in parsed[x]['children']:
        if 'Def' in parsed[child]['type']:
            ans.append(child)
    return ans

name_set=set()
var_dic={}
event_graph=[]

def get_name(where,x):
    name=parsed[x]['value']
    result = where.split("::")[:-1]
    prefixes = [""]+["::".join(result[:i])+"::" for i in range(1, len(result))]
    for _ in prefixes[::-1]:
        if _+name in name_set:
            return _+name
    return where+name
    
def get_attrname(where,x):
    base=parsed[x]['children'][0]
    attr=parsed[x]['children'][1]
    name,arg=get_rep(where,base)
    assert parsed[attr]['type']=="attr"
    return name+"."+parsed[attr]['value'],arg

def get_susname(where,x):
    base=parsed[x]['children'][0]
    idx=parsed[x]['children'][1]
    name,arg=get_rep(where,base)
    assert parsed[idx]['type']=="Index"
    idx=parsed[idx]['children'][0]
    name+="["+get_rep(where,idx)[0]+"]"
    if parsed[idx]['type']!="Constant":
        arg.append(get_rep(where,idx))
    return name,arg

def get_rep(where,x):
    if parsed[x]['type']=="Call":
        base=parsed[x]['children'][0]
        name,args=get_rep(where,base)
        if "." in name:
            self=name.rsplit(".", 1)[0]
            if "[" in self:
                args=[(self,args)]
        for arg in parsed[x]['children'][1:]:
            args.append(get_rep(where,arg))
        return name+"()",args
    if "Name" in parsed[x]['type']:
        return get_name(where,x),[]
    if "Attribute" in parsed[x]['type']:
        return get_attrname(where,x)
    if "Subscript" in parsed[x]['type']:
        return get_susname(where,x)
    if parsed[x]['type']=="Constant":
        value=parsed[x]['value']
        try:
            return int(value),[]
        except ValueError:
            pass
        try:
            return float(value),[]
        except ValueError:
            pass
        if value.lower() == 'true' or value.lower() == 'false':
            return value.lower() == 'true',[]
        return '"'+value+'"',[]

def represent(where,x):
    name,arg=get_rep(where,x)
    name_set.add(name)
    var_dic[x]=name
    return name,arg

class Scope:
    def __init__(self,x,where=""):
        self.index=x
        def_index=get_def(x)
        self.cdef=[]
        self.inst=get_inst(x)
        self.imp=get_import(x)
        for _ in self.imp:
            children=parsed[_]["children"]
            for child in children:
                assert parsed[child]["type"]=="alias"
                name_set.add(parsed[child]["value"])
        self.graph=[]
        for _ in self.inst:
            if parsed[_]['type']=="Assign":
                name,arg=represent(where,parsed[_]['children'][-1])
                for var in parsed[_]['children'][-2::-1]:
                    _name=name
                    _arg=arg
                    name,arg=represent(where,var)
                    arg.append((_name,_arg))
                self.graph.append((parsed[_]['lineno'],name,arg))
            if parsed[_]['type']=="Expr" or "UnaryOp" in parsed[_]['type']:
                if parsed[parsed[_]['children'][0]]['type']=="Call":
                    name,arg=represent(where,parsed[_]['children'][0])
                self.graph.append((parsed[_]['lineno'],name,arg))
        #print(where)
        global event_graph
        event_graph+=self.graph
        for _ in def_index:
            self.cdef.append((_,parsed[_]['value'],parsed[_]['children'][0],Scope(parsed[_]['children'][1],parsed[_]['value']+"::")))
        


module=Scope(0)
#print(name_set)
#or _ in event_graph:
 #S    print(_)

nodes=[]
edges=[]
not_event={}
def get_edge(x):
    idx,name,args=x
    pos=len(nodes)
    nodes.append(name)
    if "." in name or "[" in name or "(" in name:
        pass
    else:
        if name in not_event:
            pos=not_event[name]
        else:
            not_event[name]=pos
    for arg in args:
        edges.append((idx,pos,get_edge((idx,arg[0],arg[1]))))
    return pos

for _ in event_graph:
    get_edge(_)
print(nodes)
print(edges)


from collections import deque

def bfs(graph, start, target):
    visited = set()
    queue = deque([(start, [start])])

    while queue:
        node, path = queue.popleft()
        if node == target:
            return path
        if node in visited:
            continue
        visited.add(node)
        if node in graph:
            neighbors = graph[node]
            for neighbor in neighbors:
                queue.append((neighbor, path + [neighbor]))
    return None
    
def has_path(graph, source, san, sink):
    for so in source:
        for si in sink: 
            path = bfs(graph, so, si)
            if path is not None:
                return path
    return None
graph = {}
for _,end,start in edges:
    if start not in graph:
        graph[start] = []
    graph[start].append(end)

#############하드코딩됨
source = [1]
san = [5]
sink = [13]

result = has_path(graph, source, san, sink)
if result is not None:
    print("Path:", result)
else:
    print("No path exists.")