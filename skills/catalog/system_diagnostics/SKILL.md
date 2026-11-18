---
name: system_diagnostics
description: Analyze Windows system health, memory load, and disk bottlenecks.
author: Chairman / JARVIS
tags:
- windows
- performance
- system
---

## Diagnostics Procedure
1. Check CPU, RAM, and Disk metrics with get_system_stats.
2. If memory exceeds 85%, identify background processes via execute_powershell 'Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 5'.
3. Formulate clear optimization recommendations.
