#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, CMake, tools, RunEnvironment
import os


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake"

    def build(self):
        if self.settings.compiler == 'Visual Studio':  # remove after conan 1.9.0
            with tools.vcvars(self.settings, force=True, filter_known_paths=False):
                self.build_cmake()
        else:
            self.build_cmake()

    def build_cmake(self):
        cmake = CMake(self)
        cmake.definitions['WITH_LIBSODIUM'] = self.options['zmq'].encryption == 'libsodium'
        cmake.configure()
        cmake.build()

    def test(self):
        if not tools.cross_building(self.settings):
            bin_path = os.path.join("bin", "test_package")
            self.run(bin_path, run_environment=True)
