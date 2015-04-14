# Biicode client

## Requirements

    Python 2.7
 
Install extra dependencies (Check [`requirements.txt`](requirements.txt) file) with [`pip`](https://pypi.python.org/pypi/pip) command line tool:

    pip install -r requirements.txt

biicode.client module depends on [`biicode.common`](https://github.com/biicode/common) module too. Follow `biicode/common
repo instructions. *See "Run client" bellow also for a step by step example.*


## Run client

### Create a folder named "biicode":

        mkdir biicode
        cd biicode

### Clone this repository inside "biicode" folder:

        git clone https://github.com/biicode/client.git

### Clone [`biicode/common`](https://github.com/biicode/common) repository inside "biicode" folder:

        git clone https://github.com/biicode/client.git

### Install `biicode.client` dependencies

        pip install -r client/requirements.txt

### Install `biicode.common` dependencies

        pip install -r common/requirements.txt

### Add a module marker for the `biicode` folder:

        touch __init__.py

### Add to python path the folder containing "biicode" folder and call *main* function from *biicode.client.shell.bii* module:


        #!/usr/bin/env python
        import sys, os
        sys.path.append(os.path.join(os.getcwd(), "../"))
        from biicode.client.shell.bii import main
        main(sys.argv[1:])

