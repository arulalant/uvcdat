set(ESMF_deps ${pkgconfig_pkg} ${python_pkg})

if(CDAT_BUILD_ESMF_PARALLEL)
  set(ESMF_deps ${mpi_pkg} ${ESMF_deps})
endif()
