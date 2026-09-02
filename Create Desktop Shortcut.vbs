Option Explicit
Dim sh, fso, root, desktop, link
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
desktop = sh.SpecialFolders("Desktop")
Set link = sh.CreateShortcut(desktop & "\Orcha.lnk")
link.TargetPath = "wscript.exe"
link.Arguments = """" & root & "\Orcha.vbs"""
link.WorkingDirectory = root
link.Description = "Orcha Autonomous Work Platform"
link.Save
