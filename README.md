# Crane-pip

`crane pip` allows installation of python packages from a private index secured by OAuth 2.0 authentication (provided by a crane server).

## Features

- Installing python package from OAuth 2 protected indexes (provided by crane)
- Fall back to PyPI if (package of sub-dependencies are not found in the private index)
- Private index takes installation priority (regardlesss of package versions in PyPI)
- Third party client support (pip/uv/poetry/etc..). Provided the needed setup in the respective tools is done. See [below](#third-party-client-support).

## Installation (from source)

### temporarily install instructions:

Download the latest .tar.gz from: https://repos.dev.openanalytics.eu/repo/python-public/crane-pip/
Install the `crane-pip` in its own environment on your system using [pipx](https://github.com/pypa/pipx).

```
pipx install crane-pip-x.y.z.tar.gz
```

Verify installation by issuing the main command:
```
crane 
```
You should see help message. Something along the lines of:
```
usage: crane [-h] {pip,serve,index} ...

optional arguments:
  -h, --help         show this help message and exit

commands:
  {pip,serve,index}
    pip              Any pip command, but crane indexes do get correctly authenticated.
    index            Manage registered crane-indexes.
    serve            Serve a local index proxy performing authentication for the crane protected
                     index.
```

## Usage

The crane-pip package comes with a cli tool `crane` installed.

### Step 1 (one-time setup): Register a crane protected index.

To use a crane protected index, you should first register it with the `index register` command:
```
crane index register --help
```
For example:
```
crane index register https://private.example.com/repos/repo1 crane-pip https://id-provider.example.com/auth/realms/myrealm/protocol/openid-connect/token https://id-provider.example.com/auth/realms/myrealm/protocol/openid-connect/auth/device
```

For a given index-url you will need to register some authentication settings of the OAuth 2.0 identity provider that the crane server is using. 

Currently the folloowing info needs to provided: 
- client_id : The client that crane cli tool will use to communicate with the identity provider.
- token_url : The url to generate access tokens from.
- device_url : The url to request the device codes from.

That is it! You can now use this index in `crane pip` commands. See `crane index --help` on to manage your indexes.

### Step 2: Install packages with `crane pip install`

The `crane pip` command functions exactly the same as a normal `pip` command. But registered indexes (using step 1) in the `--index-url` flag will correctly authenticate request with the crane server.

For example:
```
crane pip install --index-url https://private.example.com/repos/repo1 cowsay
```

Will install [cowsay](https://github.com/VaasuDevanS/cowsay-python) if the package is available in the specified private index.

On first time usage, you will get promted to authenticate yourself in the browser. A browser window should automatically open or you can manually open one with the urls printed in the console.

The access token and refresh token are cached and you will only get promted again for authentication if both the access and refresh token have expired.


#### Limitations

Following pip flags are not supported
- `--extra-index-url`.
- `--proxy`.

Please also do not set these flags in any pip configuration file.

Specifying the private index via a pip configuration file is also not supported. You must provide it via the `--index-url/-i` flag.

Note, other settings in the pip-configuration file are supported.

## Third party client support

Third party tools that manage the python environment for you (like poetry/rye/...) should make use of a crane index proxy. 

Launch the proxy server:
```
crane serve https://private.example.com/repos/repo1
```
This will start a server on the localhost that acts as an index for the 3rd party tools. Launching the server will prompt to authenticate yourself in a browser, if the tokens for said index were not cached before or were already expired.

Now point your the tool that manages your environment towards the proxy index. The proxy server will forward request to the private index with the needed authentication.

### Note

The authentication prompt that requires interaction with the broweser is only requested at start-up of the server. The server will use the refresh token to update the access token if you interact with it. But if the refresh token expires or authentication rights have been revoked by the identity provider, then a restart of the server is required.


