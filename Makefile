setup=setup.py
py=python
commands=sdist upload

stage:
	$(py) $(setup) $(commands) -r pypitest

release:
	$(py) $(setup) $(commands) -r pypi
