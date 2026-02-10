# Ubuntu VPS Deployment Guide

Follow this guide to set up and run this python application on any Ubuntu VPS server using PM2, ensuring process run 24/7.

### 1. Install Node.js & PM2

```bash
sudo apt install nodejs npm -y
sudo npm install -g pm2
```

Verify PM2:

```bash
pm2 --version
```

### 2. Installing Python Dependencies

Install dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt --break-system-packages
```

### 3. Setting Up Environment Variables

Create a `.env` file in the project root:

```bash
nano .env
```

Add the following (replace placeholders with real values):

```env
TV_ACCOUNT_ID = TradingView broker account ID
TV_SESSION_ID = TradingView session ID
```

Save & exit: `Ctrl + S` → `Ctrl + X`

### 4. Start the Main Python App

```bash
pm2 start main.py --name main --interpreter=python3
```

### 7. PM2 Process Management Commands

View running processes:

```bash
pm2 ls
```

Restart processes:

```bash
pm2 restart main
```

Stop processes:

```bash
pm2 stop main
```

Delete processes:

```bash
pm2 delete main
```

View logs (max 100 lines):

```bash
pm2 logs main --lines 100
```

_Note: After every update of environment variables, kindly restart the process:_ `pm2 restart all`
