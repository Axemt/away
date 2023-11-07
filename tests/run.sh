# Fail stage if any command in script fails
set -e

# Build and install
python3 -m pip install .

# Run tests with coverage
coverage run --source away/ -m unittest discover -s tests -p '*.py'

# Cleanup
rm -rf build/
docker system prune -a --force --volumes
minikube ssh -- docker system prune -a --force --volumes

# Report
coverage report -m --fail-under 80