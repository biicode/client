# Biicode client

## Requirements

    Python 2.7

## Run client

### Create a folder named "biicode":

        mkdir biicode
        cd biicode

### Clone this repository inside "biicode" folder:

        git clone https://github.com/biicode/client.git

### Add to python path the folder containing "biicode" folder and call *main* function from *biicode.client.shell.bii* module:


        #!/usr/bin/env python
        import sys, os
        sys.path.append(os.path.join(os.getcwd(), "../"))
        from biicode.client.shell.bii import main
        main(sys.argv[1:])

