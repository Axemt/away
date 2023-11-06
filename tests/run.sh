# Build and install
python3 -m pip install .

# Run tests with coverage
coverage run --source away/ -m unittest discover -s tests -p '*.py'

# Cleanup
rm -rf build/
docker system prune -a --force
minikube ssh -- docker system prune -a --force

# Report
coverage report -m --fail-under 80