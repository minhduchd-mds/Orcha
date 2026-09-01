Option Explicit
On Error Resume Next
Dim r
Set r = CreateObject("WinHttp.WinHttpRequest.5.1")
r.SetTimeouts 1000,1000,1000,1000
r.Open "POST", "http://127.0.0.1:11435/api/app/shutdown", False
r.SetRequestHeader "Content-Type", "application/json"
r.Send "{}"
On Error GoTo 0
