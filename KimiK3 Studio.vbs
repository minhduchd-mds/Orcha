Option Explicit
Dim sh, fso, root, target
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
target = root & "\Orcha.vbs"
If fso.FileExists(target) Then
  sh.Run "wscript.exe """ & target & """", 1, False
Else
  MsgBox "Khong tim thay Orcha.vbs. Hay tai lai goi Orcha moi nhat.", 16, "Orcha"
End If
