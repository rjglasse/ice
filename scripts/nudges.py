#!/usr/bin/env python3

import os
import csv
import argparse
import sys
from pathlib import Path

from context import tasks

def read_effort_data(effort_file):
    """Read effort CSV and return list of author data"""
    effort_data = []
    
    try:
        with open(effort_file, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Handle infinite ratios
                ratio = row['commits_to_issues_ratio']
                if ratio == 'inf':
                    ratio_value = float('inf')
                else:
                    ratio_value = float(ratio)
                
                effort_data.append({
                    'author': row['author'],
                    'commits': int(row['commits']),
                    'issues': int(row['issues']),
                    'commits_to_issues_ratio': ratio_value,
                    'total_changes': int(row['total_changes']),
                    'avg_changes_per_commit': float(row['avg_changes_per_commit']),
                    'open_issues': int(row['open_issues']),
                    'closed_issues': int(row['closed_issues']),
                    'references': int(row['references']),
                    'closing_references': int(row['closing_references'])
                })
    except FileNotFoundError:
        print(f"Error: Effort file not found: {effort_file}")
        return []
    except Exception as e:
        print(f"Error reading effort file: {e}")
        return []
    
    return effort_data

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

    # Underplanning penalty
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

def generate_nudge_message(author_data, task_name, expected_exercises):
    """Generate workflow-focused nudge message"""
    author = author_data['author']
    commits = author_data['commits']
    issues = author_data['issues']
    open_issues = author_data['open_issues']
    closed_issues = author_data['closed_issues']
    references = author_data['references']
    closing_references = author_data['closing_references']
    
    nudges = []
    
    # Always provide comprehensive feedback across all dimensions
    
    # 1. Planning (Issues vs exercises)
    if issues == 0:
        nudges.append(f"📝 **Planning**: Create issues for each exercise to track progress ({issues}/{expected_exercises} issues)")
    elif issues < expected_exercises:
        nudges.append(f"📝 **Planning**: Nice that you've made your own plan, but try making more issues ({issues}/{expected_exercises}, default: ~{expected_exercises})")
    elif issues > expected_exercises + 2:
        nudges.append(f"📝 **Planning**: Good issue tracking! ({issues}/{expected_exercises})")
    else:
        nudges.append(f"📝 **Planning**: Well-balanced issue planning ({issues}/{expected_exercises} issues)")
    
    # 2. Coding Activity (Commits to issues ratio)
    if commits == 0 and issues > 0:
        nudges.append(f"💻 **Coding**: Start coding - issues need commits ({commits} commits, {issues} issues)")
    elif commits < issues:
        nudges.append(f"💻 **Coding**: More commits needed ({commits}/{issues}, target: ≥1 commit per issue)")
    elif commits >= issues and issues > 0:
        ratio = round(commits / issues, 1)
        nudges.append(f"💻 **Coding**: Good commit frequency ({commits} commits for {issues} issues, ratio: {ratio})")
    elif commits > 0 and issues == 0:
        nudges.append(f"💻 **Coding**: Active coding but consider planning with issues first ({commits} commits)")
    
    # 3. Completion (Issue states)
    if open_issues > closed_issues and closed_issues > 0:
        nudges.append(f"🎯 **Completion**: Close remaining issues to finish tasks ({open_issues} open, {closed_issues} closed)")
    elif open_issues > 0 and closed_issues == 0:
        nudges.append(f"🎯 **Completion**: Start completing issues ({open_issues} open, {closed_issues} closed)")
    elif closed_issues > 0 and open_issues == 0:
        nudges.append(f"✅ **Completion**: Excellent - all issues completed ({closed_issues} closed)")
    elif closed_issues == 0 and open_issues == 0:
        nudges.append(f"🎯 **Completion**: No issues to track completion yet")
    
    # 4. Traceability (Issue references)
    # if references == 0 and commits > 0:
    #     nudges.append(f"🔗 **Traceability**: Link commits to issues ({references}/{commits} commits reference issues)")
    # elif references > 0 and commits > 0:
    #     ref_percentage = int((references / commits) * 100)
    #     if ref_percentage >= 80:
    #         nudges.append(f"🔗 **Traceability**: Excellent issue referencing ({references}/{commits} commits, {ref_percentage}%)")
    #     else:
    #         nudges.append(f"🔗 **Traceability**: Good progress, reference issues more often ({references}/{commits} commits, {ref_percentage}%)")
    
    # 5. Professional Workflow (Closing references)
    if closing_references == 0 and closed_issues > 0:
        nudges.append(f"⚡ **Automation**: Use closing keywords like 'Fixes # 1' to automate workflow ({closing_references}/{closed_issues} issues properly closed)")
    elif closing_references > 0 and closed_issues > 0:
        closing_percentage = int((closing_references / closed_issues) * 100)
        if closing_percentage >= 80:
            nudges.append(f"⚡ **Automation**: Perfect use of closing keywords ({closing_references}/{closed_issues} issues, {closing_percentage}%)")
        else:
            nudges.append(f"⚡ **Automation**: Good start, use closing keywords more often ({closing_references}/{closed_issues} issues, {closing_percentage}%)")
    elif closed_issues == 0:
        nudges.append(f"⚡ **Automation**: Complete some issues to practice using closing keywords")
    
    # Format as markdown bullet points with opening sentence
    if nudges:
        return "Here's how it went for your plan and process:\n" + "\n".join(f"- {nudge}" for nudge in nudges)
    else:
        return "Here's how it went for your plan and process:\n- ✨ Excellent workflow! Perfect balance of planning and execution."

def format_distribution_summary(classification_counts, user_classification):
    """Format distribution summary showing where the student fits"""
    total_students = sum(classification_counts.values())
    if total_students <= 1:
        return ""
    
    distribution_parts = []
    categories = ["🌟 Workflow Master", "🚀 Strong Practitioner", "📈 Developing Process", 
                 "🌱 Learning Workflow", "🎯 Getting Started"]
    
    for category in categories:
        count = classification_counts.get(category, 0)
        if count > 0:
            percentage = int(count / total_students * 100)
            if category == user_classification:
                distribution_parts.append(f"**{category}: {percentage}%** (<< you)")
            else:
                distribution_parts.append(f"{category}: {percentage}%")
    
    # Format as markdown list
    distribution_list = "\n\n📊 **Class Distribution**:\nHere's how the rest of the course did:\n" + "\n".join(f"- {part}" for part in distribution_parts)
    return distribution_list

def write_nudges_csv(nudges_data, output_file):
    """Write nudges data to CSV file"""
    fieldnames = ['author', 'commits', 'issues', 'open_issues', 'closed_issues', 
                 'references', 'closing_references', 'classification', 'nudge_message', 'issue_created']
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in nudges_data:
            writer.writerow(row)

def main():
    parser = argparse.ArgumentParser(description='Generate workflow-focused nudge messages for authors')
    parser.add_argument('task', help='Task name (e.g., task-1, task-2)')
    parser.add_argument('--data-dir', default='data', help='Directory containing effort CSV file')
    
    args = parser.parse_args()
    
    # Get task information
    if args.task not in tasks:
        print(f"Warning: Task {args.task} not found in context.py, using default exercise count of 5")
        expected_exercises = 5
    else:
        expected_exercises = tasks[args.task]['number_of_exercises']
    
    # Define file paths
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    effort_file = base_dir / args.data_dir / args.task / "effort.csv"
    output_file = base_dir / args.data_dir / args.task / "nudges.csv"
    
    print(f"Analyzing effort data for {args.task}")
    print(f"Reading effort from: {effort_file}")
    
    # Read effort data
    effort_data = read_effort_data(effort_file)
    if not effort_data:
        return 1
    
    print(f"Found effort data for {len(effort_data)} authors")
    print(f"Expected exercises for {args.task}: {expected_exercises}")
    
    # First pass: classify all students to get distribution
    classifications = {}
    classification_counts = {}
    
    for author_data in effort_data:
        classification = classify_workflow_performance(author_data, expected_exercises)
        classifications[author_data['author']] = classification
        classification_counts[classification] = classification_counts.get(classification, 0) + 1
    
    # Second pass: generate nudges with distribution context
    nudges_data = []
    for author_data in effort_data:
        author = author_data['author']
        classification = classifications[author]
        base_nudge = generate_nudge_message(author_data, args.task, expected_exercises)
        distribution_summary = format_distribution_summary(classification_counts, classification)
        
        # Feedback issues are posted to student repositories, so keep the guide
        # reference repo-agnostic instead of linking to this repo directly.
        guide_note = "\n\nSee `ice-guide.md` in the ICE repository for the full workflow guide."
        full_message = base_nudge + distribution_summary + guide_note
        
        nudges_data.append({
            'author': author,
            'commits': author_data['commits'],
            'issues': author_data['issues'],
            'open_issues': author_data['open_issues'],
            'closed_issues': author_data['closed_issues'],
            'references': author_data['references'],
            'closing_references': author_data['closing_references'],
            'classification': classification,
            'nudge_message': full_message,
            'issue_created': False
        })
    
    # Write results
    write_nudges_csv(nudges_data, output_file)
    print(f"Nudges generated! Results written to: {output_file}")
    
    # Show classification distribution
    print("\nClassification Distribution:")
    total = sum(classification_counts.values())
    for classification, count in classification_counts.items():
        percentage = int(count / total * 100)
        print(f"  {classification}: {count} students ({percentage}%)")
    
    print("\nNudge Summary:")
    for data in nudges_data:
        classification = data['classification']
        print(f"  {data['author']} ({classification}): {data['nudge_message'][:60]}...")
    
    return 0

if __name__ == "__main__":
    exit(main())
