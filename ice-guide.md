# ICE Workflow Guide

## What is ICE?
ICE (Issue, Commit, Effort) is a system cooked up by Ric that analyzes your coding workflow to help you develop professional software development practices. It evaluates how well you plan, execute, and track your work. Eventually robots will do our coding, so the least we can do is cling onto the steering wheel! 🤖

## The 5 Pillars of Good Workflow

### 1. 📝 **Plan with Issues**
- Create one issue for each exercise or make your own plan!
- Use descriptive titles like "Exercise 1.3 -- Sum"
- **Why**: Planning helps you organize work and track progress

### 2. 💻 **Code Regularly**
- Make commits as you work on each issue
- Aim for at least 1 commit per issue (ideally more)
- Make meaningful commits that represent actual progress
- **Why**: Regular commits show consistent effort and provide backup points

### 3. ✅ **Complete Your Work**
- Close issues when you finish them
- Don't leave issues hanging open indefinitely
- **Why**: Completion demonstrates follow-through and organization

### 4. 🔗 **Link Commits to Issues**
- Reference issues in commit messages: "Work on #1", "Update #2"
- **Why**: This creates traceability between planning and execution

### 5. 🎯 **Use Closing Keywords**
- Close issues with commit messages: "Fixes #1", "Closes #2", "Resolves #3"
- **Why**: This automates issue management and shows completion

## Sample Workflow

```bash
# 1. Create issues for your exercises (on GitHub)
# Issue #1: "Exercise 1.1 -- Hello World"
# Issue #2: "Exercise 1.2 -- Arithmetic.java"
# etc.

# 2. Work on each issue with referenced commits
git commit -m "Start work on #1 - create HelloWorld.java"
git commit -m "Complete HelloWorld implementation #1"
git commit -m "Fixes #1 - HelloWorld working correctly"

# 3. Move to next issue
git commit -m "Begin #2 - create Arithmetic class"
git commit -m "Add sum method for #2"
git commit -m "Fixes #2 - Arithmetic class complete"
```

## ICE Classification Levels

- 🌟 **Workflow Master**: Excellent planning, coding, completion, and referencing
- 🚀 **Strong Practitioner**: Good workflow with minor areas for improvement  
- 📈 **Developing Process**: Making progress but needs more consistency
- 🌱 **Learning Workflow**: Basic activity but missing key workflow elements
- 🎯 **Getting Started**: Just beginning to develop workflow practices

## Quick Tips for Success

1. **Start each task by creating issues** - don't jump straight into coding
2. **Reference issue numbers in commit message** - make it a habit
3. **Use "Fixes #X" when completing work** - automate your workflow
4. **Aim for more commits than issues** - shows balanced planning and execution
5. **Close issues promptly** - don't let them pile up

## Common Mistakes to Avoid

- ❌ No issues created (jumping straight to coding)
- ❌ Issues created but never referenced in commits
- ❌ Issues left open after completion
- ❌ Too few commits relative to issues (not showing work progression)
- ❌ Generic commit messages without issue references

Remember: ICE isn't about perfection, it's about developing professional habits that will serve you throughout your career!

Pssst, here is the model in case you read this far...
```python
def classify_workflow_performance(author_data, expected_exercises):
    """Classify student workflow performance into categories"""
    commits = author_data['commits']
    issues = author_data['issues']
    closed_issues = author_data['closed_issues']
    closing_references = author_data['closing_references']
    
    # Calculate workflow scores
    issue_score = min(issues / expected_exercises, 1.0) if expected_exercises > 0 else 0
    commit_score = min(commits / max(issues, 1), 1.0) if issues > 0 else (1.0 if commits > 0 else 0)
    closing_score = closing_references / max(closed_issues, 1) if closed_issues > 0 else 0

    overall_score = issue_score * 0.45 + commit_score * 0.25 + closing_score * 0.3

    # Underplanning penalty (n.b. task-1 did not have the div by 2)
    if issues < (expected_exercises / 2):
        overall_score *= 0.5

    # Classify based on overall workflow mastery
    if overall_score >= 0.95:
        return "🌟 Workflow Master"
    elif overall_score >= 0.75:
        return "🚀 Strong Practitioner"
    elif overall_score >= 0.50:
        return "📈 Developing Process"
    elif overall_score >= 0.25:
        return "🌱 Learning Workflow"
    else:
        return "🎯 Getting Started"
```