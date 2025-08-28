#!/bin/bash

# Improved Git Commit Analysis Script
# 
# This script provides robust analysis of git commits with better error handling,
# more flexible author matching, and improved CSV generation.
#
# Features:
# - Robust CSV escaping and field separation
# - Better fix detection patterns
# - Error handling and validation
# - Configurable author matching
# - Optional file filtering (exclude generated/large files)
# - JSON output option for better data processing

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
AUTHOR_PATTERN="${1:-[Gg]lassey}"
OUTPUT_FORMAT="${2:-csv}"  # csv or json
EXCLUDE_PATTERNS="${3:-}"  # Optional: patterns to exclude (e.g., "*.min.js,*.lock,dist/*")

# Validate we're in a git repository
if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "Error: Not in a git repository" >&2
    exit 1
fi

# Function to escape CSV fields properly
escape_csv() {
    local field="$1"
    # Replace quotes with double quotes and wrap in quotes if contains special chars
    if [[ "$field" =~ [,\"$'\n'$'\r'] ]]; then
        field="${field//\"/\"\"}"
        echo "\"$field\""
    else
        echo "$field"
    fi
}

# Function to detect fix commits with better patterns
is_fix_commit() {
    local subject="$1"
    local lower_subject=$(echo "$subject" | tr '[:upper:]' '[:lower:]')
    
    # More comprehensive fix patterns
    if [[ "$lower_subject" =~ (fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved|repair|repairs|repaired)([[:space:]]|es?[[:space:]]|ed[[:space:]]|ing[[:space:]]).*#[0-9]+ ]] ||
       [[ "$lower_subject" =~ (fix|close|resolve)[[:space:]]*:?[[:space:]]*#[0-9]+ ]] ||
       [[ "$lower_subject" =~ #[0-9]+.*\b(fix|close|resolve) ]]; then
        echo "T"
    else
        echo "F"
    fi
}

# Generate analysis using git log with proper format
analyze_commits() {
    local temp_file=$(mktemp)
    trap "rm -f $temp_file" EXIT
    
    # Use null-terminated format for robust parsing
    git log --author="$AUTHOR_PATTERN" --date=short --numstat \
        --pretty=format:'%x00COMMIT%x00%H%x00%an%x00%ad%x00%s%x00' \
        | while IFS= read -r -d '' line || [[ -n "$line" ]]; do
        
        if [[ "$line" =~ ^COMMIT ]]; then
            # Process previous commit if exists
            if [[ -n "${commit:-}" ]]; then
                local fix_flag=$(is_fix_commit "$subject")
                if [[ "$OUTPUT_FORMAT" == "json" ]]; then
                    printf '{"commit":"%s","author":"%s","date":"%s","subject":"%s","insertions":%d,"deletions":%d,"total":%d,"fix":"%s"}\n' \
                        "$commit" "$author" "$date" "${subject//\"/\\\"}" "$insertions" "$deletions" $((insertions + deletions)) "$fix_flag"
                else
                    printf '%s,%s,%s,%s,%d,%d,%d,%s\n' \
                        "$commit" "$(escape_csv "$author")" "$date" "$(escape_csv "$subject")" \
                        "$insertions" "$deletions" $((insertions + deletions)) "$fix_flag"
                fi
            fi
            
            # Parse new commit
            IFS=$'\x00' read -ra fields <<< "$line"
            commit="${fields[1]}"
            author="${fields[2]}"
            date="${fields[3]}"
            subject="${fields[4]}"
            insertions=0
            deletions=0
            
        elif [[ "$line" =~ ^[0-9-]+[[:space:]]+[0-9-]+[[:space:]] ]]; then
            # Parse numstat line
            read -r ins del file <<< "$line"
            
            # Skip files matching exclude patterns
            if [[ -n "$EXCLUDE_PATTERNS" ]]; then
                local skip=false
                IFS=',' read -ra patterns <<< "$EXCLUDE_PATTERNS"
                for pattern in "${patterns[@]}"; do
                    if [[ "$file" == $pattern ]]; then
                        skip=true
                        break
                    fi
                done
                [[ "$skip" == true ]] && continue
            fi
            
            # Add to totals (handle binary files marked with -)
            [[ "$ins" != "-" ]] && insertions=$((insertions + ins))
            [[ "$del" != "-" ]] && deletions=$((deletions + del))
        fi
    done
    
    # Handle last commit
    if [[ -n "${commit:-}" ]]; then
        local fix_flag=$(is_fix_commit "$subject")
        if [[ "$OUTPUT_FORMAT" == "json" ]]; then
            printf '{"commit":"%s","author":"%s","date":"%s","subject":"%s","insertions":%d,"deletions":%d,"total":%d,"fix":"%s"}\n' \
                "$commit" "$author" "$date" "${subject//\"/\\\"}" "$insertions" "$deletions" $((insertions + deletions)) "$fix_flag"
        else
            printf '%s,%s,%s,%s,%d,%d,%d,%s\n' \
                "$commit" "$(escape_csv "$author")" "$date" "$(escape_csv "$subject")" \
                "$insertions" "$deletions" $((insertions + deletions)) "$fix_flag"
        fi
    fi
}

# Main execution
main() {
    if [[ "$OUTPUT_FORMAT" == "csv" ]]; then
        echo "commit,author,date,subject,insertions,deletions,total,fix"
    fi
    
    analyze_commits
}

# Show usage if help requested
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    cat << EOF
Usage: $0 [AUTHOR_PATTERN] [OUTPUT_FORMAT] [EXCLUDE_PATTERNS]

Arguments:
  AUTHOR_PATTERN   Git author pattern (default: [Gg]lassey)
  OUTPUT_FORMAT    Output format: csv or json (default: csv)
  EXCLUDE_PATTERNS Comma-separated file patterns to exclude (optional)

Examples:
  $0                                    # Default: Glassey commits as CSV
  $0 "john.doe" json                   # John Doe commits as JSON
  $0 ".*" csv "*.min.js,*.lock"       # All authors, exclude minified and lock files

EOF
    exit 0
fi

main "$@"
