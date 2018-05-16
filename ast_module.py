from collections import namedtuple
import llvmlite.ir as ir
from vartypes import DEFAULT_TYPE, VarTypes

# AST hierarchy

_default = lambda vartype: vartype if vartype is not None else DEFAULT_TYPE


class Node(object):
    def __init__(self, position):
        self.position = position

    def flatten(self):
        return [self.__class__.__name__, 'flatten unimplemented']

    def dump(self, indent=0):
        return dump(self.flatten(), indent)


class Expr(Node):
    pass


class Return(Expr):
    def __init__(self, position, val):
        super().__init__(position)
        self.val = val


class Break(Expr):
    def __init__(self, position):
        super().__init__(position)        


class Number(Expr):
    def __init__(self, position, val, vartype=None):
        super().__init__(position)
        self.val = val
        self.vartype = _default(vartype)
        self.name = f'{self.val}'

    def flatten(self):
        return [self.__class__.__name__, self.val, self.vartype]

    def __eq__(self, other):
        return self.val == other.val and self.vartype == other.vartype

    def __str__(self):
        return f'{self.vartype} {self.val}'


class Array(Expr):
    def __init__(self, position, elements, vartype):
        super().__init__(position)
        self.elements = elements
        self.element_type = vartype
        self.val = None
        self.name = f'{self.val}'

    def flatten(self):
        return [self.__class__.__name__, self.elements, self.val, self.element_type]

    def __eq__(self, other):
        return self.element_type == other.element_type and self.elements == other.elements and self.val == other.val

    def __str__(self):
        return f'{self.element_type.v_id}[{self.elements}]'


class ArrayAccessor(Expr):
    def __init__(self, position, elements, child=None):
        super().__init__(position)
        self.name = f'.arrayaccessor'
        self.elements = elements
        self.child = child

    def flatten(self):
        return [self.__class__.__name__, self.elements, self.child]

    def __eq__(self, other):
        return self.elements == other.elements

    def __str__(self):
        return f'{self.elements}'


class String(Expr):
    def __init__(self, position, val):
        super().__init__(position)
        self.val = val
        self.vartype = VarTypes.str
        #self.vartype = ir.ArrayType(ir.IntType(8), len(val))
        self.anonymous = True

    def flatten(self):
        return [self.__class__.__name__, self.val]

    def __eq__(self, other):
        return self.val == other.val

    def __str__(self):
        return f'"{self.val}"'


class Variable(Expr):
    def __init__(self, position, name, vartype=None, child=None):
        super().__init__(position)
        self.name = name
        self.vartype = vartype
        # _default(vartype)
        self.child = None

    def flatten(self):
        return [
            self.__class__.__name__, self.name, self.vartype,
            self.child.flatten() if self.child is not None else None
        ]

    def __str__(self):
        return f"{self.vartype} {self.name}"


class Unary(Expr):
    def __init__(self, position, op, rhs):
        super().__init__(position)
        self.op = op
        self.rhs = rhs
        #self.vartype = rhs.vartype

    def flatten(self):
        return [self.__class__.__name__, self.op, self.rhs.flatten()]


class Binary(Expr):
    def __init__(self, position, op, lhs, rhs):
        super().__init__(position)
        self.op = op
        self.lhs = lhs
        self.rhs = rhs
        #self.vartype = getattr(lhs,'vartype', None)

    def flatten(self):
        return [
            self.__class__.__name__, self.op,
            self.lhs.flatten(),
            self.rhs.flatten()
        ]


class Call(Expr):
    def __init__(self, position, callee, args, vartype=None):
        super().__init__(position)
        self.name = callee
        self.args = args
        self.vartype = _default(vartype)

    def flatten(self):
        return [
            self.__class__.__name__, self.name, self.vartype,
            [arg.flatten() for arg in self.args]
        ]

    def __str__(self):
        return f'{self.args} {self.name}'
        # ({[x for x in self.args]}


class Let(Expr):
    def __init__(self, position, vars):
        super().__init__(position)
        self.vars = vars
        #self.var = var_identifier
        #self.expr = var_expr
        #self.vartype = _default()
        # TODO: what does it yield?

    def flatten(self):
        return [
            self.__class__.__name__, self.vars, #self.vartype,
            #self.expr.flatten()
        ]


class Match(Expr):
    def __init__(self, position, cond_item, match_list, default=None):
        super().__init__(position)
        self.cond_item = cond_item
        self.match_list = match_list
        self.default = default
        '''
        match_list is a list of tuples:
            (conditional argument (default ==),
            conditional value (type must match item),
            conditional expression)
        '''


class If(Expr):
    def __init__(self, position, cond_expr, then_expr, else_expr):
        super().__init__(position)
        self.cond_expr = cond_expr
        self.then_expr = then_expr
        self.else_expr = else_expr
        #self.vartype = then_expr.vartype

    def flatten(self):
        return [
            self.__class__.__name__,
            self.cond_expr.flatten(),
            self.then_expr.flatten(),
            self.else_expr.flatten()
        ]


