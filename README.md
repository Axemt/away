# Away
[![Python package](https://github.com/Axemt/away/actions/workflows/python-package.yml/badge.svg)](https://github.com/Axemt/away/actions/workflows/python-package.yml)
![GitHub](https://img.shields.io/github/license/Axemt/away)

A python library to create local functions of OpenFaaS functions, allowing their transparent use

## Usage

### Using existing functions
Get or build a function proxy to an existing OpenFaaS function. For example, for a `fibonacci` function deployed in OpenFaaS:

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

### Using existing functions built using `away`

First off that's great! This project is useful for someone!

Use `away.protocol` to access the unpacking and packing functions to communicate with an already published function that used `away`'s default protocol.

```python
from away import protocol

packer_function = protocol.make_client_pack_args_fn(safe_args=True)
unpacker_function = protocol.make_client_unpack_args_fn(safe_args=True)

@builder.faas_function(faas, pack_args=packer_function, unpack_args=unpacker_function)
def fibonacci(n):
	pass
```
This in fact also hints at the fact that, if you would like to use a different packing/unpacking procedure, or must adapt to an existing function with specific return format, you can pass `pack_args` and `unpack_args` to `builder.faas_function` to override the default behaviour (no procedure).

The packer function must have a signature of type `Iterable[Any] -> str`, and the unpacker `str -> Tuple[Any]`

### Build and deploy your own functions programatically
You can also push a function to an OpenFaaS server with `builder.publish`. You must be logged in to the FaaS server with enough privileges to deploy functions:

```python
faas = FaasConnection(password=1234)

@builder.publish(faas) # builds a function container and pushes it to the `faas` server
def sum_two_numbers(A,B):
	return A + B

res = sum_two_numbers(1,2) # executes in the OpenFaaS server and returns 3
```
__Note__: If the function uses any values outside of the scope, they will be captured with their current values and published as part of the function. This is useful for constant values, but has the limitation that it can obviously not modify them in the outside scope. 

The decorator creates also a local proxy to call the newly published function locally. The proxy has the same characteristics as the defined function (i.e: async/sync)

```python
@builder.publish(faas)
async def sum_all_numbers(l):
	res = 0
	for n in l:
		res = res + n

	return res

await sum_all_numbers([1,2,3,4]) # async-calls the function and returns 10
```

If you would like to still have a local copy of the function, for example to offload the function to OpenFaaS when the load on the client gets high, use `builder.mirror_in_faas`. Like with `builder.publish`, the published function will retain sync/async characteristics

```python
secret = 123
def add_secret(n):
	return n + secret

add_secret_in_faas = builder.mirror_in_faas(add_secret, faas)

add_secret(1) # Executes the function locally and returns 124
add_secret_in_faas(1) # Executes the function in OpenFaaS and returns 124
```

Away includes a lightweight serialization-deserialization protocol to communicate with published functions based on `pyyaml`. By default, it only allows the use of safely unpickle-able objects. To use values that require unsafe, `pickle`-based serialization, use the kwarg `safe_args`:
__Note__: Non-builtin objects are not currently supported at the moment due to being unable to determine the type of the arg and to find the source to include.

```python
@builder.publish(faas, safe_args=False):
def use_unsafe_arg(rang):
	res = 0
	for i in rang:
		res += i
	return res
```

## Installation

To install as a pip package run `python -m pip install .` from away’s main directory

Away also needs the following external dependencies:

- [OpenFaas CLI](https://cli.openfaas.com)
- Docker
