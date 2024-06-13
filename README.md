# rdepot-pip

`rdepot-pip` allows installation of python packages from a private rdepot index repository. Users are authenticated using OAuth 2.

## Installation

Install the `rdepot-pip` in its own environment on your system using [pipx](https://github.com/pypa/pipx)

```
pipx install rdepot-pip
```

## Index configuration

Either specify directly via `-i` or `--index-url` flag which rdepot url to use or specify it with the `RDEPOT_URL` environment.

If not rdepot url is specified, it will default back to PyPI.

TODO: determine how to support more fall back urls.

## Usage 

```
rdepot-pip install --index-url rdepot.example.url pkg
```

You will get promted to authenticated yourself against the rdepot index in the browser. 

## Advanced use cases

Using other 3rd party clients with rdepot-pip. 

Spin up your own local rdepot index:

```
rdepot-local-index
```

You will get promted to authenticated yourself. 

Point your 3rd party tool to exclusive use the local adress as the index to use. This index will redirect requestes to the index you have configured.

