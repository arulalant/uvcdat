# Create an external project to clone vistrails,
# and configure and build it

include(GetGitRevisionDescription)
set(vistrails_branch master)

get_git_head_revision(refspec sha)
if("${refspec}" STREQUAL "refs/heads/devel-master")
  set(vistrails_branch uvcdat-next)
endif()

set(vistrails_tag_point_message "Specify branch of vistrails to be used for UVCDAT")
set(vistrails_tag_point ${vistrails_branch} CACHE STRING "${vistrails_tag_point_message}")
set(vistrails_url "${GIT_PROTOCOL}github.com/OpenGeoscience/VisTrails.git")

if(CDAT_AUTO_UPDATE_VISTRAILS_TAG_POINT)
  set(vistrails_tag_point ${vistrails_branch} CACHE STRING "${vistrails_tag_point_message}" FORCE)
endif()


# For configure purposes
set(SOURCE_DIR "${CMAKE_INSTALL_PREFIX}/vistrails")
set(BRANCH ${vistrails_tag_point})
set(GIT_URL "${vistrails_url}")

option(CDAT_DELETE_VISTRAILS_HISTORY "Delete GIT history of vistrails" OFF)
option(CDAT_AUTO_UPDATE_VISTRAILS_TAG_POINT "Delete GIT history of vistrails" ON)

set(vistrails_install_command ${cdat_BINARY_DIR}/git_clone_vistrails.sh)
if(EXISTS "${SOURCE_DIR}")
  configure_file(
    ${cdat_CMAKE_SOURCE_DIR}/cdat_modules_extra/git_update.sh.in
    ${cdat_BINARY_DIR}/git_update_vistrails.sh
    @ONLY
  )
  set(vistrails_install_command ${cdat_BINARY_DIR}/git_update_vistrails.sh)
else()
  configure_file(
    ${cdat_CMAKE_SOURCE_DIR}/cdat_modules_extra/git_clone.sh.in
    ${cdat_BINARY_DIR}/git_clone_vistrails.sh
    @ONLY
  )
endif()

ExternalProject_Add(vistrails
  DOWNLOAD_DIR ${CDAT_PACKAGE_CACHE_DIR}
  SOURCE_DIR ${CMAKE_INSTALL_PREFIX}
  BUILD_IN_SOURCE 0
  CONFIGURE_COMMAND ""
  BUILD_COMMAND ""
  INSTALL_COMMAND ${vistrails_install_command}
  DEPENDS ${vistrails_DEPENDENCIES}
  ${EP_LOG_OPTIONS}
)

if(CDAT_DELETE_VISTRAILS_HISTORY)
  ExternalProject_Add_Step(vistrails after_install
    COMMAND ${CMAKE_COMMAND} -E remove_directory ${CMAKE_INSTALL_PREFIX}/vistrails/.git
    DEPENDEES install
    WORKING_DIRECTORY ${CMAKE_INSTALL_PREFIX}/vistrails
  )
endif()

