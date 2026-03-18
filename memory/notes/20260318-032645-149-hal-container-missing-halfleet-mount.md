---
id: 20260318-032645-149
title: HAL container missing halfleet mount
type: decision
tags:
- architecture
- hal
- fleet
confidence: high
created: '2026-03-18T03:26:45Z'
modified: '2026-03-18T03:26:45Z'
expires: null
---

HAL's container does not mount /home/mrkai/code/halfleet/, preventing fleet audit and management tasks. HAL hotline needs read (ideally read-write) access to halfleet/ as a fourth workspace mount. Deferred.
