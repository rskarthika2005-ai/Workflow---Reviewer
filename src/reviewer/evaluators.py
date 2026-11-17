import ast

DEFAULT_ROUTE = "normal_queue"
MISSING_BRANCH = "missing_branch"


class CodeError(Exception):
    pass


def compare_values(left, sign, right):
    if left is None or right is None:
        return False
    if sign == ">=":
        return left >= right
    if sign == ">":
        return left > right
    if sign == "<=":
        return left <= right
    if sign == "<":
        return left < right
    return False


def evaluate_condition(cond, ticket):
    op = cond["op"]

    if op == "and":
        return all(evaluate_condition(item, ticket) for item in cond["items"])
    if op == "or":
        return any(evaluate_condition(item, ticket) for item in cond["items"])

    value = ticket.get(cond["field"])

    if op == "missing":
        return value is None
    if op == "equals":
        if value is None:
            return False
        return value == cond["value"]
    if op == "compare":
        return compare_values(value, cond["cmp"], cond["value"])
    return False


def route_from_rules(rules, ticket):
    for rule in sorted(rules, key=lambda r: r.order):
        if rule.condition is None:
            continue  
        if evaluate_condition(rule.condition, ticket):
            return rule.route, rule.location
    return DEFAULT_ROUTE, "default"



def route_from_workflow(nodes, ticket, start_id):
    by_id = {}
    for node in nodes:
        by_id[node.node_id] = node

    current = start_id
    where = "workflow"
    for _ in range(len(nodes) + 1):       
        node = by_id.get(current)
        if node is None or node.condition is None:
            return MISSING_BRANCH, where
        where = node.location
        if evaluate_condition(node.condition, ticket):
            target = node.if_true
        else:
            target = node.if_false
        if not target:
            return MISSING_BRANCH, where 
        if target not in by_id:
            return target, where          
        current = target
    return MISSING_BRANCH, where


def route_from_code(code, ticket, where="code"):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        raise CodeError("syntax error")

    func = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if func is None:
                func = node
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  
        else:
            raise CodeError("unsupported top-level statement: " + type(node).__name__)
    if func is None:
        raise CodeError("no function found")

    env = {}
    for arg in func.args.args:
        env[arg.arg] = ticket.get(arg.arg)

    done, value = run_block(func.body, env)
    if not done:
        return MISSING_BRANCH, where      
    return value, where


def run_block(statements, env):
    for stmt in statements:
        if isinstance(stmt, ast.Return):
            return True, eval_expr(stmt.value, env)

        elif isinstance(stmt, ast.If):
            if eval_expr(stmt.test, env):
                done, value = run_block(stmt.body, env)
            else:
                done, value = run_block(stmt.orelse, env)
            if done:
                return True, value

        elif isinstance(stmt, ast.Pass):
            continue

        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            continue  

        else:
            raise CodeError("unsupported statement: " + type(stmt).__name__)
    return False, None


def eval_expr(node, env):
    if node is None:
        return None

    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        if node.id not in env:
            raise CodeError("unknown name: " + node.id)
        return env[node.id]

    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            result = True
            for value in node.values:
                result = eval_expr(value, env)
                if not result:
                    return result
            return result
        result = False
        for value in node.values:
            result = eval_expr(value, env)
            if result:
                return result
        return result

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not eval_expr(node.operand, env)

    if isinstance(node, ast.Compare):
        left = eval_expr(node.left, env)
        for op, comparator in zip(node.ops, node.comparators):
            right = eval_expr(comparator, env)
            if not apply_compare(op, left, right):
                return False
            left = right
        return True

    raise CodeError("unsupported expression: " + type(node).__name__)


def apply_compare(op, left, right):
    if isinstance(op, ast.Is):
        return left is right
    if isinstance(op, ast.IsNot):
        return left is not right
    if isinstance(op, ast.Eq):
        return left == right
    if isinstance(op, ast.NotEq):
        return left != right
    if isinstance(op, ast.GtE):
        return compare_values(left, ">=", right)
    if isinstance(op, ast.Gt):
        return compare_values(left, ">", right)
    if isinstance(op, ast.LtE):
        return compare_values(left, "<=", right)
    if isinstance(op, ast.Lt):
        return compare_values(left, "<", right)
    raise CodeError("unsupported compare: " + type(op).__name__)