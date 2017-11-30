#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, AutoToolsBuildEnvironment, tools
import os


class ZMQConan(ConanFile):
    name = "zmq"
    version = "4.2.2"
    url = "https://github.com/bincrafters/conan-zmq"
    description = "ZeroMQ is a community of projects focused on decentralized messaging and computing"
    license = "https://github.com/someauthor/somelib/blob/master/LICENSES"
    exports_sources = ["LICENSE"]
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = "shared=False"

    def system_requirements(self):
        if self.settings.os == "Linux":
            if tools.os_info.linux_distro == "ubuntu" or tools.os_info.linux_distro == "debian":
                arch = ''
                if self.settings.arch == "x86" and tools.detected_architecture() == "x86_64":
                    arch = ':i386'
                installer = tools.SystemPackageTool()
                installer.install('pkg-config%s' % arch)

    def source(self):
        extracted_dir = "zeromq-%s" % self.version
        if self.settings.os == "Windows":
            archive_name = "%s.tar.gz" % extracted_dir
        else:
            archive_name = "%s.zip" % extracted_dir
        source_url = "https://github.com/zeromq/libzmq/releases/download/v%s/%s" % (self.version, archive_name)
        tools.get(source_url)
        os.rename(extracted_dir, "sources")

    def build(self):
        with tools.chdir("sources"):
            for name in ['autogen.sh', 'configure', 'version.sh', os.path.join('config', 'install-sh')]:
                os.chmod(name, os.stat(name).st_mode | 0o111)

            self.run('./autogen.sh')

            env_build = AutoToolsBuildEnvironment(self)
            args = ['--prefix=%s' % self.package_folder,
                    '--with-pic',
                    '--without-docs']
            if self.options.shared:
                args.extend(['--disable-static', '--enable-shared'])
            else:
                args.extend(['--enable-static', '--disable-shared'])
            if self.settings.build_type == 'Debug':
                args.append('--enable-debug')
            env_build.configure(args=args)
            env_build.make()
            env_build.make(args=['install'])

    def package(self):
        with tools.chdir("sources"):
            self.copy(pattern="LICENSE")

    def package_info(self):
        self.cpp_info.libs = ['zmq']
        if self.settings.os == "Linux":
            self.cpp_info.libs.append('pthread')
