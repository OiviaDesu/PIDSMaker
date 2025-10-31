# Contributing to PIDSMaker

Thank you for your interest in contributing to PIDSMaker! This document provides guidelines for contributing to the project.

## Quick Start

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. **Update all relevant documentation** (see [Documentation Policy](.github/DOCUMENTATION_POLICY.md))
5. Commit with descriptive messages (see [Commit Template](.github/.gitmessage))
6. Push to your fork
7. Open a Pull Request using the [PR template](.github/pull_request_template.md)

## ⚠️ Documentation Requirements

**All code changes MUST be accompanied by documentation updates.** This is not optional.

Before submitting any pull request, you must update:

### 1. Development History (`docs/DEVELOPMENT_HISTORY.md`)
- Add chronological entry with date and commit hash
- Include detailed description of changes
- Provide root cause analysis for bug fixes
- Document before/after metrics
- Add lessons learned

### 2. Preliminary Report (`PRELIMINARY_REPORT.md`)
- Update daily progress tracking
- Update experimental results (if applicable)
- Add bugs to Appendix A (if bug fix)
- Update job statistics
- Document team collaboration artifacts

### 3. Presentation Slides (`presentationSlide.md`) - If Milestone Reached
- Update results with latest metrics
- Add new challenges and solutions
- Update timeline and progress indicators
- Refresh future work section

**See [.github/DOCUMENTATION_POLICY.md](.github/DOCUMENTATION_POLICY.md) for complete requirements.**

## Contribution Guidelines

For detailed contribution guidelines, please visit:
- [Online Documentation](https://ubc-provenance.github.io/PIDSMaker/contributing/)
- [Documentation Policy](.github/DOCUMENTATION_POLICY.md) - **Required reading**

## Code Review Process

1. All PRs require documentation updates
2. PRs without documentation will be marked as incomplete
3. CI checks verify documentation is included
4. Maintainers review both code and documentation quality

## Setting Up Commit Template

Configure your local repository to use our commit message template:

```bash
git config commit.template .github/.gitmessage
```

This will help you write comprehensive commit messages that include all necessary context.

## Questions?

- Check the [Documentation Policy](.github/DOCUMENTATION_POLICY.md)
- Ask in project discussions
- Contact the maintainers

---

**Remember**: Documentation is not an afterthought—it's an integral part of every contribution.
