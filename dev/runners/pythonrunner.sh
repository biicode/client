#!/bin/bash

current_dir=$(pwd)

cd ..

path_bii=$(pwd)/bii
path_blocks=$(pwd)/blocks
path_deps=$(pwd)/deps

cd $current_dir

if [[ -d "$path_bii" ]] && [[ -d "$path_blocks" ]]; then
	export PYTHONPATH=$PYTHONPATH:$path_blocks:$path_deps
	$"python" "$@"
else
	echo You are not in a valid folder!
	echo Enter in your [bii_workspace]/[hive_name]/blocks or [bii_workspace]/[hive_name]/deps directory
fi