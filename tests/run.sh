python3 -m pip install .


coverage run --source away/ -m unittest discover -s tests -p '*.py'


coverage report -m