ZondEditor installer build notes
===============================

1) Build application EXE first:
   build\build_exe.bat

2) Compile installer with Inno Setup 6:
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\installer_protected.iss

3) Result:
   dist_installer\ZondEditor_setup.exe

Installer behavior:
- Installs dist\ZondEditor\* into Program Files\ZondEditor
- Creates desktop shortcut
- Creates ProgramData\ZondEditor and ProgramData\ZondEditor\logs
- Runs "ZondEditor.exe --init-license" after install (admin context)
