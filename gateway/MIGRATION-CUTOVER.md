# Halo Migration Cutover Guide

Target: `100.83.133.110` (Tailscale)
Source: current machine
Date prepared: 2026-03-21

Everything is pre-staged on the target. Follow these steps in order.

## 1. Stop Source (this machine)

```bash
# Stop halo service
systemctl --user stop halo

# Stop fleet instances (if running)
pm2 stop all

# Verify nothing is running
systemctl --user status halo
docker ps  # should show no halo containers
```

## 2. Final Sync (catch any changes since initial transfer)

```bash
# From this machine — sync any state changes since the transfer
rsync -avz --exclude node_modules --exclude dist --exclude .venv \
  --exclude '*.pyc' --exclude __pycache__ \
  /home/mrkai/code/halo/ \
  mrkai@100.83.133.110:/home/mrkai/code/halo/

# Fleet (if applicable)
rsync -avz --exclude node_modules --exclude dist --exclude .venv \
  /home/mrkai/code/halfleet/ \
  mrkai@100.83.133.110:/home/mrkai/code/halfleet/
```

## 3. Start Target

SSH into the target or run from here:

```bash
ssh mrkai@100.83.133.110

# Ensure logs directory exists
mkdir -p /home/mrkai/code/halo/logs

# Start halo
systemctl --user start halo

# Verify it's running
systemctl --user status halo
# Look for "Active: active (running)"

# Check logs for startup
tail -f /home/mrkai/code/halo/logs/halo.log
# Wait for "Connected to Telegram" or similar
```

## 4. Start Fleet (if using multi-agent)

```bash
export PATH=$HOME/.npm-global/bin:$PATH

# Start each fleet instance
cd /home/mrkai/code/halfleet
pm2 start microhal-ben/ecosystem.config.cjs
pm2 start microhal-dad/ecosystem.config.cjs
pm2 start microhal-mum/ecosystem.config.cjs
pm2 start microhal-gains/ecosystem.config.cjs
pm2 start microhal-money/ecosystem.config.cjs

# Verify
pm2 list
```

Note: Fleet instances need `npm install && npm run build` in each
`microhal-*/halo/` directory first if not already built:

```bash
for inst in microhal-*/halo; do
  npm --prefix "$inst" install && npm --prefix "$inst" run build
done
```

## 5. Verify

```bash
# Send a test message to @HAL via Telegram
# Check it responds

# Verify cron is running
crontab -l | grep hal-briefing

# Verify Docker can spawn containers
docker run --rm halo-agent:latest echo "container OK"
```

## 6. Post-Cutover Cleanup (optional)

On the source machine, disable the service so it doesn't auto-start:

```bash
systemctl --user disable halo
```

## What's Where on Target

| Component | Location |
|---|---|
| Service | `systemctl --user {start,stop,status} halo` |
| Logs | `/home/mrkai/code/halo/logs/halo.log` |
| .env (tokens) | `/home/mrkai/code/halo/.env` |
| SQLite | `/home/mrkai/code/halo/store/*.db` |
| Memory | `/home/mrkai/code/halo/memory/` |
| Fleet | `/home/mrkai/code/halfleet/microhal-*` |
| Crontab | `crontab -l` (5 jobs) |
| Docker image | `halo-agent:latest` (2.98GB) |
| PM2 | `$HOME/.npm-global/bin/pm2` |
| Config | `~/.config/halo/` |
| Gmail OAuth | `~/.gmail-mcp/` |
| Claude creds | `~/.claude/.credentials.json` |

## Rollback

If something goes wrong, stop the target and restart the source:

```bash
# On target
ssh mrkai@100.83.133.110 "systemctl --user stop halo"

# On source (this machine)
systemctl --user start halo
```
