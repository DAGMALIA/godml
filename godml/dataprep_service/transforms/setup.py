from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize(
        "regex_replace.pyx",
        compiler_directives={"language_level": "3"}
    )
)