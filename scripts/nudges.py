#!/usr/bin/env python3

import os
import csv
import argparse
import statistics
import random
from pathlib import Path

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
                    'closed_issues': int(row['closed_issues'])
                })
    except FileNotFoundError:
        print(f"Error: Effort file not found: {effort_file}")
        return []
    except Exception as e:
        print(f"Error reading effort file: {e}")
        return []
    
    return effort_data

def calculate_effort_baseline(effort_data):
    """Calculate baseline effort metrics from the data"""
    if not effort_data:
        return None
    
    # Filter out infinite ratios for statistical calculations
    finite_ratios = [d['commits_to_issues_ratio'] for d in effort_data 
                     if d['commits_to_issues_ratio'] != float('inf')]
    
    commits = [d['commits'] for d in effort_data]
    total_changes = [d['total_changes'] for d in effort_data]
    
    baseline = {
        'mean_commits': statistics.mean(commits) if commits else 0,
        'median_commits': statistics.median(commits) if commits else 0,
        'mean_ratio': statistics.mean(finite_ratios) if finite_ratios else 0,
        'median_ratio': statistics.median(finite_ratios) if finite_ratios else 0,
        'mean_changes': statistics.mean(total_changes) if total_changes else 0,
        'median_changes': statistics.median(total_changes) if total_changes else 0,
        'total_authors': len(effort_data)
    }
    
    return baseline

def categorize_effort(author_data, baseline):
    """Categorize author effort into one of 5 levels"""
    commits = author_data['commits']
    ratio = author_data['commits_to_issues_ratio']
    total_changes = author_data['total_changes']
    closed_issues = author_data['closed_issues']
    
    # Handle case where baseline might be zero
    mean_commits = max(baseline['mean_commits'], 1)
    mean_changes = max(baseline['mean_changes'], 1)
    mean_ratio = max(baseline['mean_ratio'], 1)
    
    # Calculate relative performance metrics
    commit_score = commits / mean_commits
    changes_score = total_changes / mean_changes
    
    # Handle infinite ratio (no issues - excellent!)
    if ratio == float('inf'):
        ratio_score = 2.0  # Very high score
    else:
        ratio_score = ratio / mean_ratio if mean_ratio > 0 else 1.0
    
    # Bonus for closing issues
    closure_bonus = 1.0 + (closed_issues * 0.1)
    
    # Overall effort score (weighted combination)
    effort_score = (commit_score * 0.4 + changes_score * 0.3 + ratio_score * 0.3) * closure_bonus
    
    # Categorize based on effort score
    if effort_score >= 1.5:
        return "Excellent"
    elif effort_score >= 1.2:
        return "Good"
    elif effort_score >= 0.8:
        return "Balanced"
    elif effort_score >= 0.5:
        return "Moderate"
    else:
        return "Low"

