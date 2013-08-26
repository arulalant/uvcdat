set(NUMEXPR_MAJOR 2)
set(NUMEXPR_MINOR 1)
set(NUMEXPR_PATCH 0)
set(NUMEXPR_VERSION ${NUMEXPR_MAJOR}.${NUMEXPR_MINOR}.${NUMEXPR_PATCH})
set(NUMEXPR_VERSION ${NUMEXPR_MAJOR}.${NUMEXPR_MINOR})
# Following not needed any longer using easy_install
#set(NUMEXPR_URL http://numexpr.googlecode.com/files/)
#set(NUMEXPR_GZ numexpr-${NUMEXPR_VERSION}.tar.gz)
#set(NUMEXPR_MD5 139115cc196dc57a66b2eb30cd3e80a0 )

add_sb_package(NAME Numexpr GROUPS "SYSTEM" DEFAULT ON)
