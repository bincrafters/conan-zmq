# -*- coding: utf-8 -*-
import os
from conans import ConanFile, tools, CMake


class ZMQConan(ConanFile):
    name = "zmq"
    version = "4.2.5"
    url = "https://github.com/bincrafters/conan-zmq"
    homepage = "https://github.com/zeromq/libzmq"
    description = "ZeroMQ is a community of projects focused on decentralized messaging and computing"
    license = "LGPL-3.0"
    author = "Bincrafters <bincrafters@gmail.com>"
    topics = ("conan", "zmq", "libzmq", "message-queue", "asynchronous")
    exports = ["LICENSE.md"]
    exports_sources = ['FindZeroMQ.cmake', 'Findlibzmq.cmake', 'CMakeLists.txt']
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False], "encryption": [None, "libsodium", "tweetnacl"]}
    default_options = {'shared': False, 'fPIC': True, 'encryption': 'libsodium'}
    generators = ['cmake']
    _source_subfolder = "sources_subfolder"
    _build_subfolder = "build_subfolder"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def build_requirements(self):
        if not tools.which("ninja"):
            self.build_requires.add('ninja_installer/1.8.2@bincrafters/stable')

    def requirements(self):
        if self.options.encryption == 'libsodium':
            self.requires.add('libsodium/1.0.16@bincrafters/stable')

    def source(self):
        sha256 = "f33807105ce47f684c26751ce4e27a708a83ce120cbabbc614c8df21252b238c"
        tools.get("{}/archive/v{}.tar.gz".format(self.homepage, self.version), sha256=sha256)
        extracted_dir = "libzmq-%s" % self.version
        os.rename(extracted_dir, self._source_subfolder)

    def _patch(self):
        # disable precompiled headers
        # fatal error C1083: Cannot open precompiled header file: 'precompiled.pch': Permission denied
        tools.replace_in_file(os.path.join(self._source_subfolder, 'CMakeLists.txt'),
                              "if (MSVC)\n    # default for all sources is to use precompiled header",
                              "if (MSVC_DISABLED)\n    # default for all sources is to use precompiled header")
        # fix PDB location
        tools.replace_in_file(os.path.join(self._source_subfolder, 'CMakeLists.txt'),
                              'install (FILES ${CMAKE_CURRENT_BINARY_DIR}/bin/libzmq',
                              'install (FILES ${CMAKE_BINARY_DIR}/bin/libzmq')

    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.definitions['ENABLE_CURVE'] = self.options.encryption is not None
        cmake.definitions['WITH_LIBSODIUM'] = self.options.encryption == "libsodium"
        cmake.definitions['ZMQ_BUILD_TESTS'] = False
        cmake.definitions['WITH_PERF_TOOL'] = False
        cmake.definitions['BUILD_SHARED'] = self.options.shared
        cmake.definitions['BUILD_STATIC'] = not self.options.shared
        cmake.configure(build_dir=self._build_subfolder)
        return cmake

    def build(self):
        self._patch()
        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        self.copy('FindZeroMQ.cmake')  # for cppzmq
        self.copy('Findlibzmq.cmake')  # for czmq
        self.copy(pattern="COPYING", src=self._source_subfolder, dst='licenses')
        cmake = self._configure_cmake()
        cmake.install()

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
