// pm2 ecosystem config template for microHAL instances.
//
// This file is a TEMPLATE showing the structure. halctl generates
// per-instance configs at: halfleet/microhal-<name>/ecosystem.config.js
//
// Usage:
//   pm2 start halfleet/microhal-ben/ecosystem.config.js
//   pm2 stop microhal-ben
//   pm2 delete microhal-ben && pm2 start <config>  # for env changes

module.exports = {
  apps: [{
    name: "microhal-INSTANCE_NAME",
    cwd: "/home/mrkai/code/halfleet/microhal-INSTANCE_NAME/nanoclaw",
    script: "npm",
    args: "start",
    env: {
      NODE_ENV: "production",
      TELEGRAM_BOT_TOKEN_ENV: "MICROHAL_INSTANCE_NAME_BOT_TOKEN",
      MICROHAL_NAME: "INSTANCE_NAME",
    },
    watch: false,
    autorestart: true,
    max_restarts: 10,
    restart_delay: 5000,
  }],
};
