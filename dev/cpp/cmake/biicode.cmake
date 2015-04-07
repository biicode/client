#=============================================================================#
#                                                                             #
#         				  biicode.cmake    									  #
#                                                                             #
#=============================================================================#
# This file contains all the macros and functions that make possible to create
# the targets (executables, libraries, etc) and respect the user project
# configuration and/or CMakeLists.txt files


#=============================================================================#
#				General SET and INCLUDE_DIRECTORIES
#=============================================================================#

# The BIICODE variable is used to execute (or not) some wished parts of any user
# block CMakeLists. For example:
# 		IF(NOT BIICODE)
#			ADD_SUBDIRECTORY(util)
# 		ENDIF()
SET(BIICODE TRUE)

# BII_TESTS_WORKING_DIR specifies a different WORKING_DIR (add_test(.. WORKING_DIR ${BII_TESTS_WORKING_DIR}))
# By default is empty
set(BII_TESTS_WORKING_DIR )

#=============================================================================#
#
#						PUBLIC FUNCTIONS AND MACROS
#
#=============================================================================#

#=============================================================================#
# [PUBLIC/USER] [USER BLOCK CMAKELISTS]
#
# INIT_BIICODE_BLOCK()
#
# Loads bii_user_block_vars.cmake files located in cmake directory
# This macro must be called by the root CMakeLists.txt of a block
# at the beginning, after the biicode.cmake inclusion.
#
#=============================================================================#

macro(INIT_BIICODE_BLOCK)
	MESSAGE("CALLING INIT_BIICODE_BLOCK IS NO LONGER NECESSARY")
endmacro() 

#=============================================================================#
# [PUBLIC/USER] [USER BLOCK CMAKELISTS]
#
# ADD_BIICODE_TARGETS()
#
#
# Adds and selects the target to be created. It's in charge of calling the macros
# which generate a library or a executable file.
#
#=============================================================================#
macro(ADD_BII_TARGETS)
	ADD_BIICODE_TARGETS(2.8)
endmacro()

macro(ADD_BIICODE_TARGETS)
	IF(${ARGV0})
		SET(BII_CMAKE_VERSION ${ARGV0})
	ELSE()
		IF(NOT BII_IS_DEP)
			MESSAGE("***********************************************************")
			MESSAGE("              ADD_BIICODE_TARGETS() is DEPRECATED")
			MESSAGE("              Use ADD_BII_TARGETS() instead")
			MESSAGE("***********************************************************")
		ENDIF()
		SET(BII_CMAKE_VERSION 2.7)
	ENDIF()

	set(BII_BLOCK_TARGETS)
	SET(BII_BLOCK_TARGET "${BII_BLOCK_USER}_${BII_BLOCK_NAME}_interface") 
	##### LIBRARY #####
	SET(vname "${BII_BLOCK_USER}_${BII_BLOCK_NAME}") 
	MESSAGE("+${BII_LIB_TYPE} LIB: ${vname}")

	BII_GENERATE_LIB(${vname} ${BII_CMAKE_VERSION})
	
	set(BII_BLOCK_TARGETS ${BII_BLOCK_TARGETS} "${vname}")
	set(BII_LIB_TARGET "${vname}")

	##### EXECUTABLES #####
	foreach(executable ${BII_BLOCK_EXES} )
		set(BII_${executable}_TARGET "${BII_BLOCK_USER}_${BII_BLOCK_NAME}_${executable}")
		MESSAGE("+ EXE: ${BII_${executable}_TARGET}")
		BII_GENERATE_EXECUTABLE( ${BII_BLOCK_USER} ${BII_BLOCK_NAME} ${executable} ${BII_CMAKE_VERSION})
		SET(BII_BLOCK_TARGETS ${BII_BLOCK_TARGETS} "${BII_BLOCK_USER}_${BII_BLOCK_NAME}_${executable}")
	endforeach ()

	##### TEST EXECUTABLES #####
	IF(BII_BLOCK_TESTS)
		message(STATUS "Initializing variables to create tests with CTest")
		MESSAGE(STATUS "Added custom target for all the tests: ${TESTS_TARGET}")
		MESSAGE("-- Following targets are defined like tests (excluded from build)")
		foreach(test ${BII_BLOCK_TESTS})
			set(BII_${test}_TARGET "${BII_BLOCK_USER}_${BII_BLOCK_NAME}_${test}")
			MESSAGE("+ TEST: ${BII_${test}_TARGET}")
			IF(COMMAND BII_ADD_TEST)
				# If user has customized command to add tests
				BII_ADD_TEST(${test})
			ELSE()
				BII_DEFINE_TEST(${BII_${test}_TARGET})
			ENDIF()
		endforeach()
	ENDIF()

