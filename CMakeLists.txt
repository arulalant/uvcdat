
#-----------------------------------------------------------------------------
cmake_minimum_required(VERSION 2.8.4)
#-----------------------------------------------------------------------------

project(cdat)

set(cdat_CMAKE_SOURCE_DIR ${cdat_SOURCE_DIR}/CMake)
set(cdat_CMAKE_BINARY_DIR ${cdat_BINARY_DIR}/CMake)
set(cdat_external_patch_dir ${cdat_SOURCE_DIR}/exsrc)

if("${CMAKE_INSTALL_PREFIX}" STREQUAL "/usr/local")
  get_filename_component(cdat_ROOT_DIR ${cdat_BINARY_DIR} PATH)
  set(CMAKE_INSTALL_PREFIX ${cdat_ROOT_DIR}/install CACHE STRING "" FORCE)
endif()

set(cdat_EXTERNALS ${CMAKE_INSTALL_PREFIX}/Externals)

#------------------------------------------------------------------------------
# Update CMake module path
#------------------------------------------------------------------------------

set(CMAKE_MODULE_PATH
  ${cdat_CMAKE_SOURCE_DIR}
  ${cdat_CMAKE_BINARY_DIR}
  ${CMAKE_MODULE_PATH}
  )

#-----------------------------------------------------------------------------
# CDat version
#------------------------------------------------------------------------------
set(cdat_VERSION_MAJOR 6)
set(cdat_VERSION_MINOR 0)
set(cdat_VERSION_PATCH "alpha")
set(cdat_VERSION ${cdat_VERSION_MAJOR}.${cdat_VERSION_MINOR}.${cdat_VERSION_PATCH})

# configure version file
configure_file(${cdat_CMAKE_SOURCE_DIR}/version.in
  ${cdat_SOURCE_DIR}/version
  @ONLY)

##############################################################################
# Important: change architecture *before* any enable_language() or project()
# calls so that it's set properly to detect 64-bit-ness...
#
if(APPLE)

  string(REGEX REPLACE "^([0-9]+)\\.([0-9]+).*$" "\\1" OSX_VER_MAJOR "${CURRENT_OSX_VERSION}")
  string(REGEX REPLACE "^([0-9]+)\\.([0-9]+).*$" "\\2" OSX_VER_MINOR "${CURRENT_OSX_VERSION}")

  if("${CMAKE_OSX_DEPLOYMENT_TARGET}" STREQUAL "")
    set(CMAKE_OSX_ARCHITECTURES "x86_64" CACHE STRING "" FORCE)
    set(CMAKE_OSX_DEPLOYMENT_TARGET "${OSX_VER_MAJOR}.${OSX_VER_MINOR}" CACHE STRING "" FORCE)
  endif()

  if(NOT "${CMAKE_OSX_SYSROOT}" STREQUAL "")
    if(NOT EXISTS "${CMAKE_OSX_SYSROOT}")
      message(FATAL_ERROR "error: CMAKE_OSX_SYSROOT='${CMAKE_OSX_SYSROOT}' does not exist")
    endif()
  endif()
endif()

#-----------------------------------------------------------------------------
# Git protocol option
#-----------------------------------------------------------------------------

option(GIT_USE_GIT_PROTOCOL "If behind a firewall turn this off to use http instead." ON)

set(git_protocol "git")
if(NOT Slicer_USE_GIT_PROTOCOL)
  set(git_protocol "http")
endif()

#-----------------------------------------------------------------------------
# Initialize git submodules.
#-----------------------------------------------------------------------------

find_package(Git)

if(GIT_FOUND)
  message("Updating git submodules")

  execute_process(
    COMMAND ${GIT_EXECUTABLE} submodule init
    WORKING_DIRECTORY ${cdat_SOURCE_DIR}
  )
  execute_process(
    COMMAND ${GIT_EXECUTABLE} submodule update
    WORKING_DIRECTORY ${cdat_SOURCE_DIR}
  )
endif()

#-----------------------------------------------------------------------------
# Attempt to detect if we have a Fortran Compiler available.
#-----------------------------------------------------------------------------

include(CheckFortran)

if(CMAKE_Fortran_COMPILER)
  enable_language(Fortran)
endif(CMAKE_Fortran_COMPILER)

#-----------------------------------------------------------------------------
# Enable and setup External project global properties
#-----------------------------------------------------------------------------

set(EP_PREFIX ${cdat_BINARY_DIR}/build/prefix)

