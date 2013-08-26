set(PIP_MAJOR_SRC 1)
set(PIP_MINOR_SRC 3)
set(PIP_PATCH_SRC 1)

set (nm PIP)
string(TOUPPER ${nm} uc_nm)
set(${uc_nm}_VERSION ${${nm}_MAJOR_SRC}.${${nm}_MINOR_SRC}.${${nm}_PATCH_SRC})
#set(${uc_nm}_VERSION ${${nm}_MAJOR_SRC}.${${nm}_MINOR_SRC})

add_sb_package(NAME pip GROUP "SYSTEM" DEFAULT ON)
