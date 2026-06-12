# Hosting Guide: Ubuntu 24.04 (HTTP Only)

This guide walks you through hosting this IPTV Web Player application on a clean **Ubuntu 24.04 64-Bit** server with HTTP (port 80) enabled and HTTPS disabled. 

> [!NOTE]
> **Why HTTP only?**
> Modern browsers block mixed content. If the web player is loaded over HTTPS, the browser will block loading external HTTP-based `.m3u8` or `.ts` IPTV streams. Hosting the player over HTTP resolves this issue.

---

## Prerequisites
- A clean **Ubuntu 24.04** Server.
- Your server's public IP address.
- An SSH client (PowerShell, Command Prompt, or Terminal).

---

## Step 1: Push Automation Files to GitHub
Make sure the setup script and deploy workflow are pushed to your repository:
```bash
git add .github/workflows/deploy-ubuntu.yml setup-server.sh
git commit -m "chore: add deployment scripts"
git push origin main
```

---

## Step 2: Log into your Ubuntu Server
Connect to your server via SSH:
```bash
ssh username@your_server_ip
```
*(Replace `username` with `ubuntu` or `root`, and `your_server_ip` with your server's public IP).*

---

## Step 3: Run the Server Setup Script
On your server, create the setup script file, paste the contents of `setup-server.sh`, and run it.

1. Open a new file using nano:
   ```bash
   nano setup-server.sh
   ```
2. Copy the contents of the local `setup-server.sh` file, paste it into the server terminal, and save:
   - Press `Ctrl + O` then `Enter` to save.
   - Press `Ctrl + X` to exit the editor.
3. Make the script executable and run it:
   ```bash
   chmod +x setup-server.sh
   sudo ./setup-server.sh
   ```
4. **Input the domain/IP:** When prompted, enter your server's public IP address or domain name and press `Enter`. The script will configure Nginx, directories, and UFW firewall permissions.

---

## Step 4: Generate a Secure SSH Key for GitHub Actions
We need to allow GitHub to securely copy the compiled site files to the server.

1. On your server terminal, generate an SSH key:
   ```bash
   ssh-keygen -t ed25519 -C "github-actions"
   ```
   *Press `Enter` to save it to the default location and press `Enter` twice to skip the passphrase.*
2. Authorize the public key:
   ```bash
   cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   chmod 700 ~/.ssh
   ```
3. View the private key and copy it:
   ```bash
   cat ~/.ssh/id_ed25519
   ```
   *Copy the entire output block, including the `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----` tags.*

---

## Step 5: Save Secrets on GitHub
1. Go to your repository on GitHub.
2. Navigate to **Settings** > **Secrets and variables** > **Actions**.
3. Under the **Secrets** tab, click **New repository secret** and add:

| Secret Name | Value |
| :--- | :--- |
| `SSH_HOST` | Your server's public IP address (e.g. `123.45.67.89`) |
| `SSH_USER` | Your SSH login username (e.g. `ubuntu` or `root`) |
| `SSH_KEY` | The contents of the private key copied in Step 4 |

---

## Step 6: Verify the Automated Deployment
1. Go to the **Actions** tab on your GitHub repository.
2. Select the **Build and Deploy to Ubuntu Server** workflow.
3. Click on the most recent run (or trigger a new commit/run) and verify it builds successfully and transfers files to the server.
4. Visit `http://your_server_ip` in your browser. The IPTV web player should load successfully and be able to play your IPTV stream URLs over HTTP.