set_property(DIRECTORY PROPERTY EP_LOG_DIR  ${cdat_BINARY_DIR}/logs)

set(EP_LOG_OPTIONS
  LOG_DOWNLOAD 1
  LOG_UPDATE 1
  LOG_CONFIGURE 1
  LOG_BUILD 1
  LOG_TEST 1
  LOG_INSTALL 1
)

INCLUDE(ExternalProject)

# ----------------------------------------------------------------------------
# generic compiler args (compiler and cflags) to pass to subprojects
#-----------------------------------------------------------------------------

set(cdat_compiler_args
  -DCMAKE_CXX_COMPILER:FILEPATH=${CMAKE_CXX_COMPILER}
  -DCMAKE_C_COMPILER:FILEPATH=${CMAKE_C_COMPILER}
  -DCMAKE_CXX_FLAGS_DEBUG:STRING=${CMAKE_CXX_FLAGS_DEBUG}
  -DCMAKE_CXX_FLAGS_MINSIZEREL:STRING=${CMAKE_CXX_FLAGS_MINSIZEREL}
  -DCMAKE_CXX_FLAGS_RELEASE:STRING=${CMAKE_CXX_FLAGS_RELEASE}
  -DCMAKE_CXX_FLAGS_RELWITHDEBINFO:STRING=${CMAKE_CXX_FLAGS_RELWITHDEBINFO}
  -DCMAKE_C_FLAGS_DEBUG:STRING=${CMAKE_C_FLAGS_DEBUG}
  -DCMAKE_C_FLAGS_MINSIZEREL:STRING=${CMAKE_C_FLAGS_MINSIZEREL}
  -DCMAKE_C_FLAGS_RELEASE:STRING=${CMAKE_C_FLAGS_RELEASE}
  -DCMAKE_C_FLAGS_RELWITHDEBINFO:STRING=${CMAKE_C_FLAGS_RELWITHDEBINFO}
  -DCMAKE_EXE_LINKER_FLAGS:STRING=${CMAKE_EXE_LINKER_FLAGS}
  -DCMAKE_SHARED_LINKER_FLAGS:STRING=${CMAKE_SHARED_LINKER_FLAGS}
)

set(cdat_tpl_cxx_flags ${CMAKE_CXX_FLAGS})
set(cdat_tpl_c_flags ${CMAKE_C_FLAGS})
set(cdat_cxx_flags ${CMAKE_CXX_FLAGS})
set(cdat_c_flags ${CMAKE_C_FLAGS})

if(APPLE)
  set(cdat_rpath_flag -R)
else()
  set(cdat_rpath_flag -Wl,--rpath,)
endif()

if(WIN32)
  list(APPEND cdat_compiler_args -DCMAKE_BUILD_TYPE:STRING=${CMAKE_CFG_INTDIR})
else()
  list(APPEND cdat_compiler_args -DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE})
endif()

if(APPLE)
  set(cdat_apple_compiler_args
    -DCMAKE_OSX_ARCHITECTURES:STRING=${CMAKE_OSX_ARCHITECTURES}
    -DCMAKE_OSX_DEPLOYMENT_TARGET:STRING=${CMAKE_OSX_DEPLOYMENT_TARGET}
    -DCMAKE_OSX_SYSROOT:PATH=${CMAKE_OSX_SYSROOT})

  set(cdat_osx_arch_flag "-arch ${CMAKE_OSX_ARCHITECTURES} -Xarch_${CMAKE_OSX_ARCHITECTURES}")
  set(cdat_osx_version_flag "-mmacosx-version-min=${CMAKE_OSX_DEPLOYMENT_TARGET}")
  set(cdat_osx_sysroot "-isysroot ${CMAKE_OSX_SYSROOT}")
  set(cdat_osx_flags "${cdat_osx_arch_flag} ${cdat_osx_version_flag} ${cdat_osx_sysroot} -pipe")
  set(cdat_osx_ld_flags "-bind_at_load -mmacosx-version-min=${CMAKE_OSX_DEPLOYMENT_TARGET}")
endif()

if(WIN32)
  set(LIBRARY_PATH PATH)
  set(CMAKE_PLATFORM WIN32)
  set(_LINK_LIBRARY_SUFFIX .lib)
elseif(APPLE)
  set(LIBRARY_PATH DYLD_LIBRARY_PATH)
  set(CMAKE_PLATFORM APPLE)
  set(_LINK_LIBRARY_SUFFIX .dylib)
