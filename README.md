# Crane-pip

`crane pip` allows installation of python packages from a private index secured by a crane authentication server.

## Installation

Install the `crane-pip` in its own environment on your system using [pipx](https://github.com/pypa/pipx)

```
pipx install crane-pip
```

## Usage 

```
crane pip install --index-url crane_secured_index.example.com pkg
```

You will get promted to authenticated yourself.

## Index proxy

Third party tools that manage the python environment for you (like poetry/rye/...) should make use of a crane index-proxy.

Launch the proxy server:
```
crane index-proxy --index crane_secured_index.example.com
```

You will get promted to authenticated yourself in a browser. Now point your the tool that manages your environment towards the proxy index. 

The proxy server will forward request to the crane secured index specified with the needed authentication.
