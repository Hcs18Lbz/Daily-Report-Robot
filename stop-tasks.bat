@echo off
echo Stopping AI News scheduled tasks...
powershell -Command "Unregister-ScheduledTask -TaskName 'AI-News-Morning' -Confirm:$false"
powershell -Command "Unregister-ScheduledTask -TaskName 'AI-News-Evening' -Confirm:$false"
echo Done.
pause