endmacro()


#=============================================================================#
# [PUBLIC/USER] [USER BLOCK CMAKELISTS]
#
# BII_CONFIGURE_FILE(config_file_in config_file_out)
#
#        config_file_in    - Existing configure file name to charge
#		 config_file_out   - Output file where will be copied all the necessary
#
# Avoids errors due to the layout of configure. IT SHOULD be used instead of
# configure_file.
#
#=============================================================================#

macro (BII_CONFIGURE_FILE config_file_in config_file_out)
	MESSAGE(WARNING "BII_CONFIGURE_FILE is deprecated, should not be used anymore")
	configure_file(
	"${CMAKE_CURRENT_SOURCE_DIR}/${config_file_in}"
	"${CMAKE_CURRENT_BINARY_DIR}/${config_file_out}"
	)
endmacro()


#=============================================================================#
# [PUBLIC/USER] [USER BLOCK CMAKELISTS]
#
# BII_FILTER_LIB_SRC(ACCEPTABLE_SOURCES)
#
#        ACCEPTABLE_SOURCES    - List of sources to preserve
#
# Removes from biicode SRC list of calculated sources if not present in
# ACCEPTABLE_SOURCES.
#
#=============================================================================#

macro (BII_FILTER_LIB_SRC ACCEPTABLE_SOURCES)
	MESSAGE(WARNING "BII_FILTER_LIB_SRC is deprecated, should not be used anymore")
	set(FILES_TO_REMOVE )
	foreach(_cell ${BII_LIB_SRC})
	  list(FIND ${ACCEPTABLE_SOURCES} ${_cell} contains)
	  if(contains EQUAL  -1)
		list(APPEND FILES_TO_REMOVE ${_cell})
	  endif(contains) 
	endforeach()

	IF(FILES_TO_REMOVE)
		list(REMOVE_ITEM BII_LIB_SRC ${FILES_TO_REMOVE})
	ENDIF()
endmacro()


#=============================================================================#
# [PUBLIC/USER] [USER BLOCK CMAKELISTS]
#
# DISABLE_BII_IMPLICIT_RULES()
#
#
# Disables the BII_IMPLICIT_RULES_ENABLED (True by default) to link all our targets 
#
#=============================================================================#

macro(DISABLE_BII_IMPLICIT_RULES)
	unset(BII_IMPLICIT_RULES_ENABLED)
endmacro(DISABLE_BII_IMPLICIT_RULES)


#=============================================================================#
# [PUBLIC/USER] [MAIN BIICODE CMAKELISTS]
#
# BII_INCLUDE_BLOCK(BLOCK_DIR)
#
#        BLOCK_DIR    - Relative path to block, f.e.: blocks/myuser/simple_block
#
#
# Used by the root CMakeLists.txt.
#
# Initialize the necessary user block variables and validates the specific
# CMakeLists.txt.
#
# If this last one doesn't exist, biicode creates a default CMakLists.txt in
# that block
#
#=============================================================================#

