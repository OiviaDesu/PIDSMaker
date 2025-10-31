# Documentation Policy

## Overview

This project maintains comprehensive documentation to ensure reproducibility, transparency, and academic rigor. **All documentation must be updated as development progresses**, not retroactively.

---

## Core Documentation Files

### 1. Development History (`docs/DEVELOPMENT_HISTORY.md`)

**Purpose**: Complete chronicle of all development activities, bugs, optimizations, and findings.

**Update Trigger**: After **every significant development activity**
- New feature implementation
- Bug discovery and fix
- Configuration changes
- Job submissions and results
- Performance optimizations
- Paper alignment corrections

**Required Information**:
- Date and time of activity
- Commit hash(es) involved
- Detailed description of changes
- Root cause analysis (for bugs)
- Impact assessment (metrics before/after)
- Lessons learned

**Template for Bug Entries**:
```markdown
### Bug #X: [Title]
**Date**: YYYY-MM-DD
**Severity**: Critical/High/Medium/Low
**Job IDs**: [job IDs that exposed the bug]
**Symptom**: [What went wrong]
**Root Cause**: [Why it happened]
**Fix**: [What was changed]
**Commits**: [commit hashes]
**Impact**: [Metrics before → after]
**Lessons**: [Key takeaways]
```

---

### 2. Presentation Slides (`presentationSlide.md`)

**Purpose**: Up-to-date project overview for demonstrations and academic presentations.

**Update Trigger**: After **major milestones**
- Phase completions (Phase 1, Phase 2, etc.)
- Significant results obtained
- New datasets or models added
- Critical bugs fixed that change results
- Before scheduled presentations

**Sections to Update**:
- **Results**: Always reflect latest validated metrics
- **Challenges & Solutions**: Add new bugs and their fixes
- **Timeline**: Update progress indicators
- **Future Work**: Adjust based on current priorities
- **Backup Slides**: Add technical details as needed

**Best Practices**:
- Keep slides concise (17 main slides + backup)
- Update charts/graphs with latest data
- Use consistent formatting and terminology
- Cite paper sections for paper-faithful claims
- Include commit hashes for reproducibility

---

### 3. Preliminary Report (`PRELIMINARY_REPORT.md`)

**Purpose**: Comprehensive academic report documenting progress, methodology, and findings.

**Update Trigger**: **Weekly** or after **significant milestones**
- End of each week (Friday)
- After major bug fixes
- After completing experimental batches
- Before academic submissions or demos
- When new results become available

**Sections to Update**:

**Daily Progress Tracking**:
- Add new day entries with all commits
- Include detailed activity descriptions
- Document challenges encountered
- Record solutions implemented

**Experimental Results**:
- Update results tables with latest metrics
- Add validation status indicators
- Include paper comparison data
- Note any unexpected findings

**Bug Tracking**:
- Add new bugs to Appendix A
- Update bug status (Fixed/In Progress/Pending)
- Include impact metrics

**Job Statistics**:
- Update job counts and success rates
- Add new job submissions
- Track compute resource usage

**Team Collaboration**:
- Document meetings and decisions
- Add code review notes
- Include communication artifacts

---

## Documentation Workflow

### Before Starting Work

1. **Review current documentation** to understand context
2. **Check DEVELOPMENT_HISTORY.md** for recent bugs and fixes
3. **Note the starting state** (baseline metrics, current issues)

### During Development

1. **Keep a development log** in your working notes
2. **Document decisions** as you make them (why not how)
3. **Screenshot/save error messages** immediately when bugs occur
4. **Record commit hashes** for all significant changes

### After Completing Work

1. ✅ **Update DEVELOPMENT_HISTORY.md** FIRST
   - Add chronological entry with full context
   - Include all relevant commit hashes
   - Document bugs with root cause analysis
   - Add before/after metrics

2. ✅ **Update PRELIMINARY_REPORT.md**
   - Add to daily progress tracking
   - Update experimental results if applicable
   - Add bugs to Appendix A
   - Update job statistics

3. ✅ **Update presentationSlide.md** (if milestone reached)
   - Refresh results slides
   - Add new challenges/solutions
   - Update timeline and progress indicators

4. ✅ **Commit documentation with descriptive message**
   ```bash
   git add docs/DEVELOPMENT_HISTORY.md PRELIMINARY_REPORT.md presentationSlide.md
   git commit -m "docs: Update after [activity] - [key finding/fix]"
   git push origin supercomputer
   ```

---

## Commit Message Guidelines

**For Documentation Updates**:
```
docs: [Brief summary of what was documented]

- Updated DEVELOPMENT_HISTORY.md: [specific changes]
- Updated PRELIMINARY_REPORT.md: [specific changes]
- Updated presentationSlide.md: [specific changes]
```

