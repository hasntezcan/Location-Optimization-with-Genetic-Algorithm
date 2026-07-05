# V1 Benchmarking

## Purpose

Benchmarking translates optimization outputs into careful, comparable, decision-support claims.

The optimizer can produce objective values such as `f1` and `f2`, but users, firms, investors, and public-sector stakeholders need clearer planning answers:

* Is the optimized scenario better than the current network under the same assumptions?
* Can the same coverage be achieved with fewer facilities?
* What changes if existing facilities are included or excluded?
* Which scenario serves more demand?
* Which scenario reduces access distance?
* Which scenario improves equity or response coverage?
* Which areas gain or lose service?
* Are results based on proxy demand or calibrated real demand?

Benchmarking should not overstate results. It should explain what was compared, under which assumptions, and with which data.

## Why F1/F2 Is Not Enough

F1 and F2 are useful optimizer objectives, but they are not enough for business or planning communication.

Current V0 objectives:

* `f1`: accessibility cost,
* `f2`: neighborhood equity cost.

These are useful for Pareto optimization, but external stakeholders often care about:

* demand covered,
* users reached,
* service gaps,
* number of facilities required,
* marginal value of adding one more facility,
* cost per covered demand,
* operational feasibility,
* current network vs optimized network.

V1 benchmarking should convert objective values into scenario-based statements.

Example:

```text id="9hxaqu"
Under the proxy demand model, the optimized same-K scenario covers 14% more demand within 500 meters than the current network.
```

not:

```text id="cbbtjl"
The optimizer proves the current network is bad.
```

## Benchmarking Core Principle

Benchmark claims are valid only when the comparison is well-defined.

Every benchmark must identify:

* scenario A,
* scenario B,
* candidate/grid data version,
* distance matrix version,
* objective bundle,
* demand type,
* facility count semantics,
* existing facility assumptions,
* constraints,
* coverage thresholds,
* whether the comparison is same-K, same-coverage, expansion, or greenfield.

Do not compare results without scenario context.

## Scenario-Based Benchmarking

V1 benchmarks should compare scenarios.

A scenario may represent:

* current network,
* greenfield optimized network,
* existing network plus new facilities,
* manually edited plan,
* reduced network,
* alternative objective bundle,
* alternative demand assumptions.

Examples:

```text id="jwh2oz"
Scenario A: Current network
Scenario B: Optimized same total facility count
Scenario C: Existing network + 5 new proposed facilities
Scenario D: Minimum facilities needed to match current coverage
```

The current network must be represented as scenario facilities, not inferred from proximity counts.

Do not infer existing locations from:

```text id="al43pa"
nearby_locker_count > 0
```

Existing facilities should come from:

```text id="2fd2qq"
scenario.facilities[]
```

or, during V0 migration, a clearly documented scenario seeded from `existing_locker_count`.

## Benchmark Compatibility Rules

Before comparing two scenarios, verify compatibility.

### Required Compatibility

Two scenarios can be compared directly only if they share:

* same candidate universe,
* same distance matrix or same distance model,
* same grid/candidate version,
* same demand model or clearly documented demand variants,
* same coordinate and snapping assumptions,
* same coverage threshold when reporting coverage,
* same objective/bundle context when comparing objective values.

### Facility Count Compatibility

A benchmark must clearly state whether it is:

* same-K,
* same total facility count,
* same new facility count,
* same coverage target,
* expansion from current network,
* greenfield from scratch.

Never leave `K` ambiguous.

### Scenario Assumption Compatibility

Reports must state:

* existing ON or OFF,
* locked candidates,
* disabled candidates,
* forbidden candidate handling,
* manual edits,
* imported facilities,
* objective bundle,
* demand type.

## Benchmark Types

## 1. Current Network Evaluation

This benchmark evaluates only the enabled existing facilities.

Question:

```text id="lntibz"
How well does the current network perform under the selected data and metric model?
```

Typical run type:

```text id="oinb4l"
current_network
```

Inputs:

* active existing scenario facilities,
* candidate grid,
* demand model,
* distance matrix,
* benchmark metrics.

Outputs:

