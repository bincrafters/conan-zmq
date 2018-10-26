#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, tools, CMake
import os
import fnmatch


class ZMQConan(ConanFile):
    name = "zmq"
    version = "4.2.2"
    url = "https://github.com/bincrafters/conan-zmq"
    description = "ZeroMQ is a community of projects focused on decentralized messaging and computing"
    license = "LGPL-3.0"
    exports = ["LICENSE.md"]
    exports_sources = ['FindZeroMQ.cmake', 'Findlibzmq.cmake', 'CMakeLists.txt']
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False], "encryption": [None, "libsodium", "tweetnacl"]}
    default_options = {'shared': False, 'fPIC': True, 'encryption': 'libsodium'}
    generators = ['cmake']
    _source_subfolder = "sources_subfolder"
    _build_subfolder = "build_subfolder"

    def _configure_cmake(self):
        cmake = CMake(self)
        if self.settings.compiler != 'Visual Studio':
            cmake.definitions['CMAKE_POSITION_INDEPENDENT_CODE'] = self.options.fPIC
        cmake.definitions['ENABLE_CURVE'] = self.options.encryption is not None
        cmake.definitions['WITH_LIBSODIUM'] = self.options.encryption == "libsodium"
        cmake.definitions['CMAKE_INSTALL_LIBDIR'] = 'lib'
        cmake.definitions['ZMQ_BUILD_TESTS'] = False
        cmake.definitions['WITH_PERF_TOOL'] = False
        cmake.configure(build_dir='build')
        return cmake

    def configure(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        if self.options.encryption == 'libsodium':
            self.requires.add('libsodium/1.0.16@bincrafters/stable')

    def source(self):
        # see https://github.com/zeromq/libzmq/issues/2597
        extracted_dir = "libzmq-%s" % self.version
        archive_name = "v%s.tar.gz" % self.version
        source_url = "https://github.com/zeromq/libzmq/archive/%s" % archive_name
        tools.get(source_url)
        os.rename(extracted_dir, self._source_subfolder)

        # disable precompiled headers
        # fatal error C1083: Cannot open precompiled header file: 'precompiled.pch': Permission denied
        tools.replace_in_file(os.path.join(self._source_subfolder, 'CMakeLists.txt'),
                              "if (MSVC)\n    # default for all sources is to use precompiled header",
                              "if (MSVC_DISABLED)\n    # default for all sources is to use precompiled header")

        # fix PDB location
        tools.replace_in_file(os.path.join(self._source_subfolder, 'CMakeLists.txt'),
                              'install (FILES ${CMAKE_CURRENT_BINARY_DIR}/bin/libzmq',
                              'install (FILES ${CMAKE_BINARY_DIR}/bin/libzmq')

        tools.replace_in_file(os.path.join(self._source_subfolder, 'builds', 'cmake', 'platform.hpp.in'),
                              'HAVE_LIBSODIUM', 'ZMQ_USE_LIBSODIUM')

    def build(self):
        if self.settings.compiler == 'Visual Studio':  # remove after conan 1.9.0
            with tools.vcvars(self.settings, force=True, filter_known_paths=False):
                cmake = self._configure_cmake()
                cmake.build()
        else:
            cmake = self._configure_cmake()
            cmake.build()

    def package(self):
        if self.settings.compiler == 'Visual Studio':  # remove after conan 1.9.0
            with tools.vcvars(self.settings, force=True, filter_known_paths=False):
                cmake = self._configure_cmake()
                cmake.install()
        else:
            cmake = self._configure_cmake()
            cmake.install()
        self.copy('FindZeroMQ.cmake')  # for cppzmq
        self.copy('Findlibzmq.cmake')  # for czmq
        self.copy(pattern="COPYING", src=self._source_subfolder, dst='licenses')
        if self.options.shared:
            exts = ['*.a']
        else:
            exts = ['*.dll', '*.so*', '*.dylib*']
        for root, _, filenames in os.walk(self.package_folder):
            for ext in exts:
                for filename in fnmatch.filter(filenames, ext):
                    os.unlink(os.path.join(root, filename))

    def package_info(self):
        if self.settings.compiler == 'Visual Studio':
            version = '_'.join(self.version.split('.'))
            if self.settings.build_type == 'Debug':
                runtime = '-gd' if self.options.shared else '-sgd'
            else:
                runtime = '' if self.options.shared else '-s'
            library_name = 'libzmq-mt%s-%s.lib' % (runtime, version)
            if not os.path.isfile(os.path.join(self.package_folder, 'lib', library_name)):
                # unfortunately Visual Studio and Ninja generators produce different file names
                toolset = {'12': 'v120',
                           '14': 'v140',
                           '15': 'v141'}.get(str(self.settings.compiler.version))
                library_name = 'libzmq-%s-mt%s-%s.lib' % (toolset, runtime, version)
            self.cpp_info.libs = [library_name, 'ws2_32', 'Iphlpapi']
        else:
            self.cpp_info.libs = ['zmq']
        if self.settings.os == "Linux":
            self.cpp_info.libs.extend(['pthread', 'rt', 'm'])
        if not self.options.shared:
            # zmq has C API, but requires C++ libraries to be lined
            if str(self.settings.compiler) in ['clang', 'gcc', 'apple-clang']:
                if str(self.settings.compiler.libcxx) in ['libstdc++', 'libstdc++11']:
                    self.cpp_info.libs.append('stdc++')
                elif str(self.settings.compiler.libcxx) == 'libc++':
                    self.cpp_info.libs.append('c++')
            self.cpp_info.defines.append('ZMQ_STATIC')
        # contains ZeroMQConfig.cmake
        self.cpp_info.builddirs.append(os.path.join(self.package_folder, 'share', 'cmake', 'ZeroMQ'))
