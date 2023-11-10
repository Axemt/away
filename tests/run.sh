set -e
# Build and install
python3 -m pip install .

# Run tests with coverage
coverage run --source away/ -m unittest discover -s tests -p '*.py'
test_retcode=$?

# Cleanup
rm -rf build/
docker system prune -a --force --volumes >> /dev/null
minikube ssh -- docker system prune -a --force --volumes >> /dev/null

# Report
coverage report -m --fail-under 80
exit $test_retcode