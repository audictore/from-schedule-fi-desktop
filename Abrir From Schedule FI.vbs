' Lanza From Schedule FI sin mostrar la ventana de consola.
' Corre "npm start" (modo desarrollo: el solver va por WSL, esquiva Smart App Control).
Dim fso, sh, here
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")
here = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = here
' 0 = ventana oculta ; False = no esperar a que termine
sh.Run "cmd /c npm start", 0, False
