# rdepot-pip

`rdepot-pip` allows installation of python packages from a private rdepot index repository. Users are authenticated using OAuth 2.

## Installation

Install the `rdepot-pip` in its own environment on your system using [pipx](https://github.com/pypa/pipx)

```
pipx install rdepot-pip
```

## Configuration

Configure which rdepot index to use. 

TODO determine still how to configure the to which index to communicate!

## Usage 

```
rdepot-pip install pkg
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

