Option Explicit
Dim r
On Error Resume Next
Set r = CreateObject("WinHttp.WinHttpRequest.5.1")
r.SetTimeouts 500, 500, 500, 500
r.Open "POST", "http://127.0.0.1:11435/api/app/shutdown", False
r.SetRequestHeader "Content-Type", "application/json"
r.Send "{}"
WScript.Sleep 300
On Error GoTo 0
