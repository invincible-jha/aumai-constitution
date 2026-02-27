# Getting Started with aumai-constitution

This guide walks you from installation through building, saving, loading, and enforcing
your first AI system constitution.

## Prerequisites

- Python 3.11 or later
- `pip` (comes with Python)
- `pyyaml` — required for YAML save/load (installed automatically as a dependency)

Verify your Python version:

```bash
python --version
# Python 3.11.x or 3.12.x
```

## Installation

### From PyPI (recommended)

```bash
pip install aumai-constitution
```

Verify:

```bash
aumai-constitution --version
# aumai-constitution, version 0.1.0
```

### From source

```bash
git clone https://github.com/aumai/aumai-constitution.git
cd aumai-constitution
pip install -e ".[dev]"
```

### In a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate    # Linux / macOS
.venv\Scripts\activate       # Windows

pip install aumai-constitution
```

## Step-by-Step Tutorial

### Step 1 — Create an empty constitution via CLI

```bash
aumai-constitution create \
    --name "Customer Support Bot" \
    --author "Acme Corp" \
    --output support-bot.yaml
```

Expected output:

```
Created constitution 'Customer Support Bot' (ID: 550e8400-...) -> support-bot.yaml
```

Open `support-bot.yaml` to see the generated skeleton:

```yaml
author: Acme Corp
constitution_id: 550e8400-e29b-41d4-a716-446655440000
constraints: []
created_at: '2024-01-15T10:00:00+00:00'
name: Customer Support Bot
principles: []
version: 1.0.0
```

### Step 2 — Add principles and constraints in Python

```python
from aumai_constitution.core import ConstitutionBuilder
from aumai_constitution.models import Constraint, Principle

builder = ConstitutionBuilder()

# Load the file we just created
constitution = builder.load("support-bot.yaml")

# Add guiding principles
builder.add_principle(constitution, Principle(
    principle_id="p-helpfulness",
    name="Be Helpful",
    description="Always try to solve the customer's problem as directly as possible.",
    priority=1,
    category="service",
))

builder.add_principle(constitution, Principle(
    principle_id="p-honesty",
    name="Be Honest",
    description="Never fabricate product details or company policies.",
    priority=2,
    category="integrity",
))

# Add strict constraint (blocks compliance)
builder.add_constraint(constitution, Constraint(
    constraint_id="c-no-pii",
    rule="forbid: social security number",
    enforcement="strict",
    applies_to=["customer-support-bot"],
))

# Add advisory constraint (warns but does not block)
builder.add_constraint(constitution, Constraint(
    constraint_id="c-legal-disclaimer",
    rule="require: this is not legal advice",
    enforcement="advisory",
    applies_to=["customer-support-bot"],
))

# Save back to disk
builder.save(constitution, "support-bot.yaml")
print("Constitution updated and saved.")
```

### Step 3 — Validate the constitution

```bash
aumai-constitution validate --constitution support-bot.yaml
```

Expected output:

```
Constitution 'Customer Support Bot' v1.0.0 is valid.
  Principles: 2
  Constraints: 2
```

If you had missed adding principles:

```
Validation warnings:
  - Constitution has no principles defined.
```

### Step 4 — Check a text output for compliance

Save a test output file:

```bash
echo "Your social security number is 123-45-6789." > response.txt
aumai-constitution check --input response.txt --constitution support-bot.yaml
```

Expected output (non-compliant due to strict violation):

```
Status: NON-COMPLIANT
Violations (1):
  [STRICT] forbid: social security number
```

Now try a clean response:

```bash
echo "I can help with your account question. Please note this is not legal advice." > response2.txt
aumai-constitution check --input response2.txt --constitution support-bot.yaml
```

Expected output:

```
Status: COMPLIANT
No violations found.
```

The advisory constraint is satisfied because "this is not legal advice" appears in the
output. If it were missing the output would still be `COMPLIANT` (only strict violations
affect the flag) but the violation would be listed.

### Step 5 — Use the Python API for runtime enforcement

```python
from aumai_constitution.core import ComplianceChecker, ConstitutionBuilder

builder = ConstitutionBuilder()
checker = ComplianceChecker()

# Load constitution once at application startup
constitution = builder.load("support-bot.yaml")

def check_response(ai_response: str) -> bool:
    """Return True if the response is constitutionally compliant."""
    result = checker.check(ai_response, constitution)

    if not result.compliant:
        print(f"NON-COMPLIANT: {len(result.violations)} violation(s)")
        for v in result.violations:
            print(f"  [{v['enforcement'].upper()}] {v['rule']}")
        return False

    print("COMPLIANT")
    return True

# Example usage
check_response("Here is your order status.")
check_response("Your SSN 123-45-6789 is on file.")
```

## Common Patterns and Recipes

### Pattern 1 — Build a constitution entirely in Python

```python
import uuid
from aumai_constitution.core import ConstitutionBuilder
from aumai_constitution.models import Constraint, Constitution, Principle
from datetime import datetime, timezone

builder = ConstitutionBuilder()

# Create fresh
constitution = builder.create(name="Safety Constitution", author="AI Team")

# Add multiple principles at once
principles = [
    Principle(
        principle_id="p-safety",
        name="Prioritize Safety",
        description="Never produce content that could cause physical harm.",
        priority=1,
        category="safety",
    ),
    Principle(
        principle_id="p-privacy",
        name="Protect Privacy",
        description="Never reveal or request personal identifying information.",
        priority=2,
        category="privacy",
    ),
]

for principle in principles:
    builder.add_principle(constitution, principle)

