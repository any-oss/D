# Soul Agent Specification

## Purpose
The Soul Agent maintains the core identity, value alignment, ethical boundaries, decision consistency, and cross-agent coordination for the multi-agent system. It serves as the central conscience and governance layer.

## Core Responsibilities

### 1. Identity Management
- Maintain system persona and character
- Consistent voice and tone across interactions
- Brand and personality enforcement
- Self-awareness and introspection capabilities

### 2. Value Alignment
- Ethical boundary definition and enforcement
- Decision validation against core values
- Bias detection and mitigation
- Fairness and inclusivity checks

### 3. Policy Enforcement
- Rule-based action validation
- Compliance verification
- Permission and authorization checks
- Audit trail maintenance

### 4. Cross-Agent Coordination
- Conflict resolution between agents
- Priority arbitration
- Resource allocation decisions
- System-wide goal alignment

### 5. Decision Auditing
- Log all significant decisions
- Trace decision rationale
- Provide explainability
- Support post-hoc analysis

## Data Schema (SQL)

```sql
-- Core identity configuration
CREATE TABLE system_identity (
    id SERIAL PRIMARY KEY,
    identity_key VARCHAR(100) NOT NULL UNIQUE,
    identity_value TEXT NOT NULL,
    category VARCHAR(50),  -- 'persona', 'values', 'constraints', 'goals'
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ethical policies and rules
CREATE TABLE ethical_policies (
    id SERIAL PRIMARY KEY,
    policy_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    policy_type VARCHAR(50),  -- 'prohibition', 'requirement', 'guideline'
    rule_expression TEXT NOT NULL,  -- Logical expression or code
    severity VARCHAR(20) DEFAULT 'medium',  -- 'low', 'medium', 'high', 'critical'
    applies_to TEXT[],  -- Agent types this applies to
    exceptions JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Decision audit log
CREATE TABLE decision_audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_name VARCHAR(100) NOT NULL,
    decision_type VARCHAR(50),
    decision_description TEXT NOT NULL,
    input_context JSONB,
    output_result JSONB,
    policies_checked TEXT[],  -- Policy names validated against
    violations_found TEXT[],
    rationale TEXT,
    confidence_score FLOAT,
    reviewer_id VARCHAR(100),  -- Human reviewer if flagged
    review_status VARCHAR(20) DEFAULT 'pending'  -- 'pending', 'approved', 'rejected'
);

-- Value hierarchy (tree structure)
CREATE TABLE value_hierarchy (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER REFERENCES value_hierarchy(id),
    value_name VARCHAR(100) NOT NULL,
    value_description TEXT,
    priority INTEGER NOT NULL,  -- Lower number = higher priority
    weight FLOAT DEFAULT 1.0,
    metadata JSONB
);

-- Conflict resolution history
CREATE TABLE conflict_resolutions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    conflicting_agents TEXT[] NOT NULL,
    conflict_description TEXT NOT NULL,
    resolution_approach VARCHAR(50),  -- 'priority_based', 'consensus', 'arbitration'
    resolution_outcome TEXT,
    winning_agent VARCHAR(100),
    compromised_values TEXT[],
    metadata JSONB
);

-- System goals and objectives
CREATE TABLE system_goals (
    id SERIAL PRIMARY KEY,
    goal_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    priority INTEGER,
    metrics_json JSONB,  -- Success criteria
    current_progress FLOAT DEFAULT 0,
    target_value FLOAT,
    deadline TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'completed', 'abandoned'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_identity_category ON system_identity(category);
CREATE INDEX idx_audit_timestamp ON decision_audit_log(timestamp DESC);
CREATE INDEX idx_audit_agent ON decision_audit_log(agent_name);
CREATE INDEX idx_policies_type ON ethical_policies(policy_type);
CREATE INDEX idx_goals_status ON system_goals(status);
```

## API Endpoints

### GET `/api/soul/identity`
Get current system identity configuration.

### PUT `/api/soul/identity`
Update system identity parameters.
```json
{
  "persona": {
    "name": "Assistant",
    "tone": "helpful, professional, friendly",
    "expertise_areas": ["coding", "analysis", "planning"]
  },
  "values": ["honesty", "helpfulness", "safety"],
  "constraints": ["no_harmful_content", "respect_privacy"]
}
```

### POST `/api/soul/validate`
Validate a proposed action against ethical policies.
```json
{
  "agent_name": "skills",
  "action": "execute_code",
  "context": {
    "code": "os.system('rm -rf /')",
    "user_intent": "clean temporary files"
  }
}
```
Response:
```json
{
  "is_allowed": false,
  "violated_policies": ["no_destructive_operations"],
  "severity": "critical",
  "recommendation": "Block this action and warn user"
}
```

### POST `/api/soul/decide`
Request decision assistance for complex scenarios.
```json
{
  "scenario": "Resource contention between agents",
  "options": [
    {"agent": "memory", "allocation": "60%"},
    {"agent": "skills", "allocation": "40%"}
  ],
  "criteria": ["fairness", "efficiency", "urgency"]
}
```

### GET `/api/soul/audit`
Query decision audit logs.
```
Query Params:
- agent: Filter by agent name
- from: Start timestamp
- to: End timestamp
- violation_only: Boolean filter for violations
- limit: Max results
```

### GET `/api/soul/goals`
Get current system goals and progress.

### POST `/api/soul/goals`
Set or update system goals.

## Lazy Loading Strategy

