---
name: automotive-adas
description: >
  Use this skill for automotive ADAS system design, perception, planning,
  control, sensor fusion, camera processing, radar and lidar workflows,
  HD maps, localization, and AUTOSAR integration. Trigger this skill when
  the user asks about ADAS architecture, lane keeping, adaptive cruise
  control, perception stacks, planning pipelines, automotive sensors,
  localization, or production vehicle driver assistance implementation.
allowed-tools: read_file
metadata:
  domain: adas
  trigger-keywords: adas, perception, planning, control, sensor-fusion, localization
---

# Automotive ADAS Skill Pack

## Scope

Use this skill for broad ADAS architecture and implementation topics.
If the request is specifically about safety goals, HARA, ASIL, or ISO 26262
work products, switch to `automotive-functional-safety-analysis` first.

## Reference Index

Read only the files that match the user request:

- ADAS feature implementation:
  `./skills/references/adas-features-implementation.md`
- AUTOSAR integration:
  `./skills/references/autosar-adas-integration.md`
- Camera processing and vision:
  `./skills/references/camera-processing-vision.md`
- HD maps and localization:
  `./skills/references/hd-maps-localization.md`
- Path planning and control:
  `./skills/references/path-planning-control.md`
- Radar and lidar processing:
  `./skills/references/radar-lidar-processing.md`
- Sensor fusion and perception:
  `./skills/references/sensor-fusion-perception.md`

## Workflow

1. Identify the ADAS subsystem or engineering topic.
2. Read the most relevant reference file from the index.
3. If the request spans multiple subsystems, read multiple files and synthesize.
4. Produce implementation guidance, architecture advice, or technical review feedback.