**Examples**:
```
docs: Document Bug #11 storage optimization and job resubmission

- Updated DEVELOPMENT_HISTORY.md: Added Bug #11 with root cause analysis
- Updated PRELIMINARY_REPORT.md: Added Oct 31 evening session, updated job stats
- Updated presentationSlide.md: Added storage optimization to challenges slide
```

```
docs: Weekly progress update (Week 3, Nov 1-7)

- Updated DEVELOPMENT_HISTORY.md: Week 3 summary with 8 commits
- Updated PRELIMINARY_REPORT.md: Added Week 3 section, updated results table
- Updated presentationSlide.md: Refreshed results with Phase 2 metrics
```

---

## Review Checklist

Before pushing any code changes, verify:

- [ ] **DEVELOPMENT_HISTORY.md updated** with chronological entry
- [ ] **Bug tracking complete** (if bug fixed): symptom, root cause, fix, impact
- [ ] **Commit hashes included** in documentation
- [ ] **PRELIMINARY_REPORT.md updated** with daily progress entry
- [ ] **Job statistics current** (if jobs submitted/completed)
- [ ] **Presentation slides updated** (if milestone reached)
- [ ] **All metrics are latest** (no stale data in docs)
- [ ] **Paper citations included** (for paper-faithful claims)
- [ ] **Lessons learned documented** (for significant bugs/optimizations)

---

## Why This Matters

### Academic Integrity
- Complete audit trail of all development decisions
- Transparent documentation of bugs and fixes
- Reproducible research with full context

### Knowledge Transfer
- Future team members can understand project evolution
- Detailed bug analysis prevents repeat mistakes
- Clear documentation of "why" decisions were made

### Progress Tracking
- Daily progress visible to stakeholders
- Easy to generate weekly/monthly summaries
- Clear demonstration of development velocity

### Presentation Readiness
- Always have up-to-date slides for demos
- No scrambling to recreate history before presentations
- Accurate metrics for academic submissions

---

## Anti-Patterns to Avoid

❌ **DON'T**: Batch update docs at the end of the week
✅ **DO**: Update docs immediately after each significant activity

❌ **DON'T**: Write vague entries like "Fixed some bugs"
✅ **DO**: Write detailed entries with root cause and impact

❌ **DON'T**: Forget to include commit hashes
✅ **DO**: Always link commits to documentation entries

❌ **DON'T**: Update only one documentation file
✅ **DO**: Update all relevant docs (history, report, slides)

❌ **DON'T**: Remove old information from history
✅ **DO**: Keep complete chronological record (append only)

❌ **DON'T**: Document only successes
✅ **DO**: Document failures, dead ends, and lessons learned

---

## Templates

### Daily Progress Entry Template

```markdown
### Day X (Month DD, YYYY) - [Brief Theme]

**Context**: [What was the starting situation]

**Accomplishments** (N commits):
- ✅ [Achievement 1]
- ✅ [Achievement 2]
- ⚠️ [Issue discovered]

**Commits**:
- `hash`: [Description]
- `hash`: [Description]

**Key Results**:
[Any metrics, findings, or insights]

**Challenges**:
[Problems encountered]

**Solutions**:
[How problems were resolved]

**Time**: [Estimated hours spent]
```

### Bug Entry Template

```markdown
### Bug #X: [Concise Title]

**Date**: YYYY-MM-DD HH:MM
**Severity**: [Critical/High/Medium/Low]
**Status**: ✅ Fixed / 🔄 In Progress / ❌ Blocked

**Discovery**:
- Job ID: [job that exposed it]
- Symptom: [What went wrong]
- Error message: `[exact error if applicable]`

**Root Cause Analysis**:
[Detailed explanation of why bug occurred]

**Fix Applied**:
- File(s) modified: `[list files]`
- Changes: [What was changed]
- Commits: [`hash1`, `hash2`]

**Impact**:
- Before: [Metrics/behavior before fix]
- After: [Metrics/behavior after fix]
- Improvement: [Quantify the improvement]

**Validation**:
- Job ID: [job that validates fix]
- Status: [Pending/Running/Completed]
- Results: [If available]

**Lessons Learned**:
- [Key takeaway 1]
- [Key takeaway 2]
```

---

## Enforcement

This documentation policy is **mandatory** for all development work. Pull requests and commits that don't include appropriate documentation updates will be flagged during code review.

**Automation**:
- CI/CD checks verify docs are updated in same commit as code changes
- Pre-commit hooks remind to update documentation
- Weekly automated reports summarize undocumented changes

**Accountability**:
- All team members responsible for documenting their own work
- Weekly documentation review in team meetings
- Documentation quality considered in project assessments

---

## Questions?

If unsure about what to document or where to put it:
1. **When in doubt, document it** - more context is better than less
2. **Ask in team channel** - get clarity before proceeding
3. **Check existing entries** - follow established patterns
4. **Refer to this policy** - covers most scenarios

---

**Last Updated**: October 31, 2025  
**Version**: 1.0  
**Maintainer**: Development Team