* covered demand,
* uncovered demand,
* average access distance,
* equity gap,
* worst-served zones,
* cost estimate if available.

Use this as the baseline for many comparisons.

## 2. Same-K / Same Facility Count Comparison

This benchmark answers:

```text id="d48p6k"
If we keep the same number of facilities, how does the optimized network compare with the current network?
```

Example:

```text id="yhvb0v"
Current network: 27 physical facilities
Optimized greenfield: 27 proposed facilities
```

or, if multiple physical facilities snap to one candidate:

```text id="21ye4n"
Current network: 27 physical facilities / 26 effective candidate locations
Optimized greenfield: 26 effective candidate locations
```

The report must state whether the comparison uses physical facility count or effective candidate location count.

Typical metrics:

* covered demand within threshold,
* average weighted distance,
* median distance,
* 90th percentile distance,
* equity score,
* worst-zone access,
* cost per covered demand if cost exists.

Careful claim example:

```text id="vwoe71"
Under the proxy demand model and the same effective candidate-location count, the optimized scenario reduces average weighted access cost by X% compared with the current scenario.
```

## 3. Same Coverage With Fewer Facilities

This benchmark answers:

```text id="4nw4wn"
How many facilities are required to match or exceed current coverage?
```

Example logic:

```text id="u1tahq"
Current network covers 82% of proxy demand within 500 meters.
Optimized K=8 covers 83%.
Optimized K=7 covers 79%.
Therefore, under this proxy model and threshold, K=8 is the smallest tested optimized network that matches or exceeds current coverage.
```

This benchmark is useful for business-facing claims such as:

```text id="dk0gql"
Similar coverage may be achievable with fewer facilities under the model assumptions.
```

Avoid:

```text id="405lsg"
The company can definitely remove X facilities.
```

Operational decisions require real usage, capacity, cost, lease, and feasibility data.

## 4. Expansion Optimization

This benchmark answers:

```text id="ltd92m"
If we keep the current network, where should we add new facilities?
```

Typical run type:

```text id="u6h3dc"
expansion_optimization
```

Example:

```text id="zxlzf1"
Existing ON + targetNewFacilityCount = 5
```

means:

```text id="n2mq5b"
current enabled existing facilities remain active, and the optimizer selects 5 additional proposed locations
```

Metrics:

* additional demand covered,
* marginal demand gain,
* reduction in uncovered demand,
* improvement in worst-served zones,
* overlap with existing facilities,
* cost per marginal covered demand.

## 5. Manual Scenario Comparison

This benchmark compares user-edited scenarios.

Examples:

* planner disables one existing facility,
* user adds three manual locations,
* user locks one proposed location,
* imported CSV locations are corrected manually,
* two stakeholder-proposed networks are compared.

Questions:

```text id="m0nl4v"
What happens if we remove this location?
What happens if we add this proposed site?
What happens if we force a facility into this neighborhood?
```

This is central to the V1 map sandbox.

## 6. Objective Bundle Comparison

This benchmark compares different planning priorities.

Examples:

```text id="ixikwh"
accessibility + demand coverage
accessibility + equity
response time + risk coverage
coverage + cost efficiency
```

Reports must state that changing the objective bundle changes the optimization problem.

Do not imply that one objective bundle is universally better. It is better only relative to the stated planning goal.

## Core Benchmark Metrics

V1 benchmark outputs may include the following metrics.

### Facility Count Metrics

* total active facilities,
* active existing facilities,
* proposed new facilities,
* effective candidate locations,
* physical facility count,
* disabled facilities,
* locked facilities.

### Access Metrics

* average distance,
* demand-weighted average distance,
* median distance,
* 90th percentile distance,
* maximum distance,
* travel time if network distance is available.

### Coverage Metrics

* covered demand within 300m,
* covered demand within 500m,
* covered demand within 700m,
* uncovered demand,
* covered population,
* uncovered population,
* percent demand covered,
* percent population covered.

### Equity Metrics

* neighborhood equity cost,
* worst-served neighborhood,
* gap between best-served and worst-served zones,
* coefficient of variation across zones,
* underserved area coverage.

### Business Metrics

