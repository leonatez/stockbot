# Deployment and Rollback Guide

## 🚀 Deployment Setup

### Prerequisites
1. **GitHub Repository**: Push your code to GitHub
2. **Render Account**: Sign up at https://render.com
3. **Environment Variables**: Prepare your secrets

### Environment Variables Required
```
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key  
GEMINI_API_KEY=your_google_gemini_api_key
ENVIRONMENT=production
```

## 📋 Deployment Steps

### 1. Connect GitHub to Render
1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Select the repository: `vietnamese-stock-analyzer`

### 2. Configure Service
- **Name**: vietnamese-stock-analyzer
- **Environment**: Python 3
- **Build Command**: (auto-detected from render.yaml)
- **Start Command**: (auto-detected from render.yaml)
- **Plan**: Free (or Starter for better performance)

### 3. Set Environment Variables
In Render dashboard → Service → Environment:
```
SUPABASE_URL = your_supabase_url
SUPABASE_SERVICE_ROLE_KEY = your_service_role_key
GEMINI_API_KEY = your_gemini_api_key
ENVIRONMENT = production
```

### 4. Deploy
- Render will automatically build and deploy
- Monitor logs for any issues
- Health check available at: `https://your-app.onrender.com/health`

## 🔄 Rollback Procedures

### Method 1: Git Revert (Recommended)
```bash
# 1. Find the problematic commit
git log --oneline -10

# 2. Revert to previous working commit
git revert <commit-hash>

# 3. Push the revert
git push origin main

# 4. Render will auto-deploy the reverted version
```

### Method 2: Reset to Previous Commit
```bash
# 1. Reset to previous commit (DANGEROUS - rewrites history)
git reset --hard <previous-commit-hash>

# 2. Force push (use with caution)
git push origin main --force

# 3. Render will deploy the reset version
```

### Method 3: GitHub Releases (Best Practice)
```bash
# 1. Create releases for stable versions
git tag -a v1.0.0 -m "Stable release v1.0.0"
git push origin v1.0.0

# 2. In Render, set to deploy from specific tag
# Dashboard → Service → Settings → Deploy from tag: v1.0.0

# 3. To rollback, change deploy branch to previous tag
```

### Method 4: Render Manual Rollback
1. Go to Render Dashboard → Your Service
2. Click on "Deploys" tab
3. Find a previous successful deployment
4. Click "Redeploy" on that version

## 🏥 Health Monitoring

### Health Check Endpoint
```
GET https://your-app.onrender.com/health
```

**Healthy Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "database": "healthy",
  "version": "1.0.0",
  "environment": "production"
}
```

**Unhealthy Response:** (503 status)
```json
{
  "status": "unhealthy", 
  "timestamp": "2024-01-01T12:00:00",
  "error": "Database connection failed",
  "version": "1.0.0"
}
```

### Monitoring Commands
```bash
# Check health status
curl https://your-app.onrender.com/health

# Monitor logs (in Render dashboard)
# Service → Logs tab → Live logs

# Check deployment status
# Service → Deploys tab
```

## 🚨 Emergency Rollback Checklist

### When to Rollback
- [ ] Health check returning 503 errors
- [ ] Database connection failures
- [ ] Critical API endpoints not responding  
- [ ] Selenium/Chrome issues preventing crawling
- [ ] Memory/performance issues

### Emergency Steps
1. **Immediate**: Use Render manual rollback (fastest)
2. **Git Revert**: Create revert commit and push
3. **Check Health**: Verify previous version is working
4. **Investigate**: Debug issue in development
5. **Fix Forward**: Create proper fix and deploy

### Rollback Verification
- [ ] Health check returns 200 OK
- [ ] Main dashboard loads successfully
- [ ] Can access technical documentation
- [ ] Stock analysis functionality works
- [ ] Database queries execute properly

## 📊 Deployment Monitoring

### Key Metrics to Watch
- **Response Time**: Should be < 3 seconds
- **Memory Usage**: Monitor for memory leaks
- **Error Rate**: Should be < 1%
- **Health Check**: Should return 200 consistently

### Log Monitoring
```bash
# Important log patterns to watch:
# ✅ "Application startup complete"
# ⚠️ "Database connection error" 
# ❌ "Chrome WebDriver failed"
# ❌ "Gemini API error"
```

## 🔧 Troubleshooting Common Issues

### Issue 1: Chrome/Selenium Not Working
```
Error: Chrome binary not found
```
**Solution**: Check Dockerfile Chrome installation

### Issue 2: Database Connection Failed
```
Error: Database connection timeout
```
**Solution**: Verify SUPABASE_URL and keys

### Issue 3: Gemini API Errors
```
Error: Gemini API key invalid
```
**Solution**: Check GEMINI_API_KEY in environment

### Issue 4: Memory Issues
```
Error: Memory limit exceeded
```
**Solution**: Upgrade to Starter plan or optimize code

## 🏷️ Version Management

### Tagging Strategy
```bash
# Major release (new features)
git tag -a v1.0.0 -m "Major release with new features"

# Minor release (improvements)  
git tag -a v1.1.0 -m "Minor improvements and bug fixes"

# Patch release (bug fixes)
git tag -a v1.1.1 -m "Critical bug fixes"

# Push tags
git push origin --tags
```

### Branch Strategy
- **main**: Production-ready code
- **develop**: Development integration
- **feature/***: Feature branches
- **hotfix/***: Emergency fixes

## 📞 Support Contacts

### When Deployment Fails
1. Check Render service logs
2. Verify environment variables
3. Test health endpoint
4. Check GitHub Actions (if configured)
5. Contact development team

### Emergency Contacts
- **Technical Lead**: Check system health
- **DevOps**: Infrastructure issues
- **Database Admin**: Supabase issues

---

## Quick Commands Reference

```bash
# Deploy new version
git add .
git commit -m "Your changes"
git push origin main

# Emergency rollback
git revert HEAD
git push origin main

# Check deployment status
curl https://your-app.onrender.com/health

# View recent commits
git log --oneline -10
```