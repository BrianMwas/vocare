#!/bin/bash

# =====================================================
# Git Security Cleanup Script
# Removes sensitive files from Git history
# =====================================================

echo "🔒 Git Security Cleanup Script"
echo "=============================="
echo ""
echo "⚠️  WARNING: This will rewrite Git history!"
echo "⚠️  Make sure all team members pull the new history after this runs."
echo ""

# Confirm before proceeding
read -p "Continue? (y/N): " confirm
if [[ $confirm != [yY] ]]; then
    echo "❌ Cleanup cancelled."
    exit 0
fi

echo ""
echo "🧹 Removing sensitive files from Git history..."

# Remove .env files from history
echo "Removing .env files..."
git filter-branch --force --index-filter \
    'git rm --cached --ignore-unmatch .env .env.local .env.development .env.production .env.staging' \
    --prune-empty --tag-name-filter cat -- --all

# Remove service.json files from history
echo "Removing Firebase service account files..."
git filter-branch --force --index-filter \
    'git rm --cached --ignore-unmatch service.json firebase-credentials.json *-firebase-adminsdk-*.json firebase-service-account*.json' \
    --prune-empty --tag-name-filter cat -- --all

# Remove other credential files
echo "Removing other credential files..."
git filter-branch --force --index-filter \
    'git rm --cached --ignore-unmatch credentials.json config.json secrets.json' \
    --prune-empty --tag-name-filter cat -- --all

# Clean up Git refs
echo "Cleaning up Git references..."
git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin

# Expire reflog and garbage collect
echo "Cleaning up Git database..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "✅ Git history cleanup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Force push to update remote repository:"
echo "   git push origin --force --all"
echo "   git push origin --force --tags"
echo ""
echo "2. All team members must clone fresh or run:"
echo "   git fetch origin"
echo "   git reset --hard origin/main"
echo ""
echo "3. Recreate your .env and service.json files locally"
echo ""
echo "⚠️  Remember: These files are now ignored and won't be committed again!"