#!/usr/bin/env bash

command_node="nodejs"
if [ "$(uname)" == "Darwin" ]; then
    command_node="node"       
fi


path_blocks={blocks_path}
path_deps={deps_path}

cd $path_blocks

if [[ -d "$path_blocks" ]]; then
	export NODE_PATH=$NODE_PATH:$path_blocks:$path_deps
	$command_node "$@"
else
	echo You are not in a valid folder!
fi

cd ..
