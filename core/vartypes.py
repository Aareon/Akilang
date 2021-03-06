from core.llvmlite_custom import Map, _PointerType, MyType
from core.tokens import Dunders

import llvmlite.ir as ir
import ctypes
from llvmlite import binding

# Singleton types (these do not require an invocation, they're only created once)

def make_type_as_ptr(my_type):
    def type_as_ptr(addrspace=0):
        t = _PointerType(my_type, addrspace, v_id=my_type.v_id)
        return t

    return type_as_ptr


class Bool(ir.IntType):
    p_fmt = '%i'
    def __new__(cls):
        return super().__new__(cls, 1, False, True)


class SignedInt(ir.IntType):
    p_fmt = '%i'
    def __new__(cls, bits, force=True):
        return super().__new__(cls, bits, force, True)


class UnsignedInt(ir.IntType):
    p_fmt = '%u'
    def __new__(cls, bits, force=True):
        return super().__new__(cls, bits, force, False)

class Float64(ir.DoubleType):
    def __new__(cls):
        t = super().__new__(cls)
        t.signed = True
        t.v_id = 'f64'
        t.width = 64
        t.is_obj = False
        t.p_fmt = '%f'
        return t

ir.IntType.is_obj = False

class Array(ir.ArrayType):
    is_obj = False
    def __init__(self, my_type, my_len):
        super().__init__(my_type, my_len)
        self.v_id = 'array_' + my_type.v_id
        self.signed = my_type.signed
        self.as_pointer = make_type_as_ptr(self)
        

class CustomClass():
    def __new__(cls, name, types, v_types):
        new_class = ir.global_context.get_identified_type('.class.' + name)
        new_class.elements = types
        new_class.v_types = v_types
        new_class.v_id = name
        new_class.signed = False
        new_class.is_obj = True
        new_class.as_pointer = make_type_as_ptr(new_class)
        return new_class


class ArrayClass(ir.types.LiteralStructType):
    is_obj = True
    def __init__(self, my_type, elements):
        arr_type = my_type
        for n in reversed(elements):
            arr_type = VarTypes.array(arr_type, n)
        super().__init__(
            [
                VarTypes.array(VarTypes.u_size, len(elements)),
                arr_type
            ]
        )
        
        self.v_id = f'array_{my_type.v_id}'
        self.del_id = 'array'        
        self.as_pointer = make_type_as_ptr(self)

# When we remake string class, we should follow ArrayClass example
# I just need to know how to initialize the string, load the contents,
# for a static instance.
# With a dynamically created instance, I don't think I can do that.

# object types

Ptr = ir.global_context.get_identified_type('.object.ptr')
Ptr.elements = (UnsignedInt(8, True).as_pointer(), )
Ptr.v_id = "ptrobj"
Ptr.is_obj = True
Ptr.signed = False
Ptr.ext_ptr = UnsignedInt(8, True).as_pointer()

Str = ir.global_context.get_identified_type('.object.str')
Str.elements = (ir.IntType(64), ir.IntType(8).as_pointer())
Str.v_id = 'str'
Str.is_obj = True
Str.signed = False
Str.ext_ptr = UnsignedInt(8, True).as_pointer()
Str.p_fmt = '%s'
Str.as_pointer = make_type_as_ptr(Str)

ErrType = ir.global_context.get_identified_type('.object.err')
ErrType.elements = (Str,)
ErrType.v_id = 'err'
ErrType.is_obj = True # ?
ErrType.signed = False

OKType = ir.global_context.get_identified_type('.object.ok')
OKType.elements = (ir.IntType(1),)
OKType.v_id = 'ok'
OKType.is_obj = True # ?
OKType.signed = False

#ResultType = ir.global_context.get_identified_type('.object.result')
#ResultType.elements = (OKType, ErrType)
#third element should be the actual result?
#how to encode that?

# types for singleton objects

NoneType = ir.global_context.get_identified_type('.object.none')
NoneType.elements = (ir.IntType(1), )
NoneType.v_id = 'none'
NoneType.is_obj = True
NoneType.signed = False
NoneType.ext_ptr = ir.IntType(8).as_pointer()



# module doesn't exist yet
# OKProto = ir.GlobalValue(ir.module, OKType, '.object.ok1')

# Object wrapper

Obj = ir.global_context.get_identified_type('.object.base')
Obj.elements = (
    ir.IntType(8),  # pointer to object prototype list
    ir.IntType(8).as_pointer()  # pointer to the object data itself
    # eventually, a pointer to a dict obj for properties
)
Obj.v_id = 'obj'
Obj.is_obj = True
Obj.ext_ptr = ir.IntType(8).as_pointer()

# This will take in a target data,
# or failing that, just default to the platform running
# The lexer, parser, and codegen objects will each
# create an instance of this, so they are all instance-local
# and not simply imported from this module

def generate_vartypes(module=None):
    
    _vartypes = Map({
        
        # singleton
        'u1': Bool(),
        'i8': SignedInt(8),
        'i16': SignedInt(16),
        'i32': SignedInt(32),
        'i64': SignedInt(64),
        'u8': UnsignedInt(8),
        'u16': UnsignedInt(16),
        'u32': UnsignedInt(32),
        'u64': UnsignedInt(64),
        'f64': Float64(),
        'u_size': None,
        # u_size is set on init

        # non-singleton
        'array': Array,
        'func': ir.FunctionType,

        # object types
        'str': Str,
        'ptrobj': Ptr,
        'None': NoneType,

        # 'any': Any
    })
    

    # TODO: add c_type to native llvmlite float
    # as we did with int
    _vartypes.f64.c_type = ctypes.c_longdouble

    # add these types in manually, since they just shadow existing ones

    _vartypes['bool'] = _vartypes.u1
    _vartypes['byte'] = _vartypes.u8

    _vartypes.func.is_obj = True

    _vartypes._DEFAULT_TYPE = _vartypes.i32
    _vartypes._DEFAULT_RETURN_VALUE = ir.Constant(_vartypes.i32, 0)

    # if no module, assume platform

    if not module:
        module = ir.Module()
    
    # Initialize target data for the module.
    target_data = binding.create_target_data(module.data_layout)

    # Set up pointer size and u_size vartype for current hardware.
    _vartypes._pointer_size = (
        ir.PointerType(_vartypes.u8).get_abi_size(target_data)
    )

    _vartypes._pointer_bitwidth = _vartypes._pointer_size * 8

    _vartypes._target_data = target_data
    
    _vartypes['u_size'] = UnsignedInt(_vartypes._pointer_bitwidth)
    _vartypes['u_mem'] = UnsignedInt(_vartypes._pointer_size)

    for _, n in enumerate(_vartypes):
        if not n.startswith('_'):
            _vartypes[n].box_id = _

    return _vartypes

VarTypes = generate_vartypes()

# platform VarTypes is the default
# we can just import from here if we want that
# and most of the time, we do

DEFAULT_TYPE = VarTypes._DEFAULT_TYPE
DEFAULT_RETURN_VALUE = VarTypes.DEFAULT_RETURN_VALUE

dunder_methods = set([f'__{n}__' for n in Dunders])