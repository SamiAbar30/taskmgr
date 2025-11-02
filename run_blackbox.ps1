# Run taskmgr on the generated blackbox_commands.txt and save output
Set-Location -Path "$PSScriptRoot"
python .\taskmgr.py .\blackbox_commands.txt | Tee-Object -FilePath .\blackbox_results.txt
Write-Host "Wrote results to blackbox_results.txt"

# Pause so the terminal window does not immediately close when run by double-click
Write-Host "Press ENTER to close this window or Ctrl+C to cancel"
Read-Host | Out-Null