class When(Expr):
    def __init__(self, position, cond_expr, then_expr, else_expr):
        super().__init__(position)
        self.cond_expr = cond_expr
        self.then_expr = then_expr
        self.else_expr = else_expr
        #self.vartype = cond_expr.vartype

    def flatten(self):
        return [
            self.__class__.__name__,
            self.cond_expr.flatten(),
            self.then_expr.flatten(),
            self.else_expr.flatten()
        ]


class While(Expr):
    def __init__(self, position, cond_expr, body):
        super().__init__(position)
        self.cond_expr = cond_expr
        self.body = body
        #self.vartype = body.vartype

    def flatten(self):
        return [
            self.__class__.__name__,
            self.cond_expr.flatten(),
            self.body.flatten()
        ]


class Do(Expr):
    def __init__(self, position, expr_list):
        super().__init__(position)
        self.expr_list = expr_list
        #self.vartype = _default()

    def flatten(self):
        return [self.__class__.__name__, [x.flatten() for x in self.expr_list]]


class Loop(Expr):
    def __init__(self, position, id_name, start_expr, end_expr, step_expr,
                 body):
        super().__init__(position)
        self.id_name = id_name
        self.start_expr = start_expr
        self.end_expr = end_expr
        self.step_expr = step_expr
        self.body = body
        #self.vartype = start_expr.vartype if start_expr else None

    def flatten(self):
        return [
            self.__class__.__name__, self.id_name,
            self.start_expr.flatten(),
            self.end_expr.flatten(),
            self.step_expr.flatten() if self.step_expr else ["No step"],
            self.body.flatten()
        ]


class VarIn(Expr):
    def __init__(self, position, vars, body):
        # vars is a sequence of (name, expr) pairs
        super().__init__(position)
        self.vars = vars
        self.body = body
        #self.vartype = _default()

    def flatten(self):
        return [
            self.__class__.__name__,
            [[var[0], var[1].flatten() if var[1] else None]
             for var in self.vars],
            self.body.flatten()
        ]


class Uni(Expr):
    def __init__(self, position, vars):
        # vars is a sequence of (name, expr) pairs
        super().__init__(position)
        self.vars = vars
        #self.vartype = _default()

    def flatten(self):
        return [
            self.__class__.__name__,
            [[var[0], var[1].flatten() if var[1] else None]
             for var in self.vars]
        ]


class Const(Uni):
    pass


class Class(Expr):
    def __init__(self, name, vars, vartype=None):
        self.name = name
        self.vars = vars
        self.v_id = name
        self.vartype = vartype

    def flatten(self):
        return [self.__class__.__name__, self.name, self.vars, self.vartype]


_ANONYMOUS = "_ANONYMOUS."

DEFAULT_PREC = 30


class Prototype(Node):
    def __init__(self,
                 position,
                 name,
                 argnames,
                 isoperator=False,
                 prec=DEFAULT_PREC,
                 vartype=None,
                 extern=False):
        super().__init__(position)
        self.name = name
        self.argnames = argnames
        self.isoperator = isoperator
        self.prec = prec
        self.vartype = _default(vartype)
        self.extern = extern

    def is_unary_op(self):
        return self.isoperator and len(self.argnames) == 1

    def is_binary_op(self):
        return self.isoperator and len(self.argnames) == 2

    def get_op_name(self):
        assert self.isoperator
        return self.name[-1]

    _anonymous_count = 0

    @classmethod
    def Anonymous(klass, position, vartype=None):
        klass._anonymous_count += 1
        return Prototype(
            position,
            _ANONYMOUS + str(klass._anonymous_count), [],
            vartype=_default(vartype))

    def is_anonymous(self):
        return self.name.startswith(_ANONYMOUS)

    def flatten(self):
        args = [f'{x[1]} {x[0]}' for x in self.argnames]
        flattened = [self.__class__.__name__, self.name, ', '.join(args)]
        if self.prec != DEFAULT_PREC:
            return flattened + [self.prec]
        else:
            return flattened


class Function(Node):
    def __init__(self, position, proto, body):
        super().__init__(position)
        self.proto = proto
        self.body = body

    def is_anonymous(self):
        return self.proto.is_anonymous()

    @staticmethod
    def Anonymous(position, body, vartype=None):
        return Function(position,
                        Prototype.Anonymous(
                            position, vartype=_default(vartype)), body)

    def flatten(self):
        return [
            self.__class__.__name__,
            self.proto.flatten(),
            self.body.flatten()
        ]


class Pointer(Expr):
    def __init__(self, position, name, vartype=None):
        super().__init__(position)
        self.name = name
        self.vartype = _default(vartype)

    def flatten(self):
        return [self.__class__.__name__, self.name, self.vartype]


def dump(flattened, indent=0):
    s = " " * indent
    starting = True
    for elem in flattened:

        if not starting:
            s += " "

        if isinstance(elem, list):
            if isinstance(elem[0], list):
                s += dump(elem, indent)
            else:
                s += '\n' + dump(elem, indent + 2)
        else:
            s += str(elem)
        starting = False
    return s


if __name__ == '__main__':

    print("Run the parsing module to test the AST stuff!")