@echo off
echo Creating AI News scheduled tasks...
powershell -Command "$action = New-ScheduledTaskAction -Execute 'E:\Clone_repository\Daily-Report-Robot\scripts\run.bat' -WorkingDirectory 'E:\Clone_repository\Daily-Report-Robot'; $trigger1 = New-ScheduledTaskTrigger -Daily -At '09:00'; $trigger2 = New-ScheduledTaskTrigger -Daily -At '19:00'; $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable; Register-ScheduledTask -TaskName 'AI-News-Morning' -Action $action -Trigger $trigger1 -Settings $settings -Description 'Daily 9am AI news push' -Force; Register-ScheduledTask -TaskName 'AI-News-Evening' -Action $action -Trigger $trigger2 -Settings $settings -Description 'Daily 7pm AI news push' -Force"
echo Done. Morning: 09:00 | Evening: 19:00
pause
