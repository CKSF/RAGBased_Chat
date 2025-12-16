$keepVersion = "Python 3.12"
$products = Get-WmiObject -Class Win32_Product | Where-Object { 
    $_.Name -like "*Python*" -and $_.Name -notlike "*$keepVersion*" -and $_.Name -notlike "*Launcher*"
}

if ($products) {
    Write-Host "Found the following components to SCRUB:"
    $products | ForEach-Object { Write-Host " - $($_.Name) ($($_.IdentifyingNumber))" }
    
    foreach ($product in $products) {
        Write-Host "Scrubbing $($product.Name)..."
        # Try standard uninstall
        $proc = Start-Process msiexec.exe -ArgumentList "/x $($product.IdentifyingNumber) /quiet /norestart" -Wait -PassThru
        
        if ($proc.ExitCode -eq 0) {
            Write-Host "[OK] Removed $($product.Name)"
        } elseif ($proc.ExitCode -eq 1603) {
             # 1603 often means "Fatal error during installation" or "Already gone"
             # We can try to force clean via registry if needed, but usually it means it's broken.
             Write-Host "[WARN] Component might be broken/missing (Code 1603). It is likely effectively gone."
        } else {
            Write-Host "[ERR] Failed with code $($proc.ExitCode)"
        }
    }
} else {
    Write-Host "Clean! No old Python versions found."
}