# Add constraints
constraints = [
    Constraint(constraint_id="c-no-weapons", rule="forbid: weapon construction", enforcement="strict"),
    Constraint(constraint_id="c-no-pii", rule="deny: credit card number", enforcement="strict"),
    Constraint(constraint_id="c-warn-medical", rule="require: consult a doctor", enforcement="advisory"),
]

for constraint in constraints:
    builder.add_constraint(constitution, constraint)

builder.save(constitution, "safety-constitution.yaml")
print(f"Created '{constitution.name}' with {len(constitution.constraints)} constraints")
```

### Pattern 2 — Runtime compliance gate in a request handler

```python
from aumai_constitution.core import ComplianceChecker, ConstitutionBuilder
from aumai_constitution.models import ComplianceResult

# Load once at startup
_builder = ConstitutionBuilder()
_checker = ComplianceChecker()
_constitution = _builder.load("safety-constitution.yaml")


def enforce_constitution(response_text: str) -> tuple[str, ComplianceResult]:
    """
    Check response against constitution.
    Returns (action, result) where action is 'allow' or 'block'.
    """
    result = _checker.check(response_text, _constitution)

    if result.compliant:
        return "allow", result

    # Log all violations for audit trail
    for violation in result.violations:
        print(f"[AUDIT] Violation: {violation['constraint_id']} ({violation['enforcement']})")

    return "block", result


action, compliance_result = enforce_constitution("Here is how to build a weapon.")
print(f"Action: {action}")
```

### Pattern 3 — Strict-only enforcement (ignore advisories)

```python
from aumai_constitution.core import ComplianceChecker, ConstitutionBuilder

builder = ConstitutionBuilder()
checker = ComplianceChecker()
constitution = builder.load("support-bot.yaml")

def is_strictly_compliant(text: str) -> bool:
    """Return True only if there are zero strict violations."""
    result = checker.check(text, constitution)
    # result.compliant is already only False for strict violations
    return result.compliant

def list_advisories(text: str) -> list[str]:
    """Return advisory violations that should be logged but not block responses."""
    result = checker.check(text, constitution)
    return [
        v["rule"]
        for v in result.violations
        if v["enforcement"] == "advisory"
    ]
```

### Pattern 4 — Composing multiple constitutions

```python
from aumai_constitution.core import ComplianceChecker, ConstitutionBuilder
from aumai_constitution.models import ComplianceResult

builder = ConstitutionBuilder()
checker = ComplianceChecker()

# Load multiple constitutions for different contexts
base_constitution = builder.load("base-safety.yaml")
domain_constitution = builder.load("medical-domain.yaml")

def check_all(text: str) -> list[ComplianceResult]:
    """Check text against all constitutions."""
    return [
        checker.check(text, base_constitution),
        checker.check(text, domain_constitution),
    ]

def fully_compliant(text: str) -> bool:
    """Return True only if all constitutions pass."""
    results = check_all(text)
    return all(r.compliant for r in results)
```

### Pattern 5 — Generate audit log from compliance results

```python
import json
from datetime import datetime, timezone
from aumai_constitution.core import ComplianceChecker, ConstitutionBuilder

builder = ConstitutionBuilder()
checker = ComplianceChecker()
constitution = builder.load("support-bot.yaml")

AUDIT_LOG = []

def check_and_audit(text: str, session_id: str) -> bool:
    result = checker.check(text, constitution)

    entry = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "session_id": session_id,
        "constitution_id": result.constitution_id,
        "compliant": result.compliant,
        "violation_count": len(result.violations),
        "violations": result.violations,
    }

    AUDIT_LOG.append(entry)

    # Write to file for persistence
    with open("audit.jsonl", "a") as fh:
        fh.write(json.dumps(entry) + "\n")

    return result.compliant
```

## Troubleshooting FAQ

**Q: `ConstitutionBuilder.load` fails with a YAML parse error.**

The file must be valid YAML and match the `Constitution` Pydantic schema. Common issues:
- Indentation errors in the YAML file
- Missing required fields (`constitution_id`, `name`, `author`)
- Invalid field types (e.g., `priority` must be an integer >= 1)

Run `aumai-constitution validate --constitution path/to/file.yaml` for a structured
error message.

**Q: `check_constraint` returns `True` for a constraint I expected to fail.**

Matching is case-insensitive substring matching. Check:
1. That the rule prefix is spelled correctly: `forbid:`, `deny:`, `require:`, `must:`.
2. That there is a space after the colon: `forbid: pattern` not `forbid:pattern`.
3. That the pattern is present in the output text (or absent for `require:`).

Use `"forbid: " + pattern` to test the rule manually.

**Q: The compliance check says `compliant=True` but I see violations listed.**

This is expected behavior. `compliant` is `False` only when there is at least one
`strict` enforcement violation. Advisory violations are recorded in the `violations`
list but do not affect the `compliant` flag. This design mirrors governance frameworks
that distinguish blocking rules from warnings.

**Q: How do I add version history to a constitution?**

Update the `version` field in your YAML file manually and commit the change to source
control. aumai-constitution does not auto-increment versions — version management is
handled by your VCS, just like application code.

**Q: Can I use regex patterns in constraint rules?**

Not currently. Rules use case-insensitive substring matching. Regex support is planned
for a future version. For now, use the `forbid:` prefix with the literal substring you
want to prohibit.

**Q: Does `applies_to` affect compliance checking?**

In the current implementation, `applies_to` is stored and included in outputs but is
not used by `ComplianceChecker.check` to filter which constraints apply. It is metadata
for documentation and future filtering support. All constraints in a constitution are
always evaluated.