macro(BII_INCLUDE_BLOCK BLOCK_DIR)
	get_filename_component(bii_user_dir ${BLOCK_DIR} PATH)
	get_filename_component(bii_base_dir ${bii_user_dir} PATH)
	if(bii_base_dir)
		get_filename_component(BII_BLOCK_PREFIX ${bii_base_dir} NAME)
	else()
		unset(BII_BLOCK_PREFIX)
	endif()
	get_filename_component(BII_BLOCK_NAME ${BLOCK_DIR} NAME)
	get_filename_component(BII_BLOCK_USER ${bii_user_dir} NAME)
	SET(bii_hive_dir ${BII_PROJECT_ROOT})
    SET(BII_IMPLICIT_RULES_ENABLED True)

	SET(vname "${BII_BLOCK_USER}_${BII_BLOCK_NAME}")
	# Load vars.cmake file with variables
	SET(var_file_name "bii_${vname}_vars.cmake")
	INCLUDE(${CMAKE_HOME_DIRECTORY}/${var_file_name})
	MESSAGE("\n\t\tBLOCK: ${BII_BLOCK_USER}/${BII_BLOCK_NAME} ")
	MESSAGE("-----------------------------------------------------------")

	IF(BII_BLOCK_PREFIX)
		SET(_cmakelist_path "${BII_PROJECT_ROOT}/${BLOCK_DIR}")
	ELSE()
		SET(_cmakelist_path "${BII_PROJECT_ROOT}")
	ENDIF()
	if(NOT EXISTS "${_cmakelist_path}/CMakeLists.txt")
		message(FATAL_ERROR "ERROR, MISSING CMakeLists.txt at: ${_cmakelist_path}")
	else()
		ADD_SUBDIRECTORY("${_cmakelist_path}" "${vname}")
	endif()
endmacro()


#=============================================================================#
# [PUBLIC/USER] [MAIN BIICODE CMAKELISTS]
#
# BII_PREBUILD_STEP(path)
#
#        path    - Relative path to block, f.e. : blocks/myuser/simple_block
#
# Called by the biicode main CMakeLists.txt, processes the biicode.configure 
# file if exists. Does nothing other case.
#
#=============================================================================#

function(BII_PREBUILD_STEP block_path)
	# Convenience per block Interface target
	get_filename_component(_bii_block_name ${block_path} NAME)
	get_filename_component(_aux ${block_path} PATH)
	get_filename_component(_bii_user_name ${_aux} NAME)
	get_filename_component(_bii_prefix ${_aux} PATH)
	SET(BII_BLOCK_TARGET "${_bii_user_name}_${_bii_block_name}_interface") 
	ADD_LIBRARY(${BII_BLOCK_TARGET} INTERFACE)
	IF(_bii_prefix)
		SET(_bii_deps_config_path "${BII_PROJECT_ROOT}/${block_path}/bii_deps_config.cmake")
	ELSE()
		SET(_bii_deps_config_path "${BII_PROJECT_ROOT}/bii_deps_config.cmake")
	ENDIF()
	if(EXISTS "${_bii_deps_config_path}")
		include("${_bii_deps_config_path}")
	endif()
endfunction()

#=============================================================================#
# [PRIVATE/INTERNAL]
#
# BII_SET_OPTION(name)
#
#        name    - Option name to save
#
# Saves in cache the passed option names 
#
#=============================================================================#

function (BII_SET_OPTION name)
	set(${name} ON CACHE BOOL "biicode" FORCE)
endfunction()

#=============================================================================#
# [PRIVATE/INTERNAL]
#
# BII_UNSET_OPTION(name)
#
#        name    - Option name to delete from cache
#
# Deletes from cache the passed option names 
#
#=============================================================================#


function (BII_UNSET_OPTION name)
	set(${name} OFF CACHE BOOL "biicode" FORCE)
endfunction()


#=============================================================================#
# [PRIVATE/INTERNAL]
#
# BII_GENERATE_EXECUTABLE(USER BLOCK FNAME)
#
#        USER    - User name
#        BLOCK   - Block folder name
#        FNAME   - Main file name 
#
# Creates the binary  target name. It's in charge of setting the necessary
# properties to the target and linking with the libraries that target depends on.
#
# It can create the C/C++ and Arduino binary target files.
#
#=============================================================================#

