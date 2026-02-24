Set objWMIService = GetObject("winmgmts:\\.\root\cimv2")
Set colItems = objWMIService.ExecQuery("Select * from Win32_Process Where Name = 'uvicorn.exe' AND CommandLine LIKE '%api:api%--port 9880%'")

If colItems.Count > 0 Then
    WScript.Quit
End If

Set WshShell = CreateObject("WScript.Shell")
' Get the directory of the VBS file
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = fso.BuildPath(scriptDir, "start_service.bat")
WshShell.Run Chr(34) & batPath & Chr(34), 0, False