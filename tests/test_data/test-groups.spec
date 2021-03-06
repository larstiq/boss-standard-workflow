%define name test-groups
%define version 0.1
%define release 1

Summary: Implement the BOSS standard workflow
Name: %{name}
Version: %{version}
Release: %{release}
Source0: testpattern.xml
License: GPLv2+
Group: Development/Languages
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Vendor <vendor@example.com>

%description
This is a test package for the update_patterns unit tests.

%prep

%build

%install
rm -rf %{buildroot}
install -d %{buildroot}/usr/share/patterns/
install %{SOURCE0} %{buildroot}/usr/share/patterns/

%files
%defattr(-,root,root)
/usr/share/patterns