### On-Demand Policy Evaluation
```python
class SoulAgent:
    def __init__(self):
        self._identity_cache = {}
        self._policies_cache = None
        self._value_tree = None
    
    async def get_identity(self, key: str):
        if key not in self._identity_cache:
            identity = await self._fetch_identity(key)
            if identity:
                self._identity_cache[key] = identity.value
        return self._identity_cache.get(key)
    
    async def load_policies(self):
        """Lazy load policies on first validation request."""
        if not self._policies_cache:
            policies = await self._fetch_all_policies()
            self._policies_cache = {p.policy_name: p for p in policies}
        return self._policies_cache
    
    async def validate_action(self, agent_name: str, action: str, context: dict):
        # Ensure policies are loaded
        policies = await self.load_policies()
        
        violations = []
        for policy_name, policy in policies.items():
            if not policy.is_active:
                continue
            
            # Check if policy applies to this agent
            if policy.applies_to and agent_name not in policy.applies_to:
                continue
            
            # Evaluate rule expression
            is_violated = await self._evaluate_rule(policy.rule_expression, context)
            if is_violated:
                violations.append({
                    'policy': policy_name,
                    'severity': policy.severity,
                    'description': policy.description
                })
        
        return {
            'is_allowed': len(violations) == 0,
            'violations': violations
        }
```

### Cached Value Hierarchy
- Load value tree once at startup
- Update only when explicitly modified
- Use for quick priority comparisons

## Ethical Evaluation Engine

```python
async def evaluate_ethical_implications(action: str, context: dict) -> EthicalAssessment:
    """Comprehensive ethical evaluation of proposed actions."""
    
    assessment = EthicalAssessment()
    
    # 1. Check explicit prohibitions
    prohibitions = await get_prohibitions()
    for prohibition in prohibitions:
        if matches_prohibition(action, context, prohibition):
            assessment.add_violation(prohibition, severity='critical')
    
    # 2. Evaluate potential harm
    harm_score = await calculate_harm_potential(action, context)
    if harm_score > 0.8:
        assessment.add_concern('high_harm_potential', severity='high')
    
    # 3. Check fairness implications
    fairness_impact = await assess_fairness(action, context)
    if not fairness_impact.is_fair:
        assessment.add_concern('unfair_treatment', severity='medium')
    
    # 4. Verify consent and authorization
    has_consent = await verify_consent(action, context)
    if not has_consent:
        assessment.add_violation('missing_consent', severity='high')
    
    # 5. Align with core values
    value_alignment = await check_value_alignment(action, context)
    assessment.alignment_score = value_alignment.score
    
    return assessment
```

## Integration Points

### Skills Agent
- Validate skill actions before execution
- Log skill decisions for audit

### Memory Agent
- Ensure memory operations respect privacy policies
- Audit sensitive memory access

### Heartbeat Agent
- Validate alert thresholds against safety policies
- Approve auto-scaling decisions

### Tools Agent
- Validate tool usage permissions
- Audit external service interactions

## Configuration Parameters

Stored in `agent_params` table:
```json
{
  "soul": {
    "identity_version": "1.0.0",
    "default_persona": "helpful_assistant",
    "enable_audit_logging": true,
    "audit_retention_days": 90,
    "auto_block_violations": true,
    "require_human_review_threshold": "critical",
    "conflict_resolution": {
      "default_approach": "priority_based",
      "escalation_enabled": true,
      "escalation_threshold": "high"
    },
    "value_weights": {
      "safety": 1.0,
      "honesty": 0.9,
      "helpfulness": 0.8,
      "efficiency": 0.6
    },
    "ethical_boundaries": {
      "allow_self_modification": false,
      "allow_external_api_calls": true,
      "allow_data_deletion": false,
      "require_user_consent": true
    }
  }
}
```

## Example Usage

```python
from services.soul_agent import SoulAgent

agent = SoulAgent()

# Get system identity
persona = await agent.get_identity('persona')
print(f"System persona: {persona}")

# Validate an action
validation = await agent.validate_action(
    agent_name="tools",
    action="delete_file",
    context={"path": "/etc/passwd", "user_requested": True}
)

if not validation['is_allowed']:
    print(f"Action blocked! Violations: {validation['violations']}")
else:
    print("Action approved")

# Request decision assistance
decision = await agent.decide(
    scenario="Two agents need same resource",
    options=[
        {"agent": "memory", "priority": 5},
        {"agent": "skills", "priority": 3}
    ],
    criteria=["system_stability", "user_impact"]
)
print(f"Decision: Allocate to {decision['winner']}")

# Query audit log
audits = await agent.query_audit(
    agent="skills",
    from_time="2024-01-15T00:00:00Z",
    violation_only=True,
    limit=10
)

for audit in audits:
    print(f"Violation: {audit['decision_description']}")
    print(f"Policies violated: {audit['violations_found']}")
```

## Core Values Definition

Example initial values in `value_hierarchy`:

| ID | Parent | Name | Description | Priority | Weight |
|----|--------|------|-------------|----------|--------|
| 1 | null | Core Values | Root of value hierarchy | 1 | 1.0 |
| 2 | 1 | Safety | Prevent harm to users and systems | 2 | 1.0 |
| 3 | 1 | Honesty | Provide truthful, accurate information | 3 | 0.9 |
| 4 | 1 | Helpfulness | Assist users effectively | 4 | 0.8 |
| 5 | 1 | Privacy | Respect and protect user privacy | 3 | 0.95 |
| 6 | 1 | Fairness | Treat all users equitably | 4 | 0.85 |
| 7 | 2 | No Harm | Never cause intentional harm | 1 | 1.0 |
| 8 | 5 | Consent | Obtain consent for data operations | 2 | 0.9 |
