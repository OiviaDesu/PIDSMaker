#!/bin/bash
# Pre-commit hook to prevent emojis in committed files
# Per .github/AI_AGENT_INSTRUCTIONS.md: NO EMOJIS ALLOWED

# ANSI color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Common emoji patterns to check
# This regex matches most emoji ranges in Unicode
EMOJI_REGEX='[\x{1F300}-\x{1F9FF}]|[\x{2600}-\x{26FF}]|[\x{2700}-\x{27BF}]|[\x{1F600}-\x{1F64F}]|[\x{1F680}-\x{1F6FF}]|[\x{1F1E0}-\x{1F1FF}]|[\x{2300}-\x{23FF}]|[\x{2B50}]|[\x{2705}]|[\x{274C}]|[\x{274E}]|[\x{2753}-\x{2755}]|[\x{2795}-\x{2797}]|[\x{27A1}]|[\x{2934}-\x{2935}]|[\x{2B05}-\x{2B07}]|[\x{2B1B}-\x{2B1C}]|[\x{3030}]|[\x{303D}]|[\x{3297}]|[\x{3299}]|[\x{FE0F}]'

# Common text emojis used in this codebase
COMMON_EMOJIS='✅|❌|⚠️|🔍|⭐|📋|💡|🚀|🔧|🐛|📝|✨'

FOUND_EMOJI=0
FILES_WITH_EMOJI=""

# Get list of staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

echo "Checking for emojis in staged files..."

for FILE in $STAGED_FILES; do
    # Skip binary files and specific directories
    if [[ "$FILE" == *.png ]] || [[ "$FILE" == *.jpg ]] || [[ "$FILE" == *.pdf ]] || \
       [[ "$FILE" == *".git/"* ]] || [[ "$FILE" == *"wandb/"* ]] || \
       [[ "$FILE" == *"__pycache__"* ]] || [[ "$FILE" == *".egg-info"* ]]; then
        continue
    fi
    
    # Check if file exists (it might have been deleted)
    if [ ! -f "$FILE" ]; then
        continue
    fi
    
    # Check for common text emojis using grep
    if grep -qP "$COMMON_EMOJIS" "$FILE" 2>/dev/null; then
        FOUND_EMOJI=1
        FILES_WITH_EMOJI="$FILES_WITH_EMOJI\n  - $FILE"
        
        # Show which emojis were found
        FOUND_IN_FILE=$(grep -nP "$COMMON_EMOJIS" "$FILE" 2>/dev/null | head -3)
        FILES_WITH_EMOJI="$FILES_WITH_EMOJI\n$(echo "$FOUND_IN_FILE" | sed 's/^/      /')"
    fi
done

if [ $FOUND_EMOJI -eq 1 ]; then
    echo -e "${RED}[COMMIT BLOCKED]${NC} Emojis detected in staged files!"
    echo ""
    echo -e "${YELLOW}Per .github/AI_AGENT_INSTRUCTIONS.md:${NC}"
    echo "  - NO EMOJIS allowed in code or documentation"
    echo "  - Use text markers: [OK], [FAIL], [WARNING], [CRITICAL]"
    echo ""
    echo "Files with emojis:"
    echo -e "$FILES_WITH_EMOJI"
    echo ""
    echo "Please remove all emojis and use text-based indicators instead."
    echo ""
    echo "Examples:"
    echo "  Replace: ✅ PAPER-ALIGNED"
    echo "  With:    [OK] PAPER-ALIGNED"
    echo ""
    echo "  Replace: ❌ Failed"
    echo "  With:    [FAIL] Failed"
    echo ""
    echo "  Replace: ⚠️ Warning"
    echo "  With:    [WARNING] Warning"
    echo ""
    exit 1
fi

echo "[OK] No emojis detected"
exit 0
