cmake_minimum_required(VERSION 3.10)
project(usb_daq)

set(CMAKE_CXX_STANDARD 17)

include_directories(libusb/include)
include_directories(asio/include)
link_directories(libusb/lib)

add_executable(server
    server.cpp
    usb-daq-v20.cpp
)

target_link_libraries(server
    usb-1.0
    ws2_32
)

# Copy runtime DLLs next to server.exe so it can start without PATH setup.
add_custom_command(TARGET server POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_SOURCE_DIR}/libusb/lib/libusb-1.0.dll"
        "$<TARGET_FILE_DIR:server>"
    COMMENT "Copy libusb-1.0.dll"
)

if(MINGW)
    foreach(_dll IN ITEMS libwinpthread-1.dll libstdc++-6.dll libgcc_s_seh-1.dll)
        add_custom_command(TARGET server POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${CMAKE_CXX_COMPILER}/../${_dll}"
                "$<TARGET_FILE_DIR:server>"
            COMMENT "Copy ${_dll}"
        )
    endforeach()
endif()


# cmake .. -G "MinGW Makefiles"
# cmake --build .