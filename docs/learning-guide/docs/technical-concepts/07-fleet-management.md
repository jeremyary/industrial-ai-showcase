# Fleet Management & Orchestration

## From one robot to many

Most physical AI research focuses on a single robot performing a single
task. Production deployments involve fleets — tens to hundreds of robots
operating in the same facility, coordinated to achieve throughput targets
without collisions, conflicts, or idle time.

Fleet management is where physical AI meets distributed systems, and
where your Kubernetes and infrastructure experience translates most
directly.

## What fleet management does

A fleet management system coordinates multiple robots to accomplish
work efficiently and safely. Its responsibilities parallel those of a
container orchestrator, but in the physical domain:

| Container orchestration | Fleet management |
|------------------------|-----------------|
| Schedule pods to nodes | Assign missions to robots |
| Health checks and readiness | Robot status monitoring (battery, errors, position) |
| Load balancing | Work distribution across the fleet |
| Rolling updates | Policy version rollout across robots |
| Autoscaling | Fleet size adjustment |
| Service discovery | Robot localization and availability |
| Resource limits | Safety zones, speed limits, payload capacity |

## Core fleet management components

### Mission dispatch

The fleet manager receives work orders (from a warehouse management
system, manufacturing execution system, or human operator) and
translates them into robot missions. A mission is a sequence of tasks:
navigate to location A, pick up pallet B, transport to location C,
place at position D.

The dispatcher must consider:

- **Robot capabilities**: Which robots can perform this task? (payload
  capacity, gripper type, battery level)
- **Robot proximity**: Which available robot is closest to the task
  start point?
- **Traffic**: Will assigning this mission create a conflict with
  other active missions?
- **Priority**: Is this mission urgent (safety-related) or routine?

### Path planning and traffic management

When multiple robots share the same physical space, their paths must
be coordinated to avoid:

- **Collisions**: Two robots attempting to occupy the same space
- **Deadlocks**: Two robots blocking each other in a narrow aisle
- **Congestion**: Too many robots converging on the same area

Traffic management approaches range from simple (first-come-first-
served at intersections) to sophisticated (centralized multi-agent
path planning that optimizes globally for throughput).

### Policy management

Each robot runs an AI policy (a VLA model) that determines how it
perceives and acts. The fleet manager controls which policy version
each robot runs:

- **Promotion**: Deploy a new policy version to a subset of the
  fleet for validation, then roll out to all robots.
- **Rollback**: Revert to a previous policy version if the new one
  causes degraded performance or safety concerns.
- **Per-site versioning**: Different sites may run different policy
  versions based on their specific environment or validation status.

Policy management through GitOps means promotions are git commits,
rollbacks are git reverts, and the audit trail is git history.

### Anomaly detection

The fleet manager monitors telemetry for anomalies:

- **Task performance**: A robot that consistently takes longer than
  expected on a task type may have a mechanical issue or a policy
  problem.
- **Safety metrics**: Anomaly scores from perception models that
  indicate potential hazards (unexpected obstacles, personnel in
  restricted zones).
- **Fleet patterns**: Aggregate metrics that reveal systemic issues
  (all robots slowing in a particular zone, suggesting a floor
  condition or lighting change).

When anomalies exceed thresholds, the fleet manager can trigger
automated responses: rerouting robots, pausing operations in an
area, or initiating a policy rollback.

## Fleet messaging patterns

Fleet systems are inherently event-driven. Robots emit telemetry.
Cameras publish frames. Managers publish missions. Safety systems
publish alerts. The messaging infrastructure must handle these streams
reliably.

### Event-driven architecture with Kafka

Apache Kafka (or AMQ Streams in the Red Hat ecosystem) is the standard
messaging backbone for fleet systems:

- **Topic-per-concern**: Separate topics for telemetry, missions,
  safety alerts, camera feeds, and events. This provides isolation
  and independent scaling.
- **Retention**: Messages are retained for a configurable period,
  enabling replay and forensic analysis.