def generate_nudge_message(author_data, category, baseline, category_distribution):
    """Generate personalized nudge message based on effort category"""
    author = author_data['author']
    commits = author_data['commits']
    issues = author_data['issues']
    ratio = author_data['commits_to_issues_ratio']
    total_changes = author_data['total_changes']
    open_issues = author_data['open_issues']
    closed_issues = author_data['closed_issues']
    
    ratio_str = "∞" if ratio == float('inf') else f"{ratio:.2f}"
    
    messages = {
        "Excellent": [
            f"🌟 Outstanding work, {author}! Your {commits} commits and {ratio_str} commit-to-issue ratio demonstrate exceptional productivity.",
            f"💪 Keep up the excellent momentum with {total_changes} total changes! You're setting a great example for the team.",
            f"🚀 Fantastic effort! Your {closed_issues} closed issues show you're not just coding, but solving problems effectively.",
            f"🏆 Exceptional performance, {author}! Your coding velocity of {commits} commits is inspiring others to step up their game.",
            f"⚡ Incredible productivity! With {total_changes} changes, you're demonstrating mastery-level commitment to quality code.",
            f"🎯 Perfect execution! Your {ratio_str} commit-to-issue ratio shows you're focused on delivering solutions, not just reporting problems.",
            f"🔥 You're on fire, {author}! This level of consistent output with {commits} commits is what excellence looks like.",
            f"💎 Top-tier contributor! Your work ethic and {closed_issues} resolved issues showcase both quantity and quality.",
            f"🌈 Amazing work! You're not just meeting expectations with {total_changes} changes - you're redefining what's possible.",
            f"🎊 Stellar performance, {author}! Your dedication shines through every one of your {commits} commits."
        ],
        
        "Good": [
            f"👍 Great job, {author}! Your {commits} commits show solid progress. Consider tackling a few more challenging features.",
            f"📈 Good momentum with {ratio_str} commit-to-issue ratio! Maybe explore some advanced techniques to push your skills further.",
            f"💡 Nice work with {total_changes} changes! You're on the right track - keep building on this foundation.",
            f"🎉 Strong effort, {author}! Your {commits} commits demonstrate good consistency. Ready to push into advanced territory?",
            f"📊 Impressive progress! With {total_changes} changes, you're showing real commitment. What's your next coding challenge?",
            f"🌟 Well done! Your {ratio_str} commit-to-issue ratio shows you're solution-focused. Time to tackle something ambitious?",
            f"🚀 Good work, {author}! Your {closed_issues} closed issues prove you finish what you start. Ready for the next level?",
            f"💫 Solid performance! Your {commits} commits show discipline. Consider mentoring someone or leading a feature?",
            f"🎯 Great trajectory, {author}! Your coding rhythm with {total_changes} changes is building nicely. What's your stretch goal?",
            f"🌸 Lovely progress! You're developing a strong pattern with {commits} commits. Ready to innovate or optimize?"
        ],
        
        "Balanced": [
            f"⚖️ Solid work, {author}! Your {commits} commits show steady progress. Try setting small daily commit goals to boost momentum.",
            f"🎯 You're maintaining a good balance with {ratio_str} commit-to-issue ratio. Consider taking on one additional feature challenge.",
            f"📚 Your {total_changes} changes show consistent effort. Maybe try a new technique or explore a different part of the codebase?",
            f"🌊 Steady as she goes, {author}! Your {commits} commits show reliability. Ready to add some experimentation to the mix?",
            f"📈 Nice foundation with {total_changes} changes! You're building good habits. What would make coding more exciting for you?",
            f"🔄 Consistent work, {author}! Your {ratio_str} commit-to-issue ratio is healthy. Time to add a personal challenge?",
            f"🌱 Growing steadily! Your {commits} commits show you're in rhythm. Consider picking up a new skill or tool?",
            f"⭐ Dependable performance! With {closed_issues} resolved issues, you're proving reliable. Ready for something adventurous?",
            f"🎨 Good craftsmanship, {author}! Your {total_changes} changes show attention to detail. What creative project calls to you?",
            f"🔧 Solid engineering! Your {commits} commits demonstrate good practices. Time to optimize or refactor something interesting?"
        ],
        
        "Moderate": [
            f"🌱 Good start, {author}! With {commits} commits, you're building momentum. Try breaking larger tasks into smaller, daily commits.",
            f"💭 {ratio_str} commit-to-issue ratio shows you're thinking about the work. Consider focusing on completing one feature at a time.",
            f"🔧 Your {total_changes} changes are a good foundation. Try setting aside dedicated coding time each day to build consistency.",
            f"🌟 You're on the right path, {author}! Your {commits} commits show promise. What would help you code more regularly?",
            f"💡 Building momentum! With {total_changes} changes, you're making progress. Consider pairing with someone for accountability?",
            f"🎯 Good thinking with {ratio_str} commit-to-issue ratio! Focus on one small win each day to build confidence.",
            f"🚀 Ready for liftoff, {author}! Your {commits} commits show potential. What's your biggest coding obstacle right now?",
            f"🌈 Every commit counts! Your {closed_issues} closed issues prove you can finish. Let's build that habit stronger.",
            f"📅 Consistency is key, {author}! Your {total_changes} changes show effort. Try scheduling 20 minutes of daily coding?",
            f"💫 You've got this! With {commits} commits under your belt, you're proving you can code. What motivates you most?"
        ],
        
        "Low": [
            f"🌟 Every journey starts with a single commit, {author}! Let's build momentum with small, daily contributions.",
            f"💪 Great potential ahead! Try starting with just 15 minutes of coding daily - consistency beats intensity.",
            f"🚀 Ready to level up? Consider pairing with a teammate or tackling smaller, achievable tasks first.",
            f"🌱 The best time to start is now, {author}! Even 5 minutes of coding daily can build incredible momentum over time.",
            f"💡 You belong here! Every expert was once a beginner. What's one tiny thing you could commit today?",
            f"🎯 Small steps, big dreams! Consider setting up your development environment and making your first commit this week.",
            f"🌈 Coding is a journey, not a destination, {author}! What's preventing you from taking that first step?",
            f"⭐ Everyone starts somewhere! Pick the smallest possible task and celebrate completing it. You've got this!",
            f"🔥 Your potential is unlimited, {author}! Try the 'two-minute rule' - commit to just 2 minutes of coding daily.",
            f"🎊 Welcome to the adventure! Coding is more fun with friends. Want to find a buddy to learn alongside you?"
        ]
    }
    
    # Randomly select a base message from the category
    category_messages = messages[category]
    base_message = random.choice(category_messages)
    
    # Add specific suggestions
    if open_issues > 0:
        base_message += f" You have {open_issues} open issues - a great opportunity to dive deeper into problem-solving!"
    
    if commits > 0 and total_changes / commits < 10:
        base_message += " Try making slightly more substantial commits to increase your impact per change."
    elif commits > 0 and total_changes / commits > 50:
        base_message += " Great substantial commits! Consider breaking very large changes into smaller, focused commits."
    
    if issues == 0 and commits > 5:
        base_message += " Your commitment to coding over issue creation shows excellent focus!"
    
    # Add distribution context
    total_students = sum(category_distribution.values())
    # if total_students > 0:  # Only show distribution if there are multiple students
    dist_summary = format_distribution_summary(category_distribution, category, total_students)
    base_message += f"\n\n## 📊 Class Distribution \n\n{dist_summary}"

    return base_message