function(BII_GENERATE_EXECUTABLE USER BLOCK FNAME BII_CMAKE_VERSION)
	SET(exe_name "${USER}_${BLOCK}_${FNAME}")
	SET(aux_src ${BII_${FNAME}_SRC})

	if(COMMAND BII_ADD_EXECUTABLE)
        BII_ADD_EXECUTABLE(${exe_name} "${aux_src}")
    else()
        ADD_EXECUTABLE( ${exe_name} ${aux_src})
    endif()

    if(BII_${FNAME}_DEPS)
        TARGET_LINK_LIBRARIES( ${exe_name} PUBLIC ${BII_${FNAME}_DEPS})
    endif()
    if(BII_${FNAME}_INCLUDE_PATHS)
        target_include_directories( ${exe_name} PUBLIC ${BII_${FNAME}_INCLUDE_PATHS})
    endif()
    if(BII_${FNAME}_SYSTEM_HEADERS AND ${BII_CMAKE_VERSION} VERSION_LESS 2.8)
        HANDLE_SYSTEM_DEPS(${exe_name} PUBLIC "BII_${FNAME}_SYSTEM_HEADERS")
    endif()
endfunction() 


#=============================================================================#
# [PRIVATE/INTERNAL]
#
# BII_DEFINE_TEST(VNAME)
#
#        VNAME    - biicode target name
#
# Creates the binary test target name. Each test is excluded from build.
#
#=============================================================================#

macro(BII_DEFINE_TEST TEST_NAME)
    # Excluding from main building. They are only executed with "cmake --build . --target biitest"
    set_target_properties(${TEST_NAME} PROPERTIES EXCLUDE_FROM_ALL TRUE)
    # User could define his/her WORKING_DIRECTORY defining BII_TESTS_WORKING_DIR variable
    add_test(NAME ${TEST_NAME} WORKING_DIRECTORY ${BII_TESTS_WORKING_DIR} COMMAND ${TEST_NAME})
    # Add all the tests to main test target: biitest
    add_dependencies(biitest ${TEST_NAME})
    # Setting FAIL_REGULAR_EXPRESSION property to each test
    set_tests_properties(${TEST_NAME} PROPERTIES FAIL_REGULAR_EXPRESSION "FAILED")
endmacro(BII_DEFINE_TEST TEST_NAME)

#=============================================================================#
# [PRIVATE/INTERNAL]
#
# BII_GENERATE_LIB(lib_name)
#
#        lib_name   - Library name 
#
# Creates the library with the biicode target name. It's in charge of setting 
# the necessary properties to the target and linking with other libraries that
# target depends on.
#
# It can create the C/C++ and Arduino library target files. The libraries'll
# be STATIC by default.
#
#=============================================================================#
function(BII_LIB_HAS_SOURCES RESULT_VAR)
  if(NOT BII_SOURCES_EXTENSION_PATTERN)
    SET(BII_SOURCES_EXTENSION_PATTERN "\\.(c|cc|cpp|cxx|c\\+\\+|m|mm)$")
  endif()
  foreach(ITR ${ARGN})
    if(ITR MATCHES ${BII_SOURCES_EXTENSION_PATTERN})
      set(${RESULT_VAR} TRUE PARENT_SCOPE)
      return()
    endif()
  endforeach()
  set(${RESULT_VAR} FALSE PARENT_SCOPE)
endfunction()


