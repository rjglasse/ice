# ICE - Issue, Commit, Effort Analysis

A comprehensive workflow analysis system for programming education that helps students develop professional software development practices through automated feedback.

## Overview

ICE analyzes student coding workflows across five key dimensions:
- **📝 Planning**: Issue creation and task breakdown
- **💻 Coding**: Commit frequency and development activity  
- **✅ Completion**: Issue closure and task completion
- **🔗 Traceability**: Linking commits to issues
- **⚡ Automation**: Using closing keywords for workflow automation

## Quick Start

1. **Extract data** from student repositories:
   ```bash
   python3 scripts/commits.py task-1
   python3 scripts/issues.py task-1
   python3 scripts/effort.py task-1
   ```

2. **Generate comprehensive feedback**:
   ```bash
   python3 scripts/nudges.py task-1
   ```

3. **Create GitHub issues** with feedback:
   ```bash
   # Preview what will be created
   python3 scripts/feedback.py task-1 --dry-run
   
   # Create issues for all students
   python3 scripts/feedback.py task-1
   
   # Target specific student
   python3 scripts/feedback.py task-1 --student username
   ```

## Workflow Classification

Students are classified into five tiers based on their workflow performance:

- **🌟 Workflow Master** (47%): Excellent across all workflow dimensions
- **🚀 Strong Practitioner** (11%): Good overall workflow with minor improvements needed
- **📈 Developing Process** (2%): Basic workflow established, consistency needed
- **🌱 Learning Workflow** (14%): Understanding workflow basics, needs development
- **🎯 Getting Started** (23%): Beginning their workflow journey

## Student Guide

Students receive personalized feedback and can learn more about improving their workflow at: 
[ICE Workflow Guide](https://gits-15.sys.kth.se/inda-25/course-instructions/blob/main/ice-guide.md)

## Configuration

Update `scripts/context.py` with:
- Teacher names for filtering
- Expected exercises per task
- Task definitions and requirements

## Output Files

Results are saved to `data/{task-name}/`:
- `commits.csv` - Git commit data with teacher filtering
- `issues.csv` - GitHub issue data with identity resolution  
- `effort.csv` - Comprehensive workflow metrics
- `nudges.csv` - Personalized feedback with peer context

## Repository Structure

```
ice/
├── scripts/           # Analysis and feedback scripts
│   ├── context.py    # Course configuration
│   ├── commits.py    # Git commit extraction
│   ├── issues.py     # GitHub issues analysis
│   ├── effort.py     # Workflow metrics calculation
│   ├── nudges.py     # Feedback generation
│   └── feedback.py   # GitHub issue creation
├── repos/            # Student repositories (empty after cleanup)
├── data/             # Analysis results by task
└── ICE-Guide.md      # Student workflow guide