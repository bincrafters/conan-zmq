#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, tools, CMake
import os


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
    default_options = "shared=False", "fPIC=True", "encryption=libsodium"
    generators = ['cmake']

    def build_cmake(self):
        cmake = CMake(self, generator='Ninja')
        if self.settings.compiler != 'Visual Studio':
            cmake.definitions['CMAKE_POSITION_INDEPENDENT_CODE'] = self.options.fPIC
        cmake.definitions['ENABLE_CURVE'] = self.options.encryption is not None
        cmake.definitions['WITH_LIBSODIUM'] = self.options.encryption == "libsodium"
        cmake.configure(build_dir='build')
        cmake.build()
        cmake.install()

    def configure(self):
        if self.settings.compiler == 'Visual Studio':
            del self.options.fPIC

    def requirements(self):
        if self.options.encryption == 'libsodium':
            self.requires.add('libsodium/1.0.15@bincrafters/stable')

    def system_requirements(self):
        if self.settings.os == "Linux" and tools.os_info.is_linux:
            if tools.os_info.with_apt:
                arch = ''
                if self.settings.arch == "x86":
                    arch = ':i386'
                elif self.settings.arch == 'x86_64':
                    arch = ':amd64'
                installer = tools.SystemPackageTool()
                installer.install('pkg-config%s' % arch)

    def source(self):
        # see https://github.com/zeromq/libzmq/issues/2597
        extracted_dir = "libzmq-%s" % self.version
        archive_name = "v%s.tar.gz" % self.version
        source_url = "https://github.com/zeromq/libzmq/archive/%s" % archive_name
        tools.get(source_url)
        os.rename(extracted_dir, "sources")

        # disable precompiled headers
        # fatal error C1083: Cannot open precompiled header file: 'precompiled.pch': Permission denied
        tools.replace_in_file(os.path.join('sources', 'CMakeLists.txt'),
                              "if (MSVC)\n    # default for all sources is to use precompiled header",
                              "if (MSVC_DISABLED)\n    # default for all sources is to use precompiled header")

        # fix PDB location
        tools.replace_in_file(os.path.join('sources', 'CMakeLists.txt'),
                              'install (FILES ${CMAKE_CURRENT_BINARY_DIR}/bin/libzmq',
                              'install (FILES ${CMAKE_BINARY_DIR}/bin/libzmq')

        tools.replace_in_file(os.path.join('sources', 'builds', 'cmake', 'platform.hpp.in'),
                              'HAVE_LIBSODIUM', 'ZMQ_USE_LIBSODIUM')

    def build(self):
        if self.settings.compiler == 'Visual Studio':
            with tools.vcvars(self.settings, force=True, filter_known_paths=False):
                self.build_cmake()
        else:
            self.build_cmake()

    def package(self):
        self.copy('FindZeroMQ.cmake')  # for cppzmq
        self.copy('Findlibzmq.cmake')  # for czmq
        self.copy(pattern="COPYING", src='sources', dst='license')

    def package_info(self):
        if self.settings.compiler == 'Visual Studio':
            version = '_'.join(self.version.split('.'))
            if self.settings.build_type == 'Debug':
                runtime = '-gd' if self.options.shared else '-sgd'
            else:
                runtime = '' if self.options.shared else '-s'
            library_name = 'libzmq-mt%s-%s.lib' % (runtime, version)
            self.cpp_info.libs = [library_name, 'ws2_32', 'Iphlpapi']
        else:
            self.cpp_info.libs = ['zmq']
        if self.settings.os == "Linux":
            self.cpp_info.libs.extend(['pthread', 'rt', 'm'])
        if not self.options.shared:
            self.cpp_info.defines.append('ZMQ_STATIC')
        # contains ZeroMQConfig.cmake
        self.cpp_info.builddirs.append(os.path.join(self.package_folder, 'share', 'cmake', 'ZeroMQ'))
