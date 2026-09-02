Option Explicit
Dim sh, fso, root, url, cmd, ok, i, edge, chrome, appCmd
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
url = "http://127.0.0.1:11435/"
Function ServerReady()
  On Error Resume Next
  Dim r, body
  Set r = CreateObject("WinHttp.WinHttpRequest.5.1")
  r.SetTimeouts 500, 500, 500, 500
  r.Open "GET", url & "health", False
  r.Send
  body = r.ResponseText
  ServerReady = (Err.Number = 0 And r.Status = 200 And InStr(1, body, "7.5.0", 1) > 0 And InStr(1, body, "Orcha", 1) > 0 And InStr(1, body, "ui_foundation", 1) > 0)
  Err.Clear
  On Error GoTo 0
End Function
Sub StopOldServer()
  On Error Resume Next
  Dim r
  Set r = CreateObject("WinHttp.WinHttpRequest.5.1")
  r.SetTimeouts 500, 500, 500, 500
  r.Open "POST", url & "api/app/shutdown", False
  r.SetRequestHeader "Content-Type", "application/json"
  r.Send "{}"
  WScript.Sleep 500
  Err.Clear
  On Error GoTo 0
End Sub
If Not ServerReady() Then
  StopOldServer
  cmd = "cmd.exe /d /s /c """"" & root & "\scripts\_python.cmd"" """ & root & "\app\studio_server_v70.py"" --profile balanced --port 11435"""
  sh.Run cmd, 0, False
  ok = False
  For i = 1 To 60
    WScript.Sleep 250
    If ServerReady() Then ok = True: Exit For
  Next
Else
  ok = True
End If
If Not ok Then
  MsgBox "Orcha v7.5 khong khoi dong duoc. Hay chay INSTALL.bat hoac kiem tra Python/Ollama.", 16, "Orcha"
  WScript.Quit 1
End If
edge = sh.ExpandEnvironmentStrings("%ProgramFiles(x86)%") & "\Microsoft\Edge\Application\msedge.exe"
If Not fso.FileExists(edge) Then edge = sh.ExpandEnvironmentStrings("%ProgramFiles%") & "\Microsoft\Edge\Application\msedge.exe"
chrome = sh.ExpandEnvironmentStrings("%ProgramFiles%") & "\Google\Chrome\Application\chrome.exe"
If Not fso.FileExists(chrome) Then chrome = sh.ExpandEnvironmentStrings("%ProgramFiles(x86)%") & "\Google\Chrome\Application\chrome.exe"
If fso.FileExists(edge) Then
  appCmd = """" & edge & """ --app=" & url & " --start-maximized"
  sh.Run appCmd, 1, False
ElseIf fso.FileExists(chrome) Then
  appCmd = """" & chrome & """ --app=" & url & " --start-maximized"
  sh.Run appCmd, 1, False
Else
  sh.Run url, 1, False
End If
