%define rcver %{nil}
%define snapshot %{nil}

%global _hardened_build 1

Summary: WPA/WPA2/IEEE 802.1X Supplicant
Name: wpa_supplicant
Epoch: 1
Version: 2.10
Release: 1%{?dist}
License: BSD
Group: System Environment/Base
Source0: http://w1.fi/releases/%{name}-%{version}%{rcver}%{snapshot}.tar.gz
Source1: build-config
Source2: %{name}.conf
Source3: %{name}.service
Source4: %{name}.sysconfig
Source6: %{name}.logrotate

%define build_gui 0

# distro specific customization and not suitable for upstream,
# works around busted drivers
Patch0: wpa_supplicant-assoc-timeout.patch
# ensures that debug output gets flushed immediately to help diagnose driver
# bugs, not suitable for upstream
Patch1: wpa_supplicant-flush-debug-output.patch
# quiet an annoying and frequent syslog message
Patch3: wpa_supplicant-quiet-scan-results-message.patch
# distro specific customization for Qt4 build tools, not suitable for upstream
Patch5: rh1542234-remove-wpa_gui.patch
Patch6: wpa_supplicant-gui-qt4.patch

URL: http://w1.fi/wpa_supplicant/

%if %{build_gui}
BuildRequires: qt-devel >= 4.0
%endif
BuildRequires: openssl-devel
BuildRequires: readline-devel
BuildRequires: dbus-devel
BuildRequires: libnl3-devel
BuildRequires: systemd-units
BuildRequires: docbook-utils
Requires(post): systemd-sysv
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
# libeap used to be built from wpa_supplicant with some fairly horrible
# hackery, solely for use by WiMAX. We dropped all WiMAX support around
# F21. This is here so people don't wind up with obsolete libeap packages
# lying around. If it's ever resurrected for any reason, this needs
# dropping.
Obsoletes: libeap < %{epoch}:%{version}-%{release}
Obsoletes: libeap-devel < %{epoch}:%{version}-%{release}

%description
wpa_supplicant is a WPA Supplicant for Linux, BSD and Windows with support
for WPA and WPA2 (IEEE 802.11i / RSN). Supplicant is the IEEE 802.1X/WPA
component that is used in the client stations. It implements key negotiation
with a WPA Authenticator and it controls the roaming and IEEE 802.11
authentication/association of the wlan driver.

%if %{build_gui}

%package gui
Summary: Graphical User Interface for %{name}
Group: Applications/System

%description gui
Graphical User Interface for wpa_supplicant written using QT

%endif

%prep
%autosetup -p1 -n %{name}-%{version}%{rcver}%{snapshot}

%build
pushd wpa_supplicant
  cp %{SOURCE1} .config
  CFLAGS="${CFLAGS:-%optflags} -fPIE -DPIE" ; export CFLAGS ;
  CXXFLAGS="${CXXFLAGS:-%optflags} -fPIE -DPIE" ; export CXXFLAGS ;
  LDFLAGS="${LDFLAGS:-%optflags} -pie -Wl,-z,now" ; export LDFLAGS ;
  # yes, BINDIR=_sbindir
  BINDIR="%{_sbindir}" ; export BINDIR ;
  LIBDIR="%{_libdir}" ; export LIBDIR ;
  make %{_smp_mflags}
%if %{build_gui}
  QTDIR=%{_libdir}/qt4 make wpa_gui-qt4 %{_smp_mflags} QMAKE='%{qmake_qt4}' LRELEASE='%{_qt4_bindir}/lrelease'
%endif
  make eapol_test
popd

pushd wpa_supplicant/doc/docbook
  make man
popd

%install
# init scripts
install -D -m 0644 %{SOURCE3} %{buildroot}/%{_unitdir}/%{name}.service
install -D -m 0644 %{SOURCE4} %{buildroot}/%{_sysconfdir}/sysconfig/%{name}
install -D -m 0644 %{SOURCE6} %{buildroot}/%{_sysconfdir}/logrotate.d/%{name}

# config
install -D -m 0600 %{SOURCE2} %{buildroot}/%{_sysconfdir}/%{name}/%{name}.conf

