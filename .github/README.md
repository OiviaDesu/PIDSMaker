# GitHub Repository Configuration

This directory contains GitHub-specific configuration files and templates to ensure consistent development practices and comprehensive documentation.

## Files Overview

### [AI_AGENT_INSTRUCTIONS.md](AI_AGENT_INSTRUCTIONS.md) **[CRITICAL] READ FIRST**

**Mandatory reading for all AI agents and automated tools.**

Defines strict requirements for:
- NO EMOJIS in any code or documentation files
- Defensive thinking protocol (assume worst case first)
- High-stakes mindset (project shutdown risk)
- Success criteria (only celebrate verified results)
- Paper alignment verification procedures
- Bug documentation standards

**Key Principle**: This project operates under survival conditions. Every job could be the last chance.

### [DOCUMENTATION_POLICY.md](DOCUMENTATION_POLICY.md) **[REQUIRED] START HERE**

**Required reading for all contributors.**

Comprehensive policy for maintaining project documentation. Defines:
- What to document (development history, bugs, results)
- When to update (after every significant change)
- How to document (templates and examples)
- Why it matters (academic integrity, reproducibility)

**Key Principle**: Documentation is updated **as you go**, not retroactively.

### [pull_request_template.md](pull_request_template.md)

Automatic template for all pull requests. Includes:
- Checklist for documentation updates
- Impact assessment section
- Testing verification
- Reminder to consult documentation policy

### [.gitmessage](.gitmessage)

Commit message template with examples. To use:

```bash
git config commit.template .github/.gitmessage
```

Helps write comprehensive commit messages with:
- Proper type prefixes (feat, fix, docs, etc.)
- Bug fix documentation (root cause, impact)
- Documentation update tracking
- Related references (job IDs, paper citations)

### [workflows/](workflows/)

CI/CD automation workflows:
- Documentation checks
- Test automation
- Deployment pipelines

### [hooks/](hooks/)

Git hooks for automated enforcement:
- `pre-commit-no-emoji.sh`: Blocks commits containing emojis

**To install hooks:**
```bash
# Install the emoji checker
cp .github/hooks/pre-commit-no-emoji.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Quick Reference

### For Every Code Change:

1. [OK] Write code
2. [OK] Update `docs/DEVELOPMENT_HISTORY.md`
3. [OK] Update `PRELIMINARY_REPORT.md`
4. [OK] Update `presentationSlide.md` (if milestone)
5. [OK] Commit all together with descriptive message
6. [OK] Push to remote

### For Bug Fixes:

1. [OK] Fix the bug
2. [OK] Document in `DEVELOPMENT_HISTORY.md`:
   - Bug number and title
   - Root cause analysis
   - Before/after metrics
   - Lessons learned
3. [OK] Add to `PRELIMINARY_REPORT.md` Appendix A
4. [OK] Submit validation job
5. [OK] Commit with bug number in message

### For New Features:

1. [OK] Implement feature
2. [OK] Document in `DEVELOPMENT_HISTORY.md` with paper citations
3. [OK] Update `PRELIMINARY_REPORT.md` daily progress
4. [OK] Update `presentationSlide.md` if milestone reached
5. [OK] Write tests (if applicable)
6. [OK] Submit validation jobs
7. [OK] Commit with descriptive message

## Templates

### Bug Entry Template (for DEVELOPMENT_HISTORY.md)

```markdown
### Bug #X: [Title]
**Date**: YYYY-MM-DD
**Severity**: Critical/High/Medium/Low
**Symptom**: [What went wrong]
**Root Cause**: [Why it happened]
**Fix**: [What was changed]
**Commits**: [hashes]
**Impact**: [Before → After]
**Lessons**: [Key takeaways]
```

### Daily Progress Entry Template (for PRELIMINARY_REPORT.md)

```markdown
### Day X (Month DD, YYYY) - [Brief Theme]

**Context**: [Starting situation]

**Accomplishments** (N commits):
- ✅ [Achievement 1]

**Commits**:
- `hash`: [Description]

**Challenges & Solutions**:
[Problems and how they were resolved]
```

## Enforcement

- **CI checks**: Verify documentation is updated
- **Pre-commit hooks**: Remind to update docs
- **PR reviews**: Check documentation quality
- **Weekly reports**: Summarize undocumented changes

## Anti-Patterns to Avoid

[FAIL] Batch update docs at end of week  
[OK] Update docs immediately after each activity

[FAIL] Vague entries: "Fixed some bugs"  
[OK] Detailed entries with root cause and impact

[FAIL] Forget commit hashes  
[OK] Always link commits to documentation

[FAIL] Update only one doc file  
[OK] Update all relevant docs (history, report, slides)

## Questions?

See [DOCUMENTATION_POLICY.md](DOCUMENTATION_POLICY.md) for complete details, or ask in project discussions.

---

**Remember**: Good documentation is not extra work—it's how we ensure reproducible, transparent, and academically rigorous research.
