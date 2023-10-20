# Away
[![Python package](https://github.com/Axemt/away/actions/workflows/python-package.yml/badge.svg)](https://github.com/Axemt/away/actions/workflows/python-package.yml)
![GitHub](https://img.shields.io/github/license/Axemt/away)

A python library to create local functions of OpenFaaS functions, allowing their transparent use

## Usage

### Obtaining local proxies
Get or build a function proxy to an OpenFaaS function. For example, for a `fibonacci` function deployed in OpenFaaS:

1. Create a `FaasConnection`:
```python
from away import builder, FaasConnection

faas = FaasConnection(’my-faas-server.com’, port=8080, user=‘admin’, password=‘1234’)
```
2. Decorate a stub function with `away.builder.faas_function`:
```python
@builder.faas_function(faas)
def fibonacci(n):
	pass
```
3. Call your function as if it were local
```python
fibonacci(10) # calls the function in OpenFaaS behind the scenes, returns 55
```

4. Or create async versions transparently
```python
@builder.faas_function(faas)
async def fibonacci(n):
	pass

res = await fibonacci(10) # calls the function asynchronously in the background, returns 55
```

You can also create a function from a name, to for example avoid shadowing a local variable
```python
fibonacci_with_a_different_name = builder.sync_from_faas_str(’fibonacci’, faas)
fibonacci_with_a_different_name(55) # returns 139583862445
```

If you wish to handle errors in the FaaS functions manually you can use the option `implicit_exception_handling=False` to make the function return the status code alongside the response. Otherwise, the function raises an exception.

```python
@builder.faas_function(faas, implicit_exception_handling=False)
def fibonacci(name):
	pass

fibonacci(10) # returns (55, 200)
```

### Building and pushing to server
You can also push a self-contained function to an OpenFaaS server with `builder.publish`. You must be logged in to the FaaS server with enough privileges to deploy functions:

```python
faas = FaasConnection(password=1234)

@builder.publish(faas) # builds a function container and pushes it to the `faas` server
def sum_two_numbers(A,B):
	return A + B

res = sum_two_numbers(1,2) # executes in the OpenFaaS server and returns 3
```

The decorator creates also a local proxy to call the newly published function locally. The proxy has the same characteristics as the defined function (i.e: async/sync)

```python
@builder.publish(faas)
async sum_all_numbers(l):
	res = 0
	for n in l:
		res = res + n

	return res

await sum_all_numbers([1,2,3,4]) # async-calls the function and returns 10
```

## Installation

To install as a pip package run `python -m pip install .` from away’s main directory