- **Consumer groups**: Multiple consumers process the same topic
  independently — the fleet manager, the monitoring system, and the
  analytics pipeline all read from the same telemetry topic.
- **Cross-cluster federation**: Kafka MirrorMaker 2 replicates topics
  between spoke clusters and the hub, enabling centralized analytics
  over distributed data.

### Topic design for fleets

A common topic structure for a multi-site robot fleet:

```
fleet.telemetry          — Robot pose, battery, task status
fleet.missions           — Mission assignments and completions
fleet.events             — Fleet-level events (policy changes, mode switches)
fleet.safety.alerts      — Safety system alerts (obstructions, zone violations)
warehouse.cameras.{id}   — Camera frame references per camera
mes.orders               — Work orders from manufacturing systems
```

Per-site topics replicate the same structure with a site prefix
(e.g., `factory-a.telemetry`, `factory-b.telemetry`), enabling
site-level isolation with hub-level aggregation via MirrorMaker.

## Multi-site fleet orchestration

When the fleet spans multiple facilities, additional concerns emerge:

### Centralized vs. distributed control

- **Centralized**: A single fleet manager at the hub makes all
  decisions. Simpler to implement, but depends on hub connectivity
  and adds latency for edge decisions.
- **Distributed**: Each site has a local dispatcher that handles
  real-time mission execution. The hub provides fleet-wide
  coordination, policy management, and analytics.
- **Hybrid** (most common): Local dispatchers handle real-time
  operations. The hub handles cross-site optimization, policy
  promotion, and anomaly response. This is the hub-spoke pattern
  from the [Edge Computing chapter](06-edge-computing.md).

### Policy promotion across sites

Rolling out a new robot policy across a multi-site fleet:

1. **Train and validate** the new policy at the hub.
2. **Deploy to one site** (canary) via GitOps.
3. **Monitor** canary site performance metrics for a validation period.
4. **Promote to remaining sites** via ApplicationSet fan-out.
5. **Monitor** fleet-wide for regression.
6. **Rollback** any site that shows degraded performance.

ACM policies ensure that every site meets baseline requirements
(security, compliance, configuration) regardless of which policy
version they are running.

## Human-in-the-loop governance

In regulated environments, AI systems cannot make all decisions
autonomously. A human-in-the-loop (HIL) governance layer provides
oversight:

- **Read-only operations** (querying fleet status, viewing telemetry)
  proceed without approval.
- **State-modifying operations** (promoting a policy, changing a safety
  threshold, deploying a new model) require human approval.

The approval mechanism can be as simple as a PR review (the GitOps
pattern: AI proposes a change as a PR, human reviews and merges) or
as sophisticated as a dedicated approval interface with blast-radius
analysis, provenance chain, and audit binding.

This governance layer sits on the management path, not the control
path — it does not add latency to the robot's real-time perception-
action loop. A robot continues operating with its current policy while
awaiting approval for a change.

## Key takeaways

- Fleet management coordinates multiple robots for efficient,
  collision-free operation — analogous to container orchestration but
  in the physical domain.
- Core functions: mission dispatch, traffic management, policy
  management, and anomaly detection.
- Event-driven architecture (Kafka) provides the messaging backbone
  for fleet telemetry, missions, and safety alerts.
- Multi-site fleets use the hub-spoke pattern with local dispatchers
  and centralized policy management.
- Human-in-the-loop governance ensures that AI-driven changes to fleet
  operations go through human review — on the management path, never
  on the control path.

## Further reading

- Wurman, P.R., D'Andrea, R., & Mountz, M. (2008). "Coordinating
  Hundreds of Cooperative, Autonomous Vehicles in Warehouses."
  *AI Magazine*, 29(1). — The Kiva Systems paper describing the
  original Amazon robotics fleet architecture.
- [AMQ Streams (Strimzi)](https://strimzi.io/) — Kafka on Kubernetes,
  the open-source basis for Red Hat AMQ Streams.
- [Red Hat Advanced Cluster Management](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/) —
  Multi-cluster governance and policy management.