# binary
install -d %{buildroot}/%{_sbindir}
install -m 0755 %{name}/wpa_passphrase %{buildroot}/%{_sbindir}
install -m 0755 %{name}/wpa_cli %{buildroot}/%{_sbindir}
install -m 0755 %{name}/wpa_supplicant %{buildroot}/%{_sbindir}
install -m 0755 %{name}/eapol_test %{buildroot}/%{_sbindir}
install -D -m 0644 %{name}/dbus/dbus-wpa_supplicant.conf %{buildroot}/%{_sysconfdir}/dbus-1/system.d/wpa_supplicant.conf
install -D -m 0644 %{name}/dbus/fi.w1.wpa_supplicant1.service %{buildroot}/%{_datadir}/dbus-1/system-services/fi.w1.wpa_supplicant1.service

%if %{build_gui}
# gui
install -d %{buildroot}/%{_bindir}
install -m 0755 %{name}/wpa_gui-qt4/wpa_gui %{buildroot}/%{_bindir}
%else
rm -f %{name}/doc/docbook/wpa_gui.8
%endif

rm -f %{name}/doc/docbook/wpa_priv.8

# man pages
install -d %{buildroot}%{_mandir}/man{5,8}
install -m 0644 %{name}/doc/docbook/*.8 %{buildroot}%{_mandir}/man8
install -m 0644 %{name}/doc/docbook/*.5 %{buildroot}%{_mandir}/man5

# some cleanup in docs and examples
rm -f  %{name}/doc/.cvsignore
rm -rf %{name}/doc/docbook
chmod -R 0644 %{name}/examples/*.py

%post
%systemd_post wpa_supplicant.service

%preun
%systemd_preun wpa_supplicant.service

%triggerun -- wpa_supplicant < 0.7.3-10
# Save the current service runlevel info
# User must manually run systemd-sysv-convert --apply wpa_supplicant
# to migrate them to systemd targets
/usr/bin/systemd-sysv-convert --save wpa_supplicant >/dev/null 2>&1 ||:

# Run these because the SysV package being removed won't do them
/sbin/chkconfig --del wpa_supplicant >/dev/null 2>&1 || :
/bin/systemctl try-restart wpa_supplicant.service >/dev/null 2>&1 || :


%files
%license COPYING
%doc %{name}/ChangeLog README %{name}/eap_testing.txt %{name}/todo.txt %{name}/wpa_supplicant.conf %{name}/examples
%config(noreplace) %{_sysconfdir}/%{name}/%{name}.conf
%config(noreplace) %{_sysconfdir}/sysconfig/%{name}
%config(noreplace) %{_sysconfdir}/logrotate.d/%{name}
%{_unitdir}/%{name}.service
%{_sysconfdir}/dbus-1/system.d/%{name}.conf
%{_datadir}/dbus-1/system-services/fi.w1.wpa_supplicant1.service
%{_sbindir}/wpa_passphrase
%{_sbindir}/wpa_supplicant
%{_sbindir}/wpa_cli
%{_sbindir}/eapol_test
%dir %{_sysconfdir}/%{name}
%{_mandir}/man8/*
%{_mandir}/man5/*

%if %{build_gui}
%files gui
%{_bindir}/wpa_gui
%endif

%changelog
* Thu Jan  20 2022 Davide Caratti <dcaratti@redhat.com> - 1:2.10-1
- Update to version 2.10 (rh #2042104)

* Thu Dec  9 2021 Davide Caratti <dcaratti@redhat.com> - 1:2.9-6.20211112gitc8b94bc7b347
- restore WEP functionality (rh #2028839)

* Fri Nov 12 2021 Davide Caratti <dcaratti@redhat.com> - 1:2.9-5.20211112gitc8b94bc7b347
- Update to latest upstream tree to include support for H2E
  Resolves: rhbz#2007333

* Fri Mar  5 2021 Davide Caratti <dcaratti@redhat.com> - 1:2.9-5
- P2P: Fix a corner case in peer addition based on PD Request (CVE-2021-27803)
- Fix buffer overflow when processing P2P group information (CVE-2021-0326)

* Fri Jan 15 2021 Davide Caratti <dcaratti@redhat.com> - 1:2.9-4
- enable WPA-EAP-SUITE-B-192 (rh #1916394)

* Tue Oct 27 2020 Davide Caratti <dcaratti@redhat.com> - 1:2.9-3
- fix p2p_listen unexpectedly stopped after 5 seconds (rh #1693684)
- allow changing 'bridge' via D-Bus (rh #1888050)
- expose OWE configurability via D-Bus (rh #1888718)

* Tue Oct 29 2019 Davide Caratti <dcaratti@redhat.com> - 1:2.9-2
- Fix AP mode PMF disconnection protection bypass (CVE-2019-16275)
- Fix NULL dereference in d-bus handler when P2P control interface is removed (rh #1752780)
- enable WIFI_DISPLAY (rh #1755941)

* Mon Oct 21 2019 Davide Caratti <dcaratti@redhat.com> - 1:2.9-1
- Update to 2.9 upstream release
- Enable OWE, SAE and DPP (rh #1730169)

* Thu Feb 07 2019 Davide Caratti <dcaratti@redhat.com> - 1:2.7-2
- Enable CI gating (rh #1682340) and add a basic selftest

* Thu Feb 07 2019 Davide Caratti <dcaratti@redhat.com> - 1:2.7-1
- Update to 2.7 upstream release

* Mon Sep 10 2018 Davide Caratti <dcaratti@redhat.com> - 1:2.6-17
- Fix duplicate Reassociation Request frame dropping (detected by Covscan)

* Fri Aug 31 2018 Davide Caratti <dcaratti@redhat.com> - 1:2.6-16
- Ignore unauthenticated encrypted EAPOL-Key data (CVE-2018-14526)

* Thu Jul 12 2018 Davide Caratti <dcaratti@redhat.com> - 1:2.6-15
- Disable build of wpa_gui (rh #1542234)
- Fix build issue with latest kernel headers (rh #1582604)
- Disable WEXT (rh #1537143)
- Fix memory leak when macsec MKA/PSK is used (rh #1582511)
- Fix authentication failure when the MAC is updated externally (rh #1582508)
- Let the kernel discard EAPOL if packet type is PACKET_OTHERHOST (rh #1582501)

* Fri Feb 09 2018 Fedora Release Engineering <releng@fedoraproject.org> - 1:2.6-14
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Tue Jan 16 2018 Davide Caratti <dcaratti@redhat.com> - 1:2.6-13
- Don't restart wpa_supplicant.service on package upgrade (rh#1535233)

* Wed Nov  1 2017 Jiří Klimeš <blueowl@centrum.cz> - 1:2.6-12
- Fix crash when using MACsec without loaded macsec.ko (rh #1497640)
- Enable Fast BSS Transition for station mode (rh #1372928)

* Mon Oct 16 2017 Lubomir Rintel <lkundrak@v3.sk> - 1:2.6-11
- hostapd: Avoid key reinstallation in FT handshake (CVE-2017-13082)
- Fix PTK rekeying to generate a new ANonce
- Prevent reinstallation of an already in-use group key and extend
  protection of GTK/IGTK reinstallation of WNM-Sleep Mode cases
  (CVE-2017-13078, CVE-2017-13079, CVE-2017-13080, CVE-2017-13081,
  CVE-2017-13087, CVE-2017-13088)
- Prevent installation of an all-zero TK
- TDLS: Reject TPK-TK reconfiguration
- WNM: Ignore WNM-Sleep Mode Response without pending request
- FT: Do not allow multiple Reassociation Response frames

* Thu Aug 03 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1:2.6-10
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1:2.6-9
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Mon Jul 17 2017 Beniamino Galvani <bgalvani@redhat.com> - 1:2.6-8
- OpenSSL: use system ciphers by default (rh #1462262)
- OpenSSL: fix private key password callback (rh #1465138)

* Wed May 17 2017 Beniamino Galvani <bgalvani@redhat.com> - 1:2.6-7
- nl80211: Fix race condition in detecting MAC change (rh #1451834)

* Tue Apr 11 2017 Davide Caratti <dcaratti@redhat.com> - 1:2.6-6
- Fix use-after-free when macsec secure channels are deleted
- Fix segmentation fault in case macsec module is not loaded (rh#1428937)

* Mon Mar 13 2017 Thomas Haller <thaller@redhat.com> - 1:2.6-5
- Enable IEEE 802.11w (management frame protection, PMF) (rh#909499)

* Thu Mar  2 2017 Davide Caratti <dcaratti@redhat.com> - 1:2.6-4
- Backport support for IEEE 802.1AE (macsec)

* Sat Feb 11 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1:2.6-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Fri Jan 27 2017 Jiří Klimeš <blueowl@centrum.cz> - 1:2.6-2
- Enable Wi-Fi Display support for Miracast (rh #1395682)

* Tue Nov 22 2016 Lubomir Rintel <lkundrak@v3.sk> - 1:2.6-1
- Update to version 2.6

* Fri Feb 05 2016 Fedora Release Engineering <releng@fedoraproject.org> - 1:2.5-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Mon Nov 16 2015 Lubomir Rintel <lkundrak@v3.sk> - 1:2.5-4
- Really synchronize the service file with upstream

* Tue Nov 03 2015 Lukáš Nykrýn <lnykryn@redhat.com> - 1:2.5-3
- Scriptlets replaced with new systemd macros (rh #850369)

* Sat Oct 31 2015 Lubomir Rintel <lkundrak@v3.sk> - 1:2.5-2
- Enable syslog by default
- Drop writing a pid and log file

* Tue Oct 27 2015 Lubomir Rintel <lkundrak@v3.sk> - 1:2.5-1
- Update to version 2.5

* Fri Oct 23 2015 Lubomir Rintel <lkundrak@v3.sk> - 1:2.4-6
- Fix the D-Bus policy

* Sat Oct  3 2015 Ville Skyttä <ville.skytta@iki.fi> - 1:2.4-5
- Don't order service after syslog.target (rh #1055197)
- Mark COPYING as %%license

* Wed Jul 15 2015 Jiří Klimeš <jklimes@redhat.com> - 1:2.4-4
- Fix for NDEF record payload length checking (rh #1241907)

* Tue Jun 16 2015 Jiří Klimeš <jklimes@redhat.com> - 1:2.4-3
- Fix a crash if P2P management interface is used (rh #1231973)

* Thu Apr 23 2015 Dan Williams <dcbw@redhat.com> - 1:2.4-2
- Remove obsolete wpa_supplicant-openssl-more-algs.patch

* Thu Apr 23 2015 Adam Williamson <awilliam@redhat.com> - 1:2.4-1
- new release 2.4
- add some info on a couple of patches
- drop some patches merged or superseded upstream
- rediff other patches
- drop libeap hackery (we dropped the kernel drivers anyhow)
- backport fix for CVE-2015-1863

* Sat Nov 01 2014 Orion Poplawski <orion@cora.nwra.com> - 1:2.3-2
- Do not install wpa_supplicant.service as executable (bug #803980)

* Thu Oct 30 2014 Lubomir Rintel <lkundrak@v3.sk> - 1:2.3-1
- Update to 2.3

* Wed Oct 22 2014 Dan Williams <dcbw@redhat.com> - 1:2.0-12
- Use os_exec() for action script execution (CVE-2014-3686)

* Thu Aug 21 2014 Kevin Fenzi <kevin@scrye.com> - 1:2.0-11
- Rebuild for rpm bug 1131960

* Mon Aug 18 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:2.0-10
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Sun Jun 08 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:2.0-9
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Mon Nov 18 2013 Dan Williams <dcbw@redhat.com> - 1:2.0-8
- Don't disconnect when PMKSA cache gets too large (rh #1016707)

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:2.0-7
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Wed Jul 10 2013 Dan Williams <dcbw@redhat.com> - 1:2.0-6
- Enable full RELRO/PIE/PIC for wpa_supplicant and libeap
- Fix changelog dates

* Wed Jul 10 2013 Dan Williams <dcbw@redhat.com> - 1:2.0-5
- Build and package eapol_test (rh #638218)

* Wed Jul 10 2013 Dan Williams <dcbw@redhat.com> - 1:2.0-4
- Disable WiMAX libeap hack for RHEL

* Wed May 15 2013 Dan Williams <dcbw@redhat.com> - 1:2.0-3
- Enable HT (802.11n) for AP mode

* Tue May  7 2013 Dan Williams <dcbw@redhat.com> - 1:2.0-2
- Use hardened build macros and ensure they apply to libeap too

* Mon May  6 2013 Dan Williams <dcbw@redhat.com> - 1:2.0-1
- Update to 2.0
- Be less aggressive when roaming due to signal strength changes (rh #837402)

* Mon Apr  1 2013 Dan Williams <dcbw@redhat.com> - 1:1.1-1
- Update to 1.1
- Be less aggressive when roaming due to signal strength changes

* Fri Feb 15 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:1.0-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Sun Jan 20 2013 Dan Horák <dan@danny.cz> - 1:1.0-3
- rebuilt again for fixed soname in libnl3

* Sun Jan 20 2013 Kalev Lember <kalevlember@gmail.com> - 1:1.0-2
- Rebuilt for libnl3

* Wed Aug 29 2012 Dan Williams <dcbw@redhat.com> - 1:1.0-1
- Enable lightweight AP mode support
- Enable P2P (WiFi Direct) support
- Enable RSN IBSS/AdHoc support

* Sun Jul 22 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:1.0-0.5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Tue May  1 2012 Dan Williams <dcbw@redhat.com> - 1:1.0-0.4
- Update to wpa_supplicant 1.0-rc3
- Fix systemd target dependencies (rh #815091)

* Fri Mar  2 2012 Dan Williams <dcbw@redhat.com> - 1:1.0-0.3
- Update to latest 1.0 git snapshot
- Rebuild against libnl3

* Thu Feb  2 2012 Dan Williams <dcbw@redhat.com> - 1:1.0-0.2
- Fix driver fallback for non nl80211-based drivers (rh #783712)

* Tue Jan 10 2012 Dan Williams <dcbw@redhat.com> - 1:1.0-0.1
- Update to 1.0-rc1 + git

* Fri Sep  9 2011 Tom Callaway <spot@fedoraproject.org> - 1:0.7.3-11
- add missing systemd scriptlets

* Thu Sep  8 2011 Tom Callaway <spot@fedoraproject.org> - 1:0.7.3-10
- convert to systemd

* Wed Jul 27 2011 Dan Williams <dcbw@redhat.com> - 1:0.7.3-9
- Fix various crashes with D-Bus interface (rh #678625) (rh #725517)

* Tue May  3 2011 Dan Williams <dcbw@redhat.com> - 1:0.7.3-8
- Don't crash when trying to access invalid properties via D-Bus (rh #678625)

* Mon May  2 2011 Dan Williams <dcbw@redhat.com> - 1:0.7.3-7
- Make examples read-only to avoid erroneous python dependency (rh #687952)

* Tue Apr 19 2011 Bill Nottingham <notting@redhat.com> - 1:0.7.3-6
- Fix EAP patch to only apply when building libeap

* Fri Mar 25 2011 Bill Nottingham <notting@redhat.com> - 1:0.7.3-5
- Add libeap/libeap-devel subpackge for WiMAX usage

* Mon Feb 07 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:0.7.3-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Tue Jan 11 2011 Dan Williams <dcbw@redhat.com> - 1:0.7.3-3
- Enable EAP-TNC (rh #659038)

* Wed Dec 15 2010 Dan Williams <dcbw@redhat.com> - 1:0.7.3-2
- Enable the bgscan_simple plugin

* Wed Dec  8 2010 Dan Williams <dcbw@redhat.com> - 1:0.7.3-1
- Update to 0.7.3
- Drop upstreamed and backported patches
- Drop support for Qt3

* Thu Oct  7 2010 Peter Lemenkov <lemenkov@gmail.com> - 1:0.6.8-11
- Added comments to some patches (see rhbz #226544#c17)
- Shortened %%install section a bit

* Thu May 13 2010 Dan Williams <dcbw@redhat.com> - 1:0.6.8-10
- Remove prereq on chkconfig
- Build GUI with qt4 for rawhide (rh #537105)

* Thu May  6 2010 Dan Williams <dcbw@redhat.com> - 1:0.6.8-9
- Fix crash when interfaces are removed (like suspend/resume) (rh #589507)

* Wed Jan  6 2010 Dan Williams <dcbw@redhat.com> - 1:0.6.8-8
- Fix handling of newer PKCS#12 files (rh #541924)

* Sun Nov 29 2009 Dan Williams <dcbw@redhat.com> - 1:0.6.8-7
- Fix supplicant initscript return value (rh #521807)
- Fix race when connecting to WPA-Enterprise/802.1x-enabled access points (rh #508509)
- Don't double-scan when attempting to associate

* Fri Aug 21 2009 Tomas Mraz <tmraz@redhat.com> - 1:0.6.8-6
- rebuilt with new openssl

* Mon Jul 27 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:0.6.8-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Wed May 13 2009 Dan Williams <dcbw@redhat.com> - 1:0.6.8-4
- Let D-Bus clients know when the supplicant is scanning

* Tue May 12 2009 Dan Williams <dcbw@redhat.com> - 1:0.6.8-3
- Ensure the supplicant starts and ends with clean driver state
- Handle driver disconnect spammage by forcibly clearing SSID
- Don't switch access points unless the current association is dire (rh #493745)

* Tue May 12 2009 Dan Williams <dcbw@redhat.com> - 1:0.6.8-2
- Avoid creating bogus Ad-Hoc networks when forcing the driver to disconnect (rh #497771)

* Mon Mar  9 2009 Dan Williams <dcbw@redhat.com> - 1:0.6.8-1
- Update to latest upstream release

* Wed Feb 25 2009 Colin Walters <walters@verbum.org> - 1:0.6.7-4
- Add patch from upstream to suppress unrequested replies, this
  quiets a dbus warning.

* Fri Feb  6 2009 Dan Williams <dcbw@redhat.com> - 1:0.6.7-3
- Fix scan result retrieval in very dense wifi environments

* Fri Feb  6 2009 Dan Williams <dcbw@redhat.com> - 1:0.6.7-2
- Ensure that drivers don't retry association when they aren't supposed to

* Fri Jan 30 2009 Dan Williams <dcbw@redhat.com> - 1:0.6.7-1
- Fix PEAP connections to Windows Server 2008 authenticators (rh #465022)
- Stop supplicant on uninstall (rh #447843)
- Suppress scan results message in logs (rh #466601)

* Sun Jan 18 2009 Tomas Mraz <tmraz@redhat.com> - 1:0.6.4-3
- rebuild with new openssl

* Wed Oct 15 2008 Dan Williams <dcbw@redhat.com> - 1:0.6.4-2
- Handle encryption keys correctly when switching 802.11 modes (rh #459399)
- Better scanning behavior on resume from suspend/hibernate
- Better interaction with newer kernels and drivers

* Wed Aug 27 2008 Dan Williams <dcbw@redhat.com> - 1:0.6.4-1
- Update to 0.6.4
- Remove 'hostap', 'madwifi', and 'prism54' drivers; use standard 'wext' instead
- Drop upstreamed patches

* Tue Jun 10 2008 Dan Williams <dcbw@redhat.com> - 1:0.6.3-6
- Fix 802.11a frequency bug
- Always schedule specific SSID scans to help find hidden APs
- Properly switch between modes on mac80211 drivers
- Give adhoc connections more time to assocate

* Mon Mar 10 2008 Christopher Aillon <caillon@redhat.com> - 1:0.6.3-5
- BuildRequires qt3-devel

* Sat Mar  8 2008 Dan Williams <dcbw@redhat.com> - 1:0.6.3-4
- Fix log file path in service config file

* Thu Mar  6 2008 Dan Williams <dcbw@redhat.com> - 1:0.6.3-3
- Don't start the supplicant by default when installed (rh #436380)

* Tue Mar  4 2008 Dan Williams <dcbw@redhat.com> - 1:0.6.3-2
- Fix a potential use-after-free in the D-Bus byte array demarshalling code

* Mon Mar  3 2008 Dan Williams <dcbw@redhat.com> - 1:0.6.3-1
- Update to latest development release; remove upstreamed patches

* Fri Feb 22 2008 Dan Williams <dcbw@redhat.com> 1:0.5.7-23
- Fix gcc 4.3 rebuild issues

* Mon Feb 18 2008 Fedora Release Engineering <rel-eng@fedoraproject.org> - 1:0.5.7-22
- Autorebuild for GCC 4.3

* Tue Dec 25 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-21
- Backport 'frequency' option for Ad-Hoc network configs

* Mon Dec 24 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-20
- Fix LSB initscript header to ensure 'messagebus' is started first (rh #244029)

* Thu Dec  6 2007 Dan Williams <dcbw@redhat.com> - 1:0.5.7-19
- Fix two leaks when signalling state and scan results (rh #408141)
- Add logrotate config file (rh #404181)
- Add new LSB initscript header to initscript with correct deps (rh #244029)
- Move other runtime arguments to /etc/sysconfig/wpa_supplicant
- Start after messagebus service (rh #385191)
- Fix initscript 'condrestart' command (rh #217281)

* Tue Dec  4 2007 Matthias Clasen <mclasen@redhat.com> - 1:0.5.7-18
- Rebuild against new openssl

* Tue Dec  4 2007 Ville Skyttä <ville.skytta at iki.fi> - 1:0.5.7-17
- Group: Application/System -> Applications/System in -gui.

* Tue Nov 13 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-16
- Add IW_ENCODE_TEMP patch for airo driver and Dynamic WEP
- Fix error in wpa_supplicant-0.5.7-ignore-dup-ca-cert-addition.patch that
    caused the last error to not be printed
- Fix wpa_supplicant-0.5.7-ignore-dup-ca-cert-addition.patch to ignore
    duplicate cert additions for all certs and keys
- Change license to BSD due to linkage against OpenSSL since there is no
    OpenSSL exception in the GPLv2 license text that upstream ships

* Sun Oct 28 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-15
- Fix Dynamic WEP associations with mac80211-based drivers

* Sun Oct 28 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-14
- Don't error an association on duplicate CA cert additions

* Wed Oct 24 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-13
- Correctly set the length of blobs added via the D-Bus interface

* Wed Oct 24 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-12
- Fix conversion of byte arrays to strings by ensuring the buffer is NULL
    terminated after conversion

* Sat Oct 20 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-11
- Add BLOB support to the D-Bus interface
- Fix D-Bus interface permissions so that only root can use the wpa_supplicant
    D-Bus interface

* Tue Oct  9 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-10
- Don't segfault with dbus control interface enabled and invalid network
    interface (rh #310531)

* Tue Sep 25 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-9
- Always allow explicit wireless scans triggered from a control interface

* Thu Sep 20 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-8
- Change system bus activation file name to work around D-Bus bug that fails
    to launch services unless their .service file is named the same as the
    service itself

* Fri Aug 24 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-7
- Make SIGUSR1 change debug level on-the-fly; useful in combination with
    the -f switch to log output to /var/log/wpa_supplicant.log
- Stop stripping binaries on install so we get debuginfo packages
- Remove service start requirement for interfaces & devices from sysconfig file,
    since wpa_supplicant's D-Bus interface is now turned on

* Fri Aug 17 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-6
- Fix compilation with RPM_OPT_FLAGS (rh #249951)
- Make debug output to logfile a runtime option

* Fri Aug 17 2007 Christopher Aillon <caillon@redhat.com> - 0.5.7-5
- Update the license tag

* Tue Jun 19 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-4
- Fix initscripts to use -Dwext by default, be more verbose on startup
    (rh #244511)

* Mon Jun  4 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-3
- Fix buffer overflow by removing syslog patch (#rh242455)

* Mon Apr  9 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-2
- Add patch to send output to syslog

* Thu Mar 15 2007 Dan Williams <dcbw@redhat.com> - 0.5.7-1
- Update to 0.5.7 stable release

* Fri Oct 27 2006 Dan Williams <dcbw@redhat.com> - 0.4.9-1
- Update to 0.4.9 for WE-21 fixes, remove upstreamed patches
- Don't package doc/ because they aren't actually wpa_supplicant user documentation,
    and becuase it pulls in perl

* Wed Jul 12 2006 Jesse Keating <jkeating@redhat.com> - 0.4.8-10.1
- rebuild

* Thu Apr 27 2006 Dan Williams <dcbw@redhat.com> - 0.4.8-10
- Add fix for madwifi and WEP (wpa_supplicant/hostap bud #140) (#rh190075#)
- Fix up madwifi-ng private ioctl()s for r1331 and later
- Update madwifi headers to r1475

* Tue Apr 25 2006 Dan Williams <dcbw@redhat.com> - 0.4.8-9
- Enable Wired driver, PKCS12, and Smartcard options (#rh189805#)

* Tue Apr 11 2006 Dan Williams <dcbw@redhat.com> - 0.4.8-8
- Fix control interface key obfuscation a bit

* Sun Apr  2 2006 Dan Williams <dcbw@redhat.com> - 0.4.8-7
- Work around older & incorrect drivers that return null-terminated SSIDs

* Mon Mar 27 2006 Dan Williams <dcbw@redhat.com> - 0.4.8-6
- Add patch to make orinoco happy with WEP keys
- Enable Prism54-specific driver
- Disable ipw-specific driver; ipw2x00 should be using WEXT instead

* Fri Mar  3 2006 Dan Williams <dcbw@redhat.com> - 0.4.8-5
- Increase association timeout, mainly for drivers that don't
	fully support WPA ioctls yet

* Fri Mar  3 2006 Dan Williams <dcbw@redhat.com> - 0.4.8-4
- Add additional BuildRequires #rh181914#
- Add prereq on chkconfig #rh182905# #rh182906#
- Own /var/run/wpa_supplicant and /etc/wpa_supplicant #rh183696#

* Wed Mar  1 2006 Dan Williams <dcbw@redhat.com> - 0.4.8-3
- Install wpa_passphrase too #rh183480#

* Mon Feb 27 2006 Dan Williams <dcbw@redhat.com> - 0.4.8-2
- Don't expose private data on the control interface unless requested

* Fri Feb 24 2006 Dan Williams <dcbw@redhat.com> - 0.4.8-1
- Downgrade to 0.4.8 stable release rather than a dev release

* Sun Feb 12 2006 Dan Williams <dcbw@redhat.com> - 0.5.1-3
- Documentation cleanup (Terje Rosten <terje.rosten@ntnu.no>)

* Sun Feb 12 2006 Dan Williams <dcbw@redhat.com> - 0.5.1-2
- Move initscript to /etc/rc.d/init.d

* Fri Feb 10 2006 Jesse Keating <jkeating@redhat.com> - 0.5.1-1.2
- bump again for double-long bug on ppc(64)

* Tue Feb 07 2006 Jesse Keating <jkeating@redhat.com> - 0.5.1-1.1
- rebuilt for new gcc4.1 snapshot and glibc changes

* Sun Feb  5 2006 Dan Williams <dcbw@redhat.com> 0.5.1-1
- Update to 0.5.1
- Add WE auth fallback to actually work with older drivers

* Thu Jan 26 2006 Dan Williams <dcbw@redhat.com> 0.4.7-2
- Bring package into Fedora Core
- Add ap_scan control interface patch
- Enable madwifi-ng driver

* Sun Jan 15 2006 Douglas E. Warner <silfreed@silfreed.net> 0.4.7-1
- upgrade to 0.4.7
- added package w/ wpa_gui in it

* Mon Nov 14 2005 Douglas E. Warner <silfreed@silfreed.net> 0.4.6-1
- upgrade to 0.4.6
- adding ctrl interface changes recommended 
  by Hugo Paredes <hugo.paredes@e-know.org>

* Sun Oct  9 2005 Douglas E. Warner <silfreed@silfreed.net> 0.4.5-1
- upgrade to 0.4.5
- updated config file wpa_supplicant is built with
  especially, the ipw2100 driver changed to just ipw
  and enabled a bunch more EAP
- disabled dist tag

* Thu Jun 30 2005 Douglas E. Warner <silfreed@silfreed.net> 0.4.2-3
- fix typo in init script

* Thu Jun 30 2005 Douglas E. Warner <silfreed@silfreed.net> 0.4.2-2
- fixing init script using fedora-extras' template
- removing chkconfig default startup

* Tue Jun 21 2005 Douglas E. Warner <silfreed@silfreed.net> 0.4.2-1
- upgrade to 0.4.2
- new sample conf file that will use any unrestricted AP
- make sysconfig config entry
- new BuildRoot for Fedora Extras
- adding dist tag to Release

* Fri May 06 2005 Douglas E. Warner <silfreed@silfreed.net> 0.3.8-1
- upgrade to 0.3.8

* Thu Feb 10 2005 Douglas E. Warner <silfreed@silfreed.net> 0.3.6-2
- compile ipw driver in

* Wed Feb 09 2005 Douglas E. Warner <silfreed@silfreed.net> 0.3.6-1
- upgrade to 0.3.6

* Thu Dec 23 2004 Douglas E. Warner <silfreed@silfreed.net> 0.2.5-4
- fixing init script

* Mon Dec 20 2004 Douglas E. Warner <silfreed@silfreed.net> 0.2.5-3
- fixing init script
- adding post/preun items to add/remove via chkconfig

* Mon Dec 20 2004 Douglas E. Warner <silfreed@silfreed.net> 0.2.5-2
- adding sysV scripts

* Mon Dec 20 2004 Douglas E. Warner <silfreed@silfreed.net> 0.2.5-1
- Initial RPM release.

