import dis
from opcode import opmap, opname
from odoo.tools.safe_eval import _SAFE_OPCODES, to_opcodes

print(f"POP_ITER in opmap: {'POP_ITER' in opmap}")
if 'POP_ITER' in opmap:
    pop_iter_code = opmap['POP_ITER']
    print(f"POP_ITER code: {pop_iter_code}")
    print(f"POP_ITER in _SAFE_OPCODES: {pop_iter_code in _SAFE_OPCODES}")

print(f"JUMP_BACKWARD in opmap: {'JUMP_BACKWARD' in opmap}")
if 'JUMP_BACKWARD' in opmap:
    jump_backward_code = opmap['JUMP_BACKWARD']
    print(f"JUMP_BACKWARD code: {jump_backward_code}")
    print(f"JUMP_BACKWARD in _SAFE_OPCODES: {jump_backward_code in _SAFE_OPCODES}")
