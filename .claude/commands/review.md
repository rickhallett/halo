# Adversarial Review (Orchestrated)

Run a full adversarial review cycle: blind review → handoff → targeted verification.

## Process

This review uses three rounds. The order matters: blind review MUST happen before the implementation model produces its handoff, otherwise the handoff framing contaminates the review.

### Round 1: Blind Review

Run `/review-blind` FIRST.

Approach the code fresh. Assume the author is overstating what the code proves. Document all findings.

You have not seen any author claims yet. This is intentional.

### Round 2: Handoff Generation

NOW produce the review handoff by running `/review-handoff`.

This documents what the implementation claims to do, where to look, and what it explicitly does NOT prove.

### Round 3: Targeted Verification

Run `/review-targeted` with the handoff as input.

Compare the handoff claims against:

1. What you found in the blind review
2. What the code actually demonstrates

Flag any discrepancies between the author's framing and your blind findings.

## Output

Produce a unified review report:

```markdown
# Adversarial Review Report

## Summary

[One paragraph: overall assessment, key risks, confidence level]

## Blind Review Findings

[Findings from Round 2, unfiltered]

## Handoff Verification

[Table from Round 3: claim verdicts]

## Discrepancies

[Where blind review contradicts or extends the handoff]

## Risk Assessment

| Risk              | Severity                 | Status                  |
| ----------------- | ------------------------ | ----------------------- |
| [identified risk] | CRITICAL/HIGH/MEDIUM/LOW | Open/Mitigated/Accepted |

## Recommendations

1. [Most important action]
2. ...

## Verdict

[ ] PASS — Implementation matches claims, risks acceptable
[ ] CONDITIONAL — Specific issues must be addressed
[ ] FAIL — Claims overstated or critical risks unaddressed
```

## Rules

1. **Order is mandatory.** Blind review → handoff → targeted. Never generate the handoff before blind review.

2. **Prefer skepticism.** "Partially true" over "confirmed" unless evidence is unambiguous.

3. **Name the non-claims.** What does this change explicitly NOT prove? The author should have said; verify they did.

4. **Discrepancies are signal.** If blind review found something the handoff omitted, that's information about handoff quality.

## When to Use

- After significant implementation work
- Before merging to main
- When claims about behavior need verification
- When you suspect the implementation model is pattern-matching rather than reasoning

## Limitations

This orchestration runs in a single context. The blind review genuinely happens before the handoff exists, so there's no contamination in that direction. However, the same model that did the implementation is doing the review — true adversarial review would use a separate model instance with no shared context.

This is a pragmatic approximation: better than self-certification, worse than independent review.