def format_distribution_summary(category_distribution, user_category, total_students):
    """Format a brief distribution summary for context"""
    # Calculate percentages
    percentages = {cat: (count / total_students * 100) for cat, count in category_distribution.items() if count > 0}
    
    # Create a brief summary
    summary_parts = []
    for category in ["Excellent", "Good", "Balanced", "Moderate", "Low"]:
        if category in percentages:
            pct = percentages[category]
            if pct >= 1:  # Only show if 1% or more
                emoji = "🌟" if category == "Excellent" else "👍" if category == "Good" else "⚖️" if category == "Balanced" else "🌱" if category == "Moderate" else "💪"
                if category == user_category:
                    summary_parts.append(f"**{emoji} {category}: {pct:.0f}%** (you)")
                else:
                    summary_parts.append(f"{emoji} {category}: {pct:.0f}%")
    
    return " | ".join(summary_parts)

def write_nudges_csv(nudges_data, output_file):
    """Write nudges data to CSV file"""
    fieldnames = ['author', 'commits', 'issues', 'commits_to_issues_ratio', 
                  'total_changes', 'effort_category', 'nudge_message', 'issue_created']
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in nudges_data:
            writer.writerow(row)

def main():
    parser = argparse.ArgumentParser(description='Generate effort-based nudge messages for authors')
    parser.add_argument('task', help='Task pattern (e.g., task-1, task-2, generictask)')
    parser.add_argument('--data-dir', default='data', help='Directory containing CSV files')
    parser.add_argument('--effort-file', default='effort.csv', help='Input effort CSV filename')
    parser.add_argument('--output', default='nudges.csv', help='Output nudges CSV filename')
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    task_data_dir = base_dir / args.data_dir / args.task
    
    effort_file = task_data_dir / args.effort_file
    output_file = task_data_dir / args.output
    
    print(f"Analyzing effort data for {args.task}")
    print(f"Reading effort from: {effort_file}")
    
    # Read effort data
    effort_data = read_effort_data(effort_file)
    if not effort_data:
        print("No effort data found. Please run analyze_task_data.py first.")
        return
    
    print(f"Found effort data for {len(effort_data)} authors")
    
    # Calculate baseline metrics
    baseline = calculate_effort_baseline(effort_data)
    print(f"Baseline metrics calculated:")
    print(f"  Mean commits: {baseline['mean_commits']:.2f}")
    print(f"  Mean changes: {baseline['mean_changes']:.2f}")
    print(f"  Mean commit-to-issue ratio: {baseline['mean_ratio']:.2f}")
    
    # First pass: categorize all authors to get distribution
    category_counts = {"Low": 0, "Moderate": 0, "Balanced": 0, "Good": 0, "Excellent": 0}
    author_categories = []
    
    for author_data in effort_data:
        category = categorize_effort(author_data, baseline)
        category_counts[category] += 1
        author_categories.append((author_data, category))
    
    # Generate nudges for each author (now with distribution context)
    nudges_data = []
    
    for author_data, category in author_categories:
        nudge_message = generate_nudge_message(author_data, category, baseline, category_counts)
        
        ratio_str = "inf" if author_data['commits_to_issues_ratio'] == float('inf') else author_data['commits_to_issues_ratio']
        
        nudges_data.append({
            'author': author_data['author'],
            'commits': author_data['commits'],
            'issues': author_data['issues'],
            'commits_to_issues_ratio': ratio_str,
            'total_changes': author_data['total_changes'],
            'effort_category': category,
            'nudge_message': nudge_message,
            'issue_created': False
        })
    
    # Sort by effort category (Excellent first)
    category_order = {"Excellent": 0, "Good": 1, "Balanced": 2, "Moderate": 3, "Low": 4}
    nudges_data.sort(key=lambda x: category_order[x['effort_category']])
    
    # Write results
    write_nudges_csv(nudges_data, output_file)
    
    print(f"\nNudges generated! Results written to: {output_file}")
    print(f"Category distribution:")
    for category, count in category_counts.items():
        print(f"  {category}: {count} authors")
    
    # Print summary
    print("\nNudge Summary:")
    for data in nudges_data:
        print(f"  {data['author']} ({data['effort_category']}): {data['nudge_message'][:80]}...")

if __name__ == '__main__':
    main()