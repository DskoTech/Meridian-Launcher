"""Builds gameinput_native.pyd from gameinput_native.cpp against the
vendored GameInput SDK (vendor/GameInput/) using pybind11.

Windows + MSVC only - GameInput is a Windows-only API. Needs the MSVC
Build Tools (Visual Studio Build Tools, "Desktop development with C++"
workload) and pybind11 installed for whichever Python this gets run
with:

    pip install pybind11 --break-system-packages
    python setup.py build_ext --inplace

That produces gameinput_native.<platform tag>.pyd right in this folder.
Copy it next to gameinput_api.py in every app folder that should use it
(same distribution convention as SDL3.dll) - see this folder's README.md.
"""

import sys
from pathlib import Path

from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

if sys.platform != "win32":
    sys.exit(
        "gameinput_native can only be built on Windows - GameInput is a "
        "Windows-only API (see gameinput_native.cpp's module docstring)."
    )

HERE = Path(__file__).resolve().parent
SDK = HERE / "vendor" / "GameInput"

ext_modules = [
    Pybind11Extension(
        "gameinput_native",
        ["gameinput_native.cpp"],
        include_dirs=[str(SDK / "include")],
        library_dirs=[str(SDK / "lib" / "x64")],
        libraries=["GameInput"],
        cxx_std=17,
    ),
]

setup(
    name="gameinput_native",
    version="1.0.0",
    description=__doc__,
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
