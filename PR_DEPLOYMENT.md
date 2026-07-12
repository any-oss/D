# PR Deployment Guide

## Overview

This repository now supports automatic deployment for Pull Requests. When a PR is opened or updated, the CI/CD pipeline will:

1. **Build** a Docker image tagged with the PR number
2. **Run security scans** using Trivy
3. **Execute tests** with coverage reporting
4. **Deploy to preview environment** (when labeled)
5. **Comment on the PR** with deployment status

---

## Workflow Trigger Conditions

### Automatic Build & Scan (All PRs)
- ✅ Triggered on: `opened`, `synchronize`, `reopened`
- ✅ Builds Docker image with tag: `pr-{PR_NUMBER}-{SHA}`
- ✅ Runs Trivy security scan
- ✅ Executes pytest test suite
- ✅ Comments PR with image information

### Full Preview Deployment (Labeled PRs)
- ✅ Requires label: `deploy-preview`
- ✅ Deploys to preview environment
- ✅ Creates GitHub Environment: `preview-pr-{PR_NUMBER}`
- ✅ Comments PR with deployment URL and status

---

## How to Use

### 1. Open a Pull Request

```bash
git checkout -b feature/my-feature
git commit -m "Add new feature"
git push origin feature/my-feature
# Create PR on GitHub
```

### 2. Wait for Automated Build

The workflow will automatically:
- Build the Docker image
- Run security scans
- Execute tests
- Comment on your PR with the image tag

### 3. Request Preview Deployment (Optional)

Add the `deploy-preview` label to your PR:

```bash
# Via GitHub UI: Add label "deploy-preview"
# Or via CLI with GitHub CLI:
gh pr edit <PR_NUMBER> --add-label deploy-preview
```

### 4. Access Preview Environment

Once deployed, check the PR comments for:
- **Docker Image**: `ghcr.io/owner/repo:pr-123-abc1234`
- **Preview URL**: `https://pr-123.preview.example.com`
- **Environment Name**: `preview-pr-123`

---

## Docker Image Tags

| Tag Pattern | Example | Description |
|-------------|---------|-------------|
| `pr-{NUMBER}-{SHA}` | `pr-42-a1b2c3d` | PR-specific build |
| `pr-{NUMBER}-latest` | `pr-42-latest` | Latest build for PR |
| `main` | `main` | Main branch build |
| `v{VERSION}` | `v1.1.0` | Release tag build |

---

## Preview Environment Lifecycle

- **Created**: When `deploy-preview` label is added
- **Updated**: On every PR update with the label
- **Destroyed**: When PR is closed or merged (manual cleanup required)

### Cleanup After Merge

```bash
# Remove preview environment
kubectl delete deployment api-pr-42
kubectl delete service api-pr-42
kubectl delete namespace preview-pr-42

# Or via Terraform/Helm depending on your setup
```

---

## Configuration

### Required Secrets

Configure these in your GitHub repository settings:

| Secret | Description |
|--------|-------------|
| `GITHUB_TOKEN` | Auto-provided by GitHub Actions |
| `DEPLOY_KEY` | SSH key for deployment (if needed) |
| `KUBE_CONFIG` | Kubernetes config (if deploying to K8s) |
| `PREVIEW_HOST` | Preview environment hostname |

### Customize Deployment

Edit `.github/workflows/pr-deploy.yml`:

```yaml
deploy-preview:
  steps:
    - name: Deploy to Preview Environment
      run: |
        # Replace with your deployment commands
        kubectl set image deployment/api api=ghcr.io/${{ github.repository }}:${{ steps.meta.outputs.tags }}
        # OR
        helm upgrade --install pr-${{ github.event.pull_request.number }} ./charts/api \
          --set image.tag=${{ steps.meta.outputs.tags }} \
          --namespace preview-pr-${{ github.event.pull_request.number }}
```

---

## Testing Locally

Test the PR deployment workflow locally before pushing:

```bash
# Install act (GitHub Actions runner)
brew install act

# Run the workflow locally
act -j build-and-push
act -j security-scan
act -j test
act -j deploy-preview
```

---

## Troubleshooting

### Build Fails
1. Check GitHub Actions logs
2. Verify Dockerfile syntax
3. Ensure all dependencies are in `requirements.txt`

### Security Scan Fails
1. Review Trivy results in GitHub Security tab
2. Fix critical/high vulnerabilities
3. Update base image if needed

### Deployment Fails
1. Check environment configuration
2. Verify secrets are set correctly
3. Review deployment logs in GitHub Actions

### Label Not Triggering
1. Ensure label is exactly `deploy-preview`
2. Re-add the label to trigger workflow
3. Check workflow permissions

---

## Best Practices

1. **Use descriptive PR titles** for easier identification
2. **Add `deploy-preview` label only when needed** to save resources
3. **Review security scan results** before merging
4. **Clean up preview environments** after merging
5. **Test critical changes** in preview before production

---

## Example PR Comment

When a PR is opened, you'll receive a comment like:

```markdown
## 🚀 PR Deployment Ready

### Docker Image Built
- **Image**: `ghcr.io/owner/repo:pr-42-a1b2c3d`
- **SHA**: `a1b2c3d`
- **PR**: #42

### Next Steps
1. Deploy to preview environment using:
   ```bash
   docker run -p 8000:8000 ghcr.io/owner/repo:pr-42-a1b2c3d
   ```
2. Or deploy to Kubernetes/Staging with this image tag

---
*Automated by PR Deploy Workflow*
```

After deployment with `deploy-preview` label:

```markdown
## ✅ Preview Deployment Successful

Your PR has been deployed to the preview environment!

**Environment**: preview-pr-42
**URL**: https://pr-42.preview.example.com
**Image**: `ghcr.io/owner/repo:pr-42-a1b2c3d`

The preview will be automatically destroyed when the PR is closed or merged.
```

---

## Related Workflows

- **CD Pipeline** (`.github/workflows/cd.yml`): Deploys main branch to production
- **PR Deploy** (`.github/workflows/pr-deploy.yml`): Deploys PRs to preview

For questions, see the [PRODUCTION_CHECKLIST.md](./PRODUCTION_CHECKLIST.md) or open an issue.