function(BII_GENERATE_LIB lib_name BII_CMAKE_VERSION)
	# COMPUTE IF LIBRARY HAS SOURCES, generate cmake_dummy for old biicode.cmake version
	if(${BII_CMAKE_VERSION} VERSION_LESS 2.8)
	  SET(DUMMY_SRC "${CMAKE_CURRENT_BINARY_DIR}/cmake_dummy.cpp")
	  IF (NOT EXISTS ${DUMMY_SRC})
	          MESSAGE(STATUS "Writing default cmake_dummy.cpp for building library")
	          FILE (WRITE  ${DUMMY_SRC} "//a dummy file for building header only libs with CMake 2.8")
	  ENDIF()
  	  SET(BII_LIB_SRC ${BII_LIB_SRC} ${DUMMY_SRC})
  	  SET(HAS_SOURCES TRUE)
  	else()
		BII_LIB_HAS_SOURCES(HAS_SOURCES ${BII_LIB_SRC})
	endif()
	# Actual creation of the lib
    if(BII_LIB_SRC AND HAS_SOURCES)
        if(COMMAND BII_ADD_LIBRARY)
            BII_ADD_LIBRARY(${lib_name} "${BII_LIB_SRC}")
        else()
            add_library(${lib_name} ${BII_LIB_TYPE} ${BII_LIB_SRC})
        endif()
        set(TRANSITIVE PUBLIC)
    else()
        add_library(${lib_name} INTERFACE)
        set(TRANSITIVE INTERFACE)
    endif()

    # SET PROPERTIES of LIB
    if(BII_LIB_DEPS)
        TARGET_LINK_LIBRARIES( ${lib_name} ${TRANSITIVE} ${BII_LIB_DEPS})
    endif()
    if(BII_LIB_INCLUDE_PATHS)
        target_include_directories( ${lib_name} ${TRANSITIVE} ${BII_LIB_INCLUDE_PATHS})
    endif()
    if(BII_LIB_SYSTEM_HEADERS AND ${BII_CMAKE_VERSION} VERSION_LESS 2.8)
        HANDLE_SYSTEM_DEPS(${lib_name} ${TRANSITIVE} "BII_LIB_SYSTEM_HEADERS")
    endif()
endfunction()


#=============================================================================#
# [PRIVATE/INTERNAL]
#
# HANDLE_SYSTEM_DEPS(target_name sys_deps)
#
#        target_name    - Complete target name, f.e.: myuser_myblock_main
#        sys_deps       - System dependencies detected by biicode 
#
# Links the passed targets with the selected system dependencies
#
#=============================================================================#

function(HANDLE_SYSTEM_DEPS target_name ACCESS sys_deps)
	if((${BII_IMPLICIT_RULES_ENABLED}) AND NOT (${CMAKE_SYSTEM_NAME} STREQUAL "Arduino") AND NOT ANDROID)
		foreach(sys_dep ${${sys_deps}})
			if(${sys_dep} STREQUAL "math.h")
				if(UNIX)
					target_link_libraries(${target_name} ${ACCESS} "m")
				endif()
			elseif((${sys_dep} STREQUAL "pthread.h") OR (${sys_dep} STREQUAL "thread"))
				if(UNIX)
					target_link_libraries(${target_name} ${ACCESS} "pthread")
				endif()
			elseif(${sys_dep} STREQUAL "GL/gl.h")
				if(APPLE)
					FIND_LIBRARY(OpenGL_LIBRARY OpenGL)
					target_link_libraries(${target_name} ${ACCESS} ${OpenGL_LIBRARY})
				elseif(UNIX)
					target_link_libraries(${target_name} ${ACCESS} "GL")
				elseif(WIN32)
					target_link_libraries(${target_name} ${ACCESS} "opengl32")
				endif()
			elseif(${sys_dep} STREQUAL "GL/glu.h")
				if(UNIX)
					if(APPLE)
						FIND_PACKAGE(GLU REQUIRED)
						TARGET_LINK_LIBRARIES(${target_name} ${ACCESS} ${GLU_LIBRARY})
					else()
						target_link_libraries(${target_name} ${ACCESS} "GLU")
					endif()
				elseif(WIN32)
					target_link_libraries(${target_name} ${ACCESS} "glu32")
				endif()
			elseif(${sys_dep} STREQUAL "winsock2.h")
				if(WIN32)
					target_link_libraries(${target_name} ${ACCESS} "ws2_32")
				endif()
			elseif(${sys_dep} STREQUAL "mmsystem.h")
				if(WIN32)
					target_link_libraries(${target_name} ${ACCESS} "winmm")
				endif()
			endif()
		endforeach()
	endif()

endfunction()
