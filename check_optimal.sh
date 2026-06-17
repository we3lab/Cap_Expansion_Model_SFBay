#!/usr/bin/env bash
#
# check_optimal.sh
# ----------------------------------------------------------------------------
# Recursively scans a directory tree for .txt log files and
# reports, for each one, whether the phrase "Optimal solution found" appears.
#
# Output layout (aligned/padded columns):
#
#   <relative folder path>                 <- header
#       <file1.txt>      Optimal solution found   <- if optimal solution found
#       <file2.txt>      N/A                     <- if optimal solution is not found
#
#
# Usage:
#   ./check_optimal.sh [SCAN_DIR] [OUTPUT_FILE]
#       SCAN_DIR      directory to scan        (default: the script's own folder)
#       OUTPUT_FILE   report file to write     (default: <script folder>/optimal_solution_report.txt)
# ----------------------------------------------------------------------------

set -euo pipefail

PHRASE="Optimal solution found"

# ---- Arguments -------------------------------------------------------------
# Directory the script file itself lives in (works no matter where it's called
# from). This is the default directory to scan.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCAN_DIR="${1:-$SCRIPT_DIR}"
OUTPUT_FILE="${2:-$SCRIPT_DIR/optimal_solution_report.txt}"

if [[ ! -d "$SCAN_DIR" ]]; then
    echo "Error: '$SCAN_DIR' is not a directory." >&2
    exit 1
fi

# Resolve absolute paths so the report location is stable and can be excluded
# from the scan (otherwise re-runs would pick up the report itself).
SCAN_DIR_ABS="$(cd "$SCAN_DIR" && pwd)"
OUTPUT_DIR_ABS="$(cd "$(dirname "$OUTPUT_FILE")" 2>/dev/null && pwd || pwd)"
OUTPUT_ABS="$OUTPUT_DIR_ABS/$(basename "$OUTPUT_FILE")"

# ---- Collect results -------------------------------------------------------
folders=()    # relative folder path (the "header")
names=()      # .txt filename        (the "subheader")
statuses=()   # "Optimal solution found" or "N/A"
maxname=0     # widest filename, for column alignment

# Run find from inside the scan dir so it prints paths relative to that root.
# Sorting the null-delimited list groups files in the same folder together.
while IFS= read -r -d '' f; do
    rel="${f#./}"                      # strip leading "./"
    abs="$SCAN_DIR_ABS/$rel"

    # Never report the output file itself.
    [[ "$abs" == "$OUTPUT_ABS" ]] && continue

    folder="$(dirname "$rel")"
    name="$(basename "$rel")"
    [[ "$folder" == "." ]] && folder="(root)"

    if grep -qF -- "$PHRASE" "$abs"; then
        status="Optimal solution found"
    else
        status="N/A"
    fi

    folders+=("$folder")
    names+=("$name")
    statuses+=("$status")

    if (( ${#name} > maxname )); then
        maxname=${#name}
    fi
done < <(cd "$SCAN_DIR_ABS" && find . -type f -name '*.txt' -print0 | sort -z)

# ---- Write report ----------------------------------------------------------
{
    printf 'Optimal-solution check\n'
    printf 'Scanned directory : %s\n' "$SCAN_DIR_ABS"
    printf 'Generated         : %s\n' "$(date '+%Y-%m-%d %H:%M:%S')"
    printf 'Phrase searched   : "%s"\n' "$PHRASE"
    printf -- '----------------------------------------------------------------\n\n'

    if (( ${#names[@]} == 0 )); then
        printf 'No .txt files found.\n'
    else
        indent="    "
        col=$(( maxname + 4 ))          # padding between filename and status
        prev=""
        for i in "${!names[@]}"; do
            if [[ "${folders[$i]}" != "$prev" ]]; then
                [[ -n "$prev" ]] && printf '\n'
                printf '%s\n' "${folders[$i]}"          # header: relative path
                prev="${folders[$i]}"
            fi
            # subheader: filename (padded) + status, aligned into columns
            printf '%s%-*s%s\n' "$indent" "$col" "${names[$i]}" "${statuses[$i]}"
        done
    fi
} > "$OUTPUT_FILE"

echo "Report written to : $OUTPUT_FILE"
echo "Files checked     : ${#names[@]}"