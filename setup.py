"""Legacy stub for setuptools.

This project is configured using pyproject.toml and PEP 517 builds.
Use `pip install .` or `python -m build` instead of `python setup.py`.
"""

import sys

if __name__ == "__main__":
	sys.exit(
		"This project uses pyproject.toml-based builds.\n"
		"Please use `pip install .` or `python -m build` instead of `python setup.py`."
	)
