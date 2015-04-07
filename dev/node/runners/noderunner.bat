@echo off

set path_blocks={blocks_path}
set path_deps={deps_path}

cd %path_blocks%

if exist %path_blocks% (
	set NODE_PATH=%NODE_PATH%;%path_blocks%;%path_deps%
	node %* ) else (
	echo You are not in a valid folder!
	)

cd ..
