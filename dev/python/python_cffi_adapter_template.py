cffi_template = '''from cffi import FFI
def link_clib(block_cell_name):
    ffi = FFI()
    ffi.cdef(r\'\'\'{{headers}}\'\'\')
    C = ffi.dlopen('{{dynlib_file}}')
    return ffi, C
'''