* cost per covered demand,
* cost per facility,
* marginal demand gain,
* marginal cost per additional covered demand,
* demand per facility,
* overlap / cannibalization proxy,
* estimated operating cost if available,
* estimated installation cost if available.

### Emergency / Public Service Metrics

* average response time,
* 90th percentile response time,
* high-risk uncovered zones,
* incident-weighted response distance,
* equity of emergency coverage,
* population outside response threshold.

## Demand Type

Every benchmark must state demand type.

### Proxy Demand

Proxy demand is estimated from indirect indicators.

Examples:

* population,
* POI density,
* transit access,
* commercial activity,
* risk proxies,
* incident proxies,
* service gap indicators.

Proxy demand is useful for exploratory planning but should not be presented as observed customer demand.

### Calibrated Real Demand

Calibrated real demand uses observed data.

Examples:

* deliveries,
* orders,
* failed deliveries,
* returns,
* emergency calls,
* incident records,
* clinic visits,
* service usage,
* store transactions.

Calibrated demand supports stronger operational claims, but still depends on data quality, time period, and modeling assumptions.

### Claim Rule

If demand is proxy, say:

```text id="8gy8dm"
under the proxy demand model
```

If demand is calibrated real demand, say:

```text id="h6scr0"
under the calibrated demand model using [data period/source]
```

Do not blur these two.

## Example Benchmark Table

Values below are illustrative and should not be treated as project results.

| Scenario          | Facility count | Covered proxy demand within 500m | Avg weighted distance | Equity cost | Notes                                  |
| ----------------- | -------------: | -------------------------------: | --------------------: | ----------: | -------------------------------------- |
| Current network   |             10 |                              82% |                 410 m |        0.31 | Existing facilities only               |
| Optimized same K  |             10 |                              91% |                 330 m |        0.24 | Same facility count                    |
| Optimized fewer K |              8 |                              83% |                 395 m |        0.28 | Similar coverage with fewer facilities |
| Expansion         |             13 |                              95% |                 280 m |        0.21 | Existing plus 3 proposed               |

A real benchmark table should include:

* scenario IDs,
* data version,
* demand type,
* facility count semantics,
* existing ON/OFF,
* objective bundle,
* coverage threshold.

## Example Business Claim Templates

### Same-K Improvement

```text id="o1sazo"
Under the proxy demand model and the same facility-count assumption, the optimized scenario covers X% more demand within 500 meters than the current network.
```

### Access Improvement

```text id="ja7xrj"
Under the same candidate universe and distance model, the optimized scenario reduces demand-weighted average access distance by X% compared with the current scenario.
```

### Fewer Facilities

```text id="x9r6b7"
Under the proxy demand model, the optimized K=N scenario matches or exceeds the current network's 500-meter coverage using M fewer effective candidate locations.
```

### Expansion

```text id="3mv2gx"
Keeping the current enabled facilities fixed, adding N optimized facilities increases covered proxy demand within 500 meters by X percentage points.
```

### Manual Scenario

```text id="buab32"
Compared with the current scenario, the manually edited scenario improves coverage in [area/zone] but increases average access distance by X%, showing a tradeoff between local priority and system-wide efficiency.
```

## Claims to Avoid

Avoid claims like:

```text id="62yb7c"
This proves the city needs exactly X facilities.
```

```text id="8pwnec"
The optimizer found the true best business plan.
```

```text id="1ykxlh"
The current network is definitely bad.
```

```text id="xs342u"
The company can remove X facilities without risk.
```

```text id="z7iq5d"
This result guarantees higher revenue.
```

Use careful scenario-specific language instead.

## Valid Claim Pattern

Good benchmark claims follow this structure:

```text id="jf6zgb"
Under [data model],
using [candidate universe],
with [scenario assumptions],
and [facility count semantics],
scenario A performs [X metric] better/worse than scenario B.
```

Example:

```text id="inaitv"
Under the proxy demand model, using the Kadikoy candidate grid and the same effective facility count, the optimized greenfield scenario reduces demand-weighted access cost by X% compared with the current network scenario.
```

## Required Benchmark Metadata

Every benchmark report should include:

* benchmark ID,
* scenario IDs compared,
* candidate source,
* distance matrix source,
* candidate ID order,
* demand type,
* objective bundle,
* run type,
* existing ON/OFF setting,
* target facility count semantics,
* active existing candidate IDs count,
* proposed facility count,
* locked candidate IDs count,
* disabled candidate IDs count,
* coverage threshold,
* distance type,
* matrix units,
* timestamp where available,
* code/data version or file hashes where available.

## Scenario Comparison Checklist

Before publishing or presenting a benchmark, check:

* Are both scenarios using the same candidate universe?
* Are both scenarios using the same distance matrix?
* Are facility counts comparable?
* Is the benchmark same-K, same-coverage, expansion, or manual comparison?
* Is demand proxy or calibrated?
* Are existing facilities ON or OFF?
* Are locked/disabled candidates documented?
* Are manually edited facilities documented?
* Are forbidden candidates handled consistently?
* Are objective bundles stated?
* Are coverage thresholds stated?
* Are results reproducible from metadata?

## Benchmark Output Files

Future benchmark outputs should be run-specific rather than shared global files.

Recommended structure:

```text id="ckfsmx"
output/runs/<run_id>/
  scenario.json
  run_metadata.json
  final_archive.csv
  benchmark_summary.json
  benchmark_summary.csv
  benchmark_report.md
```

Current V0 scripts may still write shared outputs under:

```text id="so43vd"
output/
```

V1 should move toward run-specific outputs to avoid overwriting and to support reproducibility.

## Benchmark Engine Responsibilities

The Benchmark & Reporting Engine should:

* load scenarios,
* validate comparison compatibility,
* compute metrics,
* compare current and optimized networks,
* produce tables,
* produce careful text claims,
* preserve metadata,
* distinguish proxy and calibrated demand,
* flag invalid or weak comparisons.

It should not silently compare incompatible scenarios.

## Minimum Useful V1 Benchmark Set

The first useful V1 benchmark set should include:

### A. Current Network

```text id="zoblx3"
enabled existing facilities only
```

### B. Greenfield Same Effective Facility Count

```text id="rasau1"
existing OFF, optimized from scratch, same effective candidate-location count
```

### C. Greenfield Same Physical Facility Count

```text id="hbodg4"
existing OFF, optimized from scratch, same physical facility count if relevant
```

### D. Expansion

```text id="xfnvle"
existing ON, add N new optimized facilities
```

### E. Minimum K for Same Coverage

```text id="gavfoy"
find smallest tested optimized K that matches current coverage threshold
```

These five comparisons are enough to support early firm/investor discussions without overclaiming.

## V0 to V1 Benchmark Migration

Current V0 benchmark scripts may use:

```text id="lwlz45"
data/candidate_points.csv
output/final_archive.csv
output/run_metadata.json
```

V1 should migrate toward:

```text id="d90sza"
scenario input
run-specific optimizer output
benchmark output tied to scenario metadata
```

Migration path:

```text id="s9psqr"
existing_locker_count from V0
  -> default current-network scenario
  -> current network benchmark
  -> optimized scenario comparison
  -> scenario-based benchmark report
```

Do not use `nearby_locker_count` to construct current network benchmarks.

## Non-Negotiable Rules

* Do not claim real-world business improvement without stating data assumptions.
* Do not compare scenarios with different candidate universes without saying so.
* Do not compare K values without explaining facility count semantics.
* Do not infer current network from `nearby_locker_count`.
* Do not hide whether existing facilities were ON or OFF.
* Do not treat proxy demand as observed demand.
* Do not report “best” without stating the objective bundle.
* Do not publish benchmark numbers without scenario metadata.
* Do not use global overwritten output files as the only benchmark record for important comparisons.

## Summary

Benchmarking is the bridge between optimization and decision-making.

The V1 benchmark spine is:

```text id="1we4de"
scenario assumptions
  -> compatible comparison
  -> objective and coverage metrics
  -> business/planning interpretation
  -> careful claim language
  -> reproducible report metadata
```

The goal is not to say:

```text id="ja5sro"
the optimizer is always right
```

The goal is to say:

```text id="9mxygw"
under these data and scenario assumptions, this alternative performs better on these measurable criteria
```
