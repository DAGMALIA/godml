# distutils: language = c++
# cython: boundscheck=False, wraparound=False, cdivision=True

import re
cimport cython

@cython.cfunc
@cython.inline
def _replace_text(text: str, pattern: object, repl: str) -> str:
    """Aplica regex.replace a un solo string"""
    if text is None:
        return ""
    return pattern.sub(repl, text)

def cy_regex_replace(list input_col, str pattern, str repl):
    """
    Reemplaza texto en una columna de strings usando regex compilado en Cython.
    Args:
        input_col: lista de strings (columna DataFrame)
        pattern: regex pattern
        repl: string de reemplazo
    Returns:
        lista de strings con reemplazos
    """
    cdef Py_ssize_t n = len(input_col)
    cdef list result = [None] * n
    regex = re.compile(pattern)

    for i in range(n):
        result[i] = _replace_text(input_col[i], regex, repl)

    return result
