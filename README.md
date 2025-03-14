# Monzo for Slack

Monzo for Slack is a Slack app that logs Monzo transactions to a Slack channel. 

## Setup

### Slack
1. Create a new Slack app [here](https://api.slack.com/apps) using the manifest in `manifest.yml`
2. Install the app to your workspace from the OAuth & Permissions page
3. Create a new channel or choose an existing one in Slack for the transactions to be logged to. Get the channel ID by right clicking on the channel in Slack and selecting "Copy link". The channel ID is the last part of the URL. (e.g. `C01B2AB3C4D`)
4. Create a new file called `.env` in the root of the project with the contents of the `.env.example` file and fill in the values for your Slack app & channel
5. Make sure to invite the app to the channel

### Monzo
1. Create a new OAuth client in the Monzo Developer Portal [here](https://developers.monzo.com/apps/new) with the redirect URL set to `https://YOUR_APP_URL/monzo/callback`. Confidential mode should be set to true.
2. Add the client ID and secret to the `.env` file

### In Slack
1. You'll get a DM from the app with a link to connect your Monzo account. Click the link and follow the instructions to connect your Monzo account to the app. You will need to authorise it inside the Monzo app as well as logging in.
2. That's it! All your transactions will now be logged to the channel you specified :D