else()
  set(LIBRARY_PATH LD_LIBRARY_PATH)
  set(CMAKE_PLATFORM UNIX)
  set(_LINK_LIBRARY_SUFFIX .so)
endif()

#-----------------------------------------------------------------------------
# Create binary subdirectories
#-----------------------------------------------------------------------------

# Here we create several of binary directory subdirectories as often
# third party install systems do bad things when left to create them.

file(MAKE_DIRECTORY ${cdat_EXTERNALS} ${cdat_EXTERNALS}/lib ${cdat_EXTERNALS}/bin ${cdat_EXTERNALS}/include)

file(MAKE_DIRECTORY ${cdat_BINARY_DIR}/logs)
file(MAKE_DIRECTORY ${cdat_SOURCE_DIR}/logs)
file(MAKE_DIRECTORY ${cdat_SOURCE_DIR}/libcdms)
file(MAKE_DIRECTORY ${cdat_BINARY_DIR}/build)
file(MAKE_DIRECTORY ${cdat_BINARY_DIR}/sources)

#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------

include(PackageVersions)

set(external_packages)
set(found_system_include_dirs)
set(found_system_libraries)

macro (add_cdat_package package)
  string(TOUPPER ${package} UC_PACKAGE)
  string(TOLOWER ${package} LC_PACKAGE)
  if(NOT DEFINED CDAT_USE_SYSTEM_${UC_PACKAGE})
    if(NOT ${UC_PACKAGE}_FOUND)
      option(CDAT_USE_SYSTEM_${UC_PACKAGE} "Use system installed ${LC_PACKAGE}" OFF)
    else()
      option(CDAT_USE_SYSTEM_${UC_PACKAGE} "Use system installed ${LC_PACKAGE}" ON)
    endif()
  endif()

  if(NOT ${UC_PACKAGE}_FOUND AND NOT ${CDAT_USE_SYSTEM_${UC_PACKAGE}})
    list(APPEND external_packages External_${package})
    set(${package}_dep ${package})
  else()
    unset(${package}_dep)
    if(external_packages)
      list(REMOVE_ITEM external_packages External_${package})
    endif()

    if(${UC_PACKAGE}_INCLUDE_DIR)
      list(APPEND found_system_include_dirs ${${UC_PACKAGE}_INCLUDE_DIR})
      message("  Including: ${UC_PACKAGE}_INCLUDE_DIR: ${${UC_PACKAGE}_INCLUDE_DIR}")
    endif()

    if(${UC_PACKAGE}_LIBRARY)
      get_filename_component(lib_path ${${UC_PACKAGE}_LIBRARY} PATH)
      list(APPEND found_system_libraries ${lib_path})
      message("  Linking: ${UC_PACKAGE}_LIBRARY: ${lib_path}")
    endif()
  endif()
endmacro (add_cdat_package)

find_package(Qt4)

option(CDAT_USE_SYSTEM_INTROSPECTION "Detect System installed libraries." OFF)

# Attempt to find each package on the system

find_package(MD5)
find_package(Wget)

# By default lets build everything but make an exception for Qt.
if(CDAT_USE_SYSTEM_INTROSPECTION)

find_package(PkgConfig)
set(PKGCONFIG_FOUND ${PKG_CONFIG_FOUND})

find_package(CURL)
find_package(LibXml2)
find_package(LibXslt)
#find_package(XGKS)
#find_package(PBMPLUS)
find_package(FFMPEG)
#find_package(gifsicle)
#find_package(GS)
find_package(TIFF)
find_package(JPEG)
find_package(BLAS)
find_package(LAPACK)
find_package(ZLIB)
# This will find the png framework which Cairo won't find.
if(NOT APPLE)
  find_package(PNG)
  find_package(Freetype)
endif()
#find_package(pixman)
#find_package(fontconfig)
find_package(Cairo)

# CMOR doesn't know how to configure with the System frameworks version of uuid
if(NOT APPLE)
  find_package(UUID)
endif()
#find_package(udunits2)
find_package(HDF5)
#find_package(NetCDF)
#find_package(PythonInterp)
#find_package(PythonLibs)
# unix tools
find_package(TermCap)
find_package(Readline)
##find_package(TCL)
# python packages
#find_package(setuptools)
#find_package(PyOpenGL)
#find_package(NUMPY)
# python mega widgets
#find_package(PMW)

endif(CDAT_USE_SYSTEM_INTROSPECTION)

