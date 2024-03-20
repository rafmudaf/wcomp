
from pathlib import Path

from setuptools import find_packages, setup


# Package meta-data.
NAME = "wcomp"
DESCRIPTION = "A framework for systematically comparing steady-state, analytical wind farm wake modeling software."
URL = "https://github.com/rafmudaf/wcomp"
EMAIL = "rafael.mudafort@nrel.gov"
AUTHOR = "NREL National Wind Technology Center"
REQUIRES_PYTHON = ">=3.10"

# What packages are required for this module to be executed?
REQUIRED = [
    "floris",   # At develop, latest hash is c7f8f36
    "foxes==v0.6.2",
    "py-wake",  # At master with two additional commits on rafmudaf/PyWake, latest hash is 35e63b7
    "numpy>=1.20",
    "windIO",
    "matplotlib",
]
EXTRAS = {
    "docs": {
        "jupyter-book",
        # "jupyter-book==0.14",
        # "sphinx-book-theme==0.4.0rc1",
        # "sphinx-autodoc-typehints",
        "sphinxcontrib-autoyaml",
        "sphinxcontrib.mermaid",
        "pylint",  # Used for pyreverse to generate diagrams
    },
    "develop": {
        "pytest",
        "ruff",
        "isort",
    },
}

ROOT = Path(__file__).parent
with open(ROOT / "wcomp" / "version.py") as version_file:
    VERSION = version_file.read().strip()

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=DESCRIPTION,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    license="GPL-3.0 license",
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
)
