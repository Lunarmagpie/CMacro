#!/usr/bin/env python3

"""
It was supposed to be a joke like cursed code but it went to an actual (unfinished) library lol

What actually interests you is the macro() function that can run C code directly in your Python file 😳️

Coming soon: I've planned to add some locals grabbing so you would be able to use Python variables in C code.

uhh it is the moment I write the credits so:
- author: Qexat
- contributors: (fill here)
- license: none (for now)

oh also it depends on gcc
"""

from __future__ import annotations

import ctypes
from io import TextIOWrapper
import os
import subprocess
import sys
from typing import Any


_C_EXT = '.c'
_O_EXT = '.o'
_SO_EXT = '.so'

DEFAULT_LOG_FILE: str = "cmp_log.txt"


def create_c_file(file_name: str, source: str) -> str:
    """
    Given a string containing C source code, generates a C file.
    Returns the absolute path of this latter.

    ### Parameters
        - file_name: str -> the name of the file, without extension
        - source: str -> the source of the code to put in the file    

    Note: this does NOT check if the source code is valid.
    """

    if not isinstance(file_name, str):
        raise TypeError("file name must be a string")
    if not isinstance(source, str):
        raise TypeError("source code must be a string")

    with open(file_name + _C_EXT, 'w') as _tmp:
        _tmp.write(source)

    return os.path.abspath(file_name + _C_EXT)


def generate_object_file(cfile_path: str, logs: str | None = None) -> str:
    """
    Given a C file, generates an intermediate object file.
    Returns the absolute path of this latter.

    ### Parameters
        - cfile_path: str -> path to the C file
        - logs: str (optional) -> path or file to logs file to output errors. default: sys.stdout
    """

    if not isinstance(cfile_path, str):
        raise TypeError("C file path must be a string")

    if logs is None:
        logs = sys.stdout

    if not os.path.exists(cfile_path):
        raise FileNotFoundError(f"No such file or directory: '{cfile_path}'")

    object_file_gencmd: str = f"gcc -c -Wall -Werror -fpic {cfile_path}"
    error, printed_out = subprocess.getstatusoutput(object_file_gencmd)

    if error:
        if isinstance(logs, str):
            log_file = open(logs, 'w')
        elif isinstance(logs, TextIOWrapper):
            log_file = logs
        else:
            raise TypeError("logs must be either a string or TextIOWrapper")

        if not log_file.writable():
            raise PermissionError("cannot write in provided logs file")

        log_file.write(printed_out)
        error_message = "your code generated a compile error"

        if isinstance(logs, str):
            error_message += f". Check {logs} for more information"

        raise SyntaxError(error_message)
    else:
        return os.path.abspath(cfile_path.removesuffix(_C_EXT) + _O_EXT)


def _so_name_from_obj(objfile_path: str) -> str:
    return f"lib{objfile_path.split(os.sep)[-1].removesuffix(_O_EXT)}1"


def generate_shared_library(objfile_path: str, shared_lib_name: str | None = None) -> str:
    """
    Given an object file, generates a shared library that can be loaded into Python.
    Returns the absolute path of this latter.

    ### Parameters
        - objfile_path: str -> path to the object file
        - shared_lib_name: str (optional) -> name of the shared library. default: based on object file name 
    """

    if not isinstance(objfile_path, str):
        raise TypeError("object file path must be a string")

    if shared_lib_name is None:
        shared_lib_name = _so_name_from_obj(objfile_path)

    if not isinstance(shared_lib_name, str):
        raise TypeError("shared library name must be a string")

    shared_lib_name += _SO_EXT

    shared_library_gencmd: str = f"gcc -shared -o {shared_lib_name} {objfile_path}"

    # We assume that if the first compilation succeeded, this one will do as well
    subprocess.getstatusoutput(shared_library_gencmd)

    return os.path.abspath(shared_lib_name)


def clean_intermediate_files(*intermediate_files: str) -> None:
    """
    Removes intermediate files that were generated during compilation.

    ### Parameters
        - intermediate_files: tuple[str] -> intermediate files to clean

    Note: incorrect args are ignored.
    """

    for file in intermediate_files:
        if os.path.exists(file):
            os.remove(file)


def load_shared_library(path: str) -> ctypes.CDLL:
    if not isinstance(path, str):
        raise TypeError("path must be a string")

    try:
        sl = ctypes.CDLL(f"{path}")
    except OSError:
        raise FileNotFoundError(f"No such file or directory: '{path}'")
    else:
        return sl


def _ctype_from_object(__o: object):
    match __o.__class__.__name__:
        case 'int':
            return ctypes.c_int
        case 'float':
            return ctypes.c_float
        case 'str':
            return ctypes.POINTER(ctypes.c_char)
        case 'list':
            if not __o:
                return ctypes.Array()
            else:
                fe, *re = __o
                if re and not all([type(fe) == type(el) for el in __o]):
                    raise TypeError(
                        "array type inconsistency: impossible to convert to C type")
                return ctypes.POINTER(_ctype_from_object(fe))
        case '_':
            raise NotImplementedError(
                f"type conversion from '{type(__o).__name__}' to C has not been implemented yet")


def object_to_ctype(__o: object) -> ctypes._CData:
    """
    Converts an object to its C equivalent. Coded by hand, probably lacks of accuracy.

    ### Parameters
        - o: object -> object to convert
    """

    return ctypes.cast(id(__o), ctypes.POINTER(_ctype_from_object(__o))).contents


def macro(source: str, fnte: str = "main", **kwargs) -> Any:
    """
    Executes C code from source directly in Python.

    ### Parameters
        - source: str -> the C source code to execute
        - fnte: str -> function name to execute within given source code. Raises a `NameError` if it cannot be found.

    ### Keyword Arguments
        - logs: str -> path to logs file in case of compilation output. default: see `DEFAULT_LOG_FILE`
        - keep_files: bool -> whether compilation intermediate files are kept or not. default: False
    """

    file_name: str = "tmp"

    if not isinstance(source, str):
        raise TypeError("source must be a string")
    if not isinstance(fnte, str):
        raise TypeError("function name to execute must be a string")

    logs: str | None = kwargs.get("logs", None)
    keep_files: bool = kwargs.get("keep_files", False)

    if not isinstance(keep_files, bool):
        raise TypeError("keep_files flag must be a boolean")

    c_file: str = create_c_file(file_name, source)
    o_file: str = generate_object_file(c_file, logs=logs)
    so_file: str = generate_shared_library(o_file)
    shared_library = load_shared_library(so_file)

    if not keep_files:
        clean_intermediate_files(c_file, o_file, so_file)

    c_argv = object_to_ctype(sys.argv)
    c_argc = object_to_ctype(len(sys.argv))

    try:
        c_main = shared_library[fnte]
    except AttributeError:
        raise NameError(f"{file_name}.c: name '{fnte}' is not defined")
    else:
        return c_main(c_argc, c_argv)