if(NOT PKG_CONFIG_FOUND)
  set(cdat_PKG_CONFIG_EXECUTABLE ${cdat_EXTERNALS}/bin/pkg-config)
else()
  set(cdat_PKG_CONFIG_EXECUTABLE ${PKG_CONFIG_EXECUTABLE})
endif()

set(cdat_configure_command ${CMAKE_COMMAND} -P ${cdat_CMAKE_BINARY_DIR}/cdat_configure_step.cmake)
set(cdat_make_command ${CMAKE_COMMAND} -P ${cdat_CMAKE_BINARY_DIR}/cdat_make_step.cmake)
set(cdat_install_command ${CMAKE_COMMAND} -P ${cdat_CMAKE_BINARY_DIR}/cdat_install_step.cmake)

#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
add_cdat_package(wget)
add_cdat_package(pkgconfig)
add_cdat_package(termcap)
add_cdat_package(readline)
add_cdat_package(libXML2)
add_cdat_package(libXSLT)
add_cdat_package(zlib)
add_cdat_package(CURL)

# Probably should be eliminated since we use Qt now.
#if(0)
#  add_cdat_package(xgks)
#endif()

add_cdat_package(FFMPEG)
#add_cdat_package(gifsicle)
add_cdat_package(png)
add_cdat_package(jpeg)
add_cdat_package(tiff)

#if(APPLE)
  # really old package that doesn't often build on linux.
#  add_cdat_package(pbmplus)
#endif()

add_cdat_package(TclTk)

# On OSX use vecLib framework
if(NOT APPLE)
  if(CMAKE_Fortran_COMPILER)
    add_cdat_package(LAPACK)
  else()
    add_cdat_package(CLAPACK)
  endif()
endif()

add_cdat_package(freetype)
add_cdat_package(pixman)
add_cdat_package(fontconfig)
add_cdat_package(Cairo)
add_cdat_package(uuid)
add_cdat_package(udunits2)
#add_cdat_package(ghostscript)
#add_cdat_package(HDF4) 
add_cdat_package(HDF5)
add_cdat_package(NetCDF)
add_cdat_package(Qt)
add_cdat_package(jasper)
add_cdat_package(g2clib)

# Python Packages
add_cdat_package(Python)
add_cdat_package(setuptools)
add_cdat_package(SIP)
add_cdat_package(PyQt)
add_cdat_package(PyOpenGL)
add_cdat_package(NUMPY)
add_cdat_package(Pmw)

option(CDAT_BUILD_PARAVIEW "Build ParaView" OFF)
if(CDAT_BUILD_PARAVIEW)
  add_cdat_package(ParaView)
endif()

add_cdat_package(CMOR)
add_cdat_package(CDAT)
add_cdat_package(gui_support)

option(CDAT_BUILD_VISTRAILS "Build VisTrails" OFF)
if(CDAT_BUILD_VisTrails)
  add_cdat_package(VisTrails)
endif()

#-----------------------------------------------------------------------------
# Construct Include and Link variables
#-----------------------------------------------------------------------------

#set(system_include_dirs)
if(found_system_include_dirs)
  list(REMOVE_DUPLICATES found_system_include_dirs)
  list(REMOVE_ITEM found_system_include_dirs ${CMAKE_CXX_IMPLICIT_INCLUDE_DIRECTORIES} ${CMAKE_C_IMPLICIT_INCLUDE_DIRECTORIES})
  set(cdat_external_include_directories)
  foreach(include_dir ${found_system_include_dirs})
    set(cdat_external_include_directories "-I${include_dir} ${cdat_external_include_directories}")
  endforeach()
endif()
message("cdat_external_include_directories: ${cdat_external_include_directories}")


#set(system_libraries)
message("found_system_libraries ${found_system_libraries}")
if(found_system_libraries)
  list(REMOVE_DUPLICATES found_system_libraries)
  list(REMOVE_ITEM found_system_libraries ${CMAKE_PLATFORM_IMPLICIT_LINK_DIRECTORIES})
  set(cdat_external_link_directories)
  foreach(library_dir ${found_system_libraries})
    set(cdat_external_link_directories "-L${library_dir} ${cdat_external_link_directories}")
  endforeach()
endif()
message("cdat_external_link_directories: ${cdat_external_link_directories}")

#-----------------------------------------------------------------------------
# configure custom configure/build/install step files
#-----------------------------------------------------------------------------

