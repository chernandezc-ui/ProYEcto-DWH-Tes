"""Inventario AST sin importar módulos ni abrir conexiones."""
import ast
import collections
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
roots=['ETL','backend','comun']
paths=sorted(p for root in roots for p in (ROOT/root).rglob('*.py') if '__pycache__' not in p.parts)
texts={p.relative_to(ROOT).as_posix():p.read_text(encoding='utf-8-sig') for p in paths}
references=collections.Counter()
calls=collections.Counter()
modules=[];functions=[];duplicates=collections.defaultdict(list);exceptions=[];routes=[]
for name,source in texts.items():
    tree=ast.parse(source,filename=name)
    imports=[];defs=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Name):references[node.id]+=1
        if isinstance(node,ast.Attribute):references[node.attr]+=1
        if isinstance(node,ast.Call):
            key=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ''
            calls[key]+=1
        if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
        if isinstance(node,ast.ImportFrom):imports.append('.'*node.level+(node.module or ''))
        if isinstance(node,ast.ExceptHandler) and (node.type is None or isinstance(node.type,ast.Name) and node.type.id in ('Exception','BaseException')):
            exceptions.append({'path':name,'line':node.lineno,'bare':node.type is None,'body':[type(x).__name__ for x in node.body]})
    def walk(body,parent=''):
        for node in body:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                qual=parent+node.name
                decorators=[ast.unparse(d) for d in node.decorator_list]
                record=dict(path=name,name=node.name,qualname=qual,line=node.lineno,end=node.end_lineno,
                    lines=node.end_lineno-node.lineno+1,branches=sum(isinstance(n,(ast.If,ast.For,ast.While,ast.ExceptHandler,ast.IfExp)) for n in ast.walk(node)),
                    decorators=decorators,method=bool(parent),async_function=isinstance(node,ast.AsyncFunctionDef))
                functions.append(record);defs.append(qual)
                if decorators and any(any('.'+method+'(' in d for method in ('get','post','put','patch','delete')) for d in decorators):
                    routes.append(record)
                if not parent:
                    body_without_doc=node.body[1:] if node.body and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant) and isinstance(node.body[0].value.value,str) else node.body
                    signature=ast.dump(ast.Module(body=body_without_doc,type_ignores=[]),include_attributes=False)
                    if record['lines']>=8:duplicates[hashlib.sha256(signature.encode()).hexdigest()].append({'path':name,'name':qual,'line':node.lineno})
            elif isinstance(node,ast.ClassDef):walk(node.body,parent+node.name+'.')
    walk(tree.body)
    modules.append(dict(path=name,lines=len(source.splitlines()),imports=imports,definitions=defs,
        sha256=hashlib.sha256(source.encode()).hexdigest(),runtime=not('/tests/' in name or '/tools/' in name or '/scratch' in name or '/test' in name or name.startswith('ETL/check_'))))
for f in functions:
    f['symbol_references']=references[f['name']]
    f['call_sites_same_name']=calls[f['name']]
zero=[f for f in functions if not f['method'] and not f['decorators'] and references[f['name']]==0 and not f['name'].startswith('__')]
runtime_paths={m['path'] for m in modules if m['runtime']}
summary=dict(python_files=len(modules),python_lines=sum(m['lines'] for m in modules),
    runtime_files=len(runtime_paths),runtime_lines=sum(m['lines'] for m in modules if m['runtime']),
    functions_and_methods=len(functions),http_handlers=len(routes),broad_exception_handlers=len(exceptions),
    no_reference_candidates=len(zero),runtime_no_reference_candidates=sum(f['path'] in runtime_paths for f in zero))
result={'method':'AST lexical inventory, not proof of dead code; dynamic loading and framework entry points require manual tracing',
        'summary':summary,'largest_modules':sorted(modules,key=lambda m:-m['lines'])[:25],
        'largest_runtime_functions':sorted([f for f in functions if f['path'] in runtime_paths],key=lambda f:-f['lines'])[:25],
        'no_reference_candidates':zero,'identical_body_groups':[v for v in duplicates.values() if len(v)>1],
        'broad_exception_handlers':exceptions,'modules':modules,'functions':functions,'http_handlers':routes}
(OUT/'inventario-estatico.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
print('RUNTIME CANDIDATES:')
for f in zero:
    if f['path'] in runtime_paths:print(f"{f['path']}:{f['line']} {f['name']}")
print('LARGEST:')
for f in result['largest_runtime_functions'][:12]:print(f"{f['path']}:{f['line']} {f['name']} {f['lines']} lines {f['branches']} branch nodes")
print('DUPLICATES:')
for group in result['identical_body_groups']:print(group)
