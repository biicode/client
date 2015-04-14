@echo off

set current_dir=%cd%

cd ..

set path_bii=%cd%\bii
set path_blocks=%cd%\blocks
set path_deps=%cd%\deps

cd %current_dir%

if exist %path_bii% if exist %path_blocks% (
	set PYTHONPATH=%PYTHONPATH%;%path_blocks%;%path_deps%
	python %* ) else (
	echo You are not in a valid folder!
	echo Enter in your [bii_workspace]/[hive_name]/blocks or [bii_workspace]/[hive_name]/deps directory
	)