configure_file(${cdat_CMAKE_SOURCE_DIR}/cdat_common_environment.cmake.in
    ${cdat_CMAKE_BINARY_DIR}/cdat_common_environment.cmake
    @ONLY)

configure_file(${cdat_CMAKE_SOURCE_DIR}/cdat_configure_step.cmake.in
    ${cdat_CMAKE_BINARY_DIR}/cdat_configure_step.cmake
    @ONLY)

configure_file(${cdat_CMAKE_SOURCE_DIR}/cdat_make_step.cmake.in
  ${cdat_CMAKE_BINARY_DIR}/cdat_make_step.cmake
  @ONLY)

configure_file(${cdat_CMAKE_SOURCE_DIR}/cdat_cmake_make_step.cmake.in
  ${cdat_CMAKE_BINARY_DIR}/cdat_cmake_make_step.cmake
  @ONLY)

configure_file(${cdat_CMAKE_SOURCE_DIR}/cdat_install_step.cmake.in
  ${cdat_CMAKE_BINARY_DIR}/cdat_install_step.cmake
  @ONLY)

#configure_file(${cdat_CMAKE_SOURCE_DIR}/cdat_python_install_step.cmake.in
#  ${cdat_CMAKE_BINARY_DIR}/cdat_python_install_step.cmake
#  @ONLY)

#------------------------------------------------------------------------------
# Establish Target Dependencies based on Selected Options and find results
#------------------------------------------------------------------------------

set(wget_DEPENDENCIES)
set(pkgconfig_DEPDENCIES ${wget_dep})
set(termcap_DEPENDENCIES ${pkgconfig_dep})
set(readline_DEPENDENCIES ${pkgconfig_dep} ${termcap_dep})
set(uuid_DEPENDENCIES ${pkgconfig_dep})
set(udunits2_DEPENDENCIES ${pkgconfig_dep})
set(libXML2_DEPENDENCIES ${pkgconfig_dep} ${readline_dep})
set(libXSLT_DEPENDENCIES ${pkgconfig_dep} ${readline_dep} ${libXML2_dep})
set(jpeg_DEPENDENCIES ${pkgconfig_dep})
set(zlib_DEPENDENCIES ${pkgconfig_dep})
set(CURL_DEPENDENCIES ${pkgconfig_dep} ${libXML2_dep} ${zlib_dep})
set(png_DEPENDENCIES ${pkgconfig_dep} ${zlib_dep})
set(tiff_DEPENDENCIES ${pkgconfig_dep} ${jpeg_dep} ${zlib_dep})
set(jasper_DEPENDENCIES ${pkgconfig_dep} ${jpeg_dep} ${zlib_dep})
#set(gifsicle_DEPENDENCIES ${pkgconfig_dep})
set(pbmplus_DEPENDENCIES ${pkgconfig_dep} ${tiff_dep} ${jpeg_dep} ${zlib_dep})
set(freetype_DEPENDENCIES ${pkgconfig_dep} ${png_dep})
set(fontconfig_DEPENDENCIES ${pkgconfig_dep} ${libXML2_dep} ${freetype_dep})
set(g2clib_DEPENDENCIES ${pkgconfig_dep} ${png_dep} ${zlib_dep} ${jasper_dep})
set(Python_DEPENDENCIES ${pkgconfig_dep} ${termcap_dep} ${readline_dep} ${TclTk_dep} ${libXML2_dep} ${CURL_dep} ${zlib_dep} ${libXSLT_dep} ${png_dep} ${jpeg_dep} ${tiff_dep})
set(SIP_DEPENDENCIES ${pkgconfig_dep} ${Python_dep})
set(Qt_DEPENDENCIES ${pkgconfig_dep} ${readline_dep} ${libXML2_dep} ${jpeg_dep} ${zlib_dep} ${png_dep} ${tiff_dep} ${fontconfig_dep} ${fontconfig_dep})
set(PyQt_DEPENDENCIES ${pkgconfig_dep} ${Qt_dep} ${SIP_dep})
set(PyOpenGL_DEPENDENCIES ${pkgconfig_dep} ${Python_dep})
set(Pmw_DEPENDENCIES ${pkgconfig_dep} ${Python_dep})
set(pixman_DEPENDENCIES ${pkgconfig_dep})
set(FFMPEG_DEPENDENCIES ${pkgconfig_dep})
set(ghostscript_DEPENDENCIES ${pkgconfig_dep} ${zlib_dep} ${jpeg_dep} ${png_dep} ${fontconfig_dep} ${freetype_dep} ${pixman_dep} ${libXSLT_dep} ${libXML2_dep})
set(NetCDF_DEPENDENCIES ${pkgconfig_dep} ${HDF5_dep} ${CURL_dep} ${zlib_dep})

set(TclTk_DEPENDENCIES ${pkgconfig_dep} ${libXML2_dep} ${libXSLT_dep} ${jpeg_dep} ${png_dep} ${tiff_dep})

set(setuptools_DEPENDENCIES ${pkgconfig_dep} ${Python_dep})
set(LAPACK_DEPENDENCIES ${pkgconfig_dep})
set(CLAPACK_DEPENDENCIES ${pkgconfig_dep})
set(NUMPY_DEPENDENCIES ${pkgconfig_dep} ${Python_dep} ${CLAPACK_dep} ${LAPACK_dep})

set(VTK_DEPENDENCIES ${pkgconfig_dep} ${zlib_deb} ${png_dep} ${jpeg_dep} ${xml_dep})
set(Cairo_DEPENDENCIES ${pkgconfig_dep} ${png_dep} ${fontconfig_dep} ${freetype_dep} ${pixman_dep})
set(HDF4_DEPENDENCIES ${pkgconfig_dep} ${zlib_dep} ${jpeg_dep})
set(HDF5_DEPENDENCIES ${pkgconfig_dep} ${libXML2_dep} ${libXSLT_dep} ${zlib_dep})

set(ParaView_DEPENDENCIES ${pkgconfig_dep} ${Python_dep} ${HDF5_dep} ${png_dep} ${jpeg_dep} ${libXML2_dep} ${Qt_dep} ${freetype_dep} ${NetCDF_dep} ${zlib_dep})

set(CMOR_DEPENDENCIES ${pkgconfig_dep} ${Python_dep} ${HDF5_dep} ${Cairo_dep} ${png_dep} ${fontconfig_dep} ${freetype_dep} ${pixman_dep} ${NetCDF_dep} ${zlib_dep} ${uuid_dep} ${udunits2_dep})
set(CDAT_DEPENDENCIES ${wget_dep} ${CMOR_dep} ${Python_dep} ${PyQt_dep} ${PyOpenGL_dep} ${NUMPY_dep} ${Pmw_dep} ${jasper_dep} ${g2clib_dep} ${FFMPEG_dep} ${Qt_dep} ${pixman_dep} ${tiff_dep})
set(gui_support_DEPENDENCIES ${CDAT_dep})
set(VisTrails_DEPENDENCIES ${ParaView_dep} ${CDAT_dep})

message("readline_DEPENDENCIES ${readline_DEPENDENCIES}")
message("libXML2_DEPENDENCIES ${libXML2_DEPENDENCIES}")
message("libXSLT_DEPENDENCIES ${libXSLT_DEPENDENCIES}")
message("zlib_DEPENDENCIES ${zlib_DEPENDENCIES}")
message("png_DEPENDENCIES ${png_DEPENDENCIES}")
message("tcl_DEPENDENCIES ${tcl_DEPENDENCIES}")
message("Python_DEPENDENCIES ${Python_DEPENDENCIES}")
message("SIP_DEPENDENCIES ${SIP_DEPENDENCIES}")
message("NetCDF_DEPENDENCIES ${NetCDF_DEPENDENCIES}")
message("Pmw_DEPENDENCIES ${Pmw_DEPENDENCIES}")
message("ghostscript_DEPENDENCIES ${ghostscript_DEPENDENCIES}")
message("VTK_DEPENDENCIES ${VTK_DEPENDENCIES}")
message("Cairo_DEPENDENCIES ${Cairo_DEPENDENCIES}")
message("CMOR_DEPENDENCIES ${CMOR_DEPENDENCIES}")
message("CDAT_DEPENDENCIES ${CDAT_DEPENDENCIES}")

list(REMOVE_DUPLICATES external_packages)
foreach(package ${external_packages})
  message("Building ${package}")
  include(${package})
endforeach()

#-----------------------------------------------------------------------------
# checked_get
#-----------------------------------------------------------------------------

set(HASWGET ${WGET_EXECUTABLE})
set(MD5PRG ${MD5_EXECUTABLE})
set(MD5CNT 1)

configure_file(${cdat_SOURCE_DIR}/checked_get.sh.in
  ${cdat_SOURCE_DIR}/checked_get.sh
  @ONLY)

include(CDATLogger)
