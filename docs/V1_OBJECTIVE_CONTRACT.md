# V1 Objective Contract

## Why Objectives Need to Be Modular

The current system is tied to a parcel locker objective pair. V1 needs objectives that can be combined by use case without rewriting the optimizer core.

Modular objectives allow:

- Different facility domains to share the same optimization engine.
- Clear naming and reporting for business users.
- Independent validation of objective inputs.
- Safer migration from V0 parcel locker logic to generic location optimization.

## Current F1 and F2

The current Java SPEA2 engine evaluates:

- `f1`: accessibility cost, based on demand-weighted distance to the nearest selected locker.
- `f2`: equity cost, based on inequality of accessibility quality across neighborhoods.

Both are minimization objectives.

## Future Objective Interface Concept

A future objective should define:

- `id`: stable objective identifier.
- `label`: business-readable name.
- `direction`: initially `minimize`.
- `requiredCandidateFields`: grid or feature columns required by the objective.
- `requiredScenarioFields`: scenario entities or settings required by the objective.
- `evaluate(solution, context)`: returns a numeric value.
- `reportingUnit`: meters, cost, coverage loss, minutes, risk score, or another domain unit.
- `normalization`: optional normalization method for comparison and UI display.

## Minimize-Only Strategy for Early V1

Early V1 should keep all objectives as minimize-only values. Metrics that users think of as "higher is better" can be converted to losses or penalties.

Examples:

- Maximize coverage becomes minimize uncovered demand.
- Maximize equity becomes minimize inequality.
- Maximize service quality becomes minimize travel time or access cost.

This keeps Pareto comparison and current SPEA2 behavior simpler during the migration.

## Example Objectives

- Accessibility cost: demand-weighted distance or travel time to nearest facility.
- Demand coverage loss: unmet demand outside a service threshold.
- Cost efficiency: facility cost, operating cost, or cost per covered demand unit.
- Equity: inequality across neighborhoods, groups, or zones.
- Response time: emergency or service response travel time.
- Risk coverage: uncovered risk exposure or hazard-weighted distance.
- Cannibalization / overlap penalty: excessive overlap with existing facilities or same-brand service areas.

## Use-Case Objective Set Examples

### Parcel Locker Business

- Minimize accessibility cost.
- Minimize uncovered demand.
- Minimize overlap with existing lockers.
- Minimize operating cost or facility count for a target service level.

### Food Desert

- Minimize distance to healthy food access.
- Minimize uncovered low-income or low-access population.
- Minimize inequity across neighborhoods.
- Minimize implementation cost.

### Fire Stations

- Minimize response time.
- Minimize high-risk uncovered zones.
- Minimize inequity in response coverage.
- Minimize overlap or redundant coverage.

### Police

- Minimize response time to incident demand.
- Minimize uncovered risk hotspots.
- Minimize inequity across patrol zones.
- Minimize station or staffing cost proxy.

## Contract Requirements

- Objectives should declare required inputs.
- Objective outputs should be named and unit-aware.
- Objective logic should not assume parcel lockers unless the objective is explicitly parcel-locker-specific.
- Objective bundles should be scenario configuration, not hard-coded UI or optimizer behavior.

