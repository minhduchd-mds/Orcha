Option Explicit
Dim sh, fso, root, desktop, link
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
desktop = sh.SpecialFolders("Desktop")
Set link = sh.CreateShortcut(desktop & "\KimiK3-Lite Studio.lnk")
link.TargetPath = "wscript.exe"
link.Arguments = """" & root & "\KimiK3 Studio.vbs"""
link.WorkingDirectory = root
link.Description = "KimiK3-Lite Desktop Studio"
link.Save
