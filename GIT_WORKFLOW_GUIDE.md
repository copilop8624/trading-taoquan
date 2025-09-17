# 🔧 Git Workflow Guide - Trading Optimization System

## 📋 Quick Commands Reference

### 🛡️ Safety Commands (Always Use These!)

```bash
# Check current status before any changes
git status

# Create backup before working
git branch backup-$(Get-Date -Format "yyyyMMdd-HHmm")

# Save current work
git add -A
git commit -m "backup: working state before changes"
```

### 🔄 Branch Management

**Available Branches:**
- `main` - Production stable code ✅
- `development` - For testing new features 🧪
- `backup-stable-interface` - Known working interface 🎯
- `backup-working-state` - Current working version 💾
- `backup-local-main` - Local backup of main 🔒

### 📁 Restore Template (Like We Just Did!)

```bash
# Option 1: Restore from backup branch
git checkout backup-stable-interface -- templates/index.html

# Option 2: Restore from backup file
copy "templates\index_backup_before_home_fix.html" "templates\index.html"

# Option 3: Restore specific commit
git checkout [commit-hash] -- templates/index.html
```

### 🚀 Safe Development Workflow

#### Before Making Changes:
```bash
# 1. Check status
git status

# 2. Create backup branch with timestamp
$timestamp = Get-Date -Format "yyyyMMdd-HHmm"
git branch "backup-before-changes-$timestamp"

# 3. Commit current state
git add -A
git commit -m "backup: safe state before [description]"
```

#### During Development:
```bash
# Switch to development branch
git checkout development

# Make your changes to files...

# Test changes
git add templates/index.html
git commit -m "test: trying new interface changes"
```

#### After Testing:
```bash
# If changes work well
git checkout main
git merge development
git commit -m "feat: successful interface improvements"

# If changes break things
git checkout main  # Go back to working version
# Files are automatically restored!
```

### 🆘 Emergency Restore Commands

#### If Template Breaks:
```bash
# Quick restore from known working backup
git checkout backup-stable-interface -- templates/index.html

# Or restore from backup file
copy "templates\index_backup_before_home_fix.html" "templates\index.html"

# Restart server
.\\.venv_new\\Scripts\\python.exe web_app.py
```

#### If Entire Project Breaks:
```bash
# Nuclear option - restore everything from backup
git checkout backup-working-state
```

#### If Need to Find Working Commit:
```bash
# See recent commits
git log --oneline -10

# Restore specific file from specific commit
git checkout [commit-hash] -- [filename]
```

### 💡 Best Practices

1. **Always backup before changes:**
   ```bash
   git branch backup-$(Get-Date -Format "yyyyMMdd-HHmm")
   git commit -am "backup: before making changes"
   ```

2. **Use descriptive commit messages:**
   ```bash
   git commit -m "fix: restore working template interface"
   git commit -m "feat: add new optimization feature"
   git commit -m "backup: stable state with Quick Summary working"
   ```

3. **Test on development branch first:**
   ```bash
   git checkout development
   # make changes
   # test thoroughly
   git checkout main
   git merge development  # only if testing successful
   ```

4. **Keep backup branches clean:**
   ```bash
   # List all branches
   git branch

   # Delete old backup branches (optional)
   git branch -d backup-old-name
   ```

### 🎯 Templates Specific Workflow

Since templates are critical for the web interface:

```bash
# Before editing templates
copy "templates\index.html" "templates\index_backup_$(Get-Date -Format 'yyyyMMdd-HHmm').html"

# After editing and testing
git add templates/index.html
git commit -m "feat: improved template - tested working"

# If template breaks
copy "templates\index_backup_before_home_fix.html" "templates\index.html"
```

### 📊 Git Status Meanings

- `M` = Modified file
- `A` = Added (new) file  
- `D` = Deleted file
- `??` = Untracked file (ignored by .gitignore)

### 🔍 Useful Commands

```bash
# See what changed
git diff

# See commit history
git log --oneline -10

# See all branches
git branch -a

# See current branch
git branch

# Push to remote (backup to GitHub)
git push origin main
```

## 🎉 Summary

**Main Rule:** Always create a backup branch before making changes!

```bash
git branch backup-$(Get-Date -Format "yyyyMMdd-HHmm")
git commit -am "backup: safe working state"
```

This prevents situations like today where we needed to hunt for working template files! 

**Remember:** Git is your friend - use it frequently and you'll never lose working code again! 🛡️