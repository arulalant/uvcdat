set(VISTRAILS_VERSION ${VISTRAILS_TAG_POINT})
set(VISTRAILS_SOURCE "${GIT_PROTOCOL}vistrails.org/git/vistrails.git")
set(VISTRAILS_VERSION uvcdat-master)
## Now tarball so faking md5 to tell checkout point
set(VISTRAILS_MD5 uvcdat-master)
add_sb_package(NAME vistrails GROUPS GUI DEFAULT ON)
