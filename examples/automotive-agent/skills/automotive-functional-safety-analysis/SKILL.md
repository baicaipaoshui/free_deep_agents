---
name: automotive-functional-safety-analysis
description: >
  Use this skill for automotive functional safety analysis across ADAS features.
  Trigger this skill when the task mentions HARA, ASIL decomposition, ISO 26262,
  safety goals, safety concept, FMEA/FTA, fault handling, safety mechanisms,
  diagnostic coverage, or safety case review for production vehicles.
allowed-tools: read_file
metadata:
  domain: automotive-functional-safety
  trigger-keywords: hara, asil, iso-26262, safety-goal, fmea, fta, diagnostics
  profile: starter
---

# Automotive Functional Safety Analysis Skill Pack

## Scope

Use this skill when the user asks for safety engineering outputs, not only
performance architecture. This skill is focused on safety argument quality and
traceability from hazards to technical mitigations.

## Reference Index

Start with these files and read only what is needed:

- AUTOSAR and platform integration constraints:
  `./skills/references/autosar-adas-integration.md`
- ADAS feature behavior and operational assumptions:
  `./skills/references/adas-features-implementation.md`
- Perception pipeline failure modes:
  `./skills/references/sensor-fusion-perception.md`
- Sensor-level limitations and degradation behavior:
  `./skills/references/radar-lidar-processing.md`
- Vision stack edge cases:
  `./skills/references/camera-processing-vision.md`
- Localization and map dependency risks:
  `./skills/references/hd-maps-localization.md`
- Planning/control fallback strategy context:
  `./skills/references/path-planning-control.md`

## Analysis Checklist

1. Define item and operational design domain assumptions.
2. Identify hazards and hazardous events by driving scenario.
3. Draft HARA severity, exposure, and controllability rationale.
4. Derive safety goals and candidate ASIL allocations.
5. Map safety mechanisms to sensing, fusion, planning, and control layers.
6. Identify residual risk and verification evidence gaps.
7. Output a concise safety review with assumptions and open risks.

## Output Template

When possible, structure the answer in this order:

1. Safety context and assumptions.
2. Hazard list and HARA rationale.
3. Safety goals and ASIL candidates.
4. Proposed technical safety mechanisms.
5. Verification strategy and unresolved risks.
