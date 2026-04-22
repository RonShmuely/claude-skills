---
name: pcusage
description: Report live PC system usage stats — CPU, GPU, RAM, disk, network, and running processes. Trigger when the user says "PCUSAGE", "pc usage", "system stats", "how's my PC doing", "check resources", "monitor system", or any variation asking about current hardware utilization. Always run the PowerShell monitoring script and present results in a clean table format.
---

# PCUSAGE — Live System Monitor

Collect and display real-time system resource usage in a single snapshot. This runs on Windows 11 with PowerShell.

## What to Collect

Run the PowerShell script below via Bash, then present the results in a clean markdown table. The script collects everything in one shot.

## PowerShell Script

Save to a temp file and execute — don't try to run inline (escaping issues in bash):

```
cat > /tmp/pcusage.ps1 << 'PSEOF'
# CPU
$cpu = (Get-CimInstance Win32_Processor).LoadPercentage
Write-Output "CPU_LOAD=$cpu%"

# RAM
$os = Get-CimInstance Win32_OperatingSystem
$totalGB = [math]::Round($os.TotalVisibleMemorySize/1MB, 1)
$freeGB = [math]::Round($os.FreePhysicalMemory/1MB, 1)
$usedGB = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1MB, 1)
$ramPct = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/$os.TotalVisibleMemorySize * 100, 0)
Write-Output "RAM_USED=${usedGB}GB / ${totalGB}GB (${ramPct}%)"

# GPU (nvidia-smi)
try {
    $nv = & "C:\Windows\System32\nvidia-smi.exe" --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader,nounits 2>$null
    if ($nv) {
        $parts = $nv.Split(',').Trim()
        Write-Output "GPU_UTIL=$($parts[0])%"
        Write-Output "GPU_VRAM=$($parts[1])MB / $($parts[2])MB"
        Write-Output "GPU_TEMP=$($parts[3])C"
        Write-Output "GPU_POWER=$($parts[4])W"
    }
} catch { Write-Output "GPU_UTIL=N/A" }

# Disks
Get-Volume | Where-Object { $_.DriveLetter -and $_.Size -gt 0 } | ForEach-Object {
    $letter = $_.DriveLetter
    $totalG = [math]::Round($_.Size/1GB, 1)
    $freeG = [math]::Round($_.SizeRemaining/1GB, 1)
    $usedPct = [math]::Round(($_.Size - $_.SizeRemaining)/$_.Size * 100, 0)
    Write-Output "DISK_${letter}=${freeG}GB free / ${totalG}GB (${usedPct}% used)"
}

# Network (bytes sent/received since boot)
$net = Get-NetAdapterStatistics -ErrorAction SilentlyContinue | Where-Object { $_.ReceivedBytes -gt 0 } | Select-Object -First 1
if ($net) {
    $rxGB = [math]::Round($net.ReceivedBytes/1GB, 2)
    $txGB = [math]::Round($net.SentBytes/1GB, 2)
    Write-Output "NET_RX=${rxGB}GB received"
    Write-Output "NET_TX=${txGB}GB sent"
}

# Top 5 processes by RAM
Write-Output "TOP_PROCS:"
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 5 | ForEach-Object {
    $memMB = [math]::Round($_.WorkingSet64/1MB, 0)
    Write-Output "  $($_.Name): ${memMB}MB"
}

# Uptime
$boot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime
$up = (Get-Date) - $boot
Write-Output "UPTIME=$([math]::Floor($up.TotalHours))h $($up.Minutes)m"
PSEOF
powershell -ExecutionPolicy Bypass -File /tmp/pcusage.ps1
```

## Output Format

Parse the script output and present as:

```
## PC Usage Snapshot

| Resource | Status |
|----------|--------|
| **CPU** | 23% |
| **RAM** | 18.2GB / 31.8GB (57%) |
| **GPU** | 45% — VRAM 4200MB / 16048MB — 52°C — 85W |
| **Disk C:** | 255GB free / 930GB (73% used) |
| **Disk D:** | 1.2TB free / 1.8TB (35% used) |
| **Network** | ↓ 2.3GB received ↑ 0.8GB sent |
| **Uptime** | 14h 32m |

### Top Processes (by RAM)
| Process | Memory |
|---------|--------|
| chrome | 1,842MB |
| LM Studio | 890MB |
| ... | ... |
```

If the user asks to log this, append the snapshot with a timestamp to `C:\Users\ronsh\Desktop\WeldingRef\weld-log-data\pc-usage-log.json`. Create the file if it doesn't exist, as a JSON array of snapshots.
