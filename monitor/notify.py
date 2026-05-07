"""Optional webhook notification for monitor alerts."""
import os
import json
import urllib.request


def post_alert(summary: str) -> bool:
    """Post alert to Slack or Discord if webhook is configured."""
    slack_url = os.environ.get("SLACK_WEBHOOK")
    discord_url = os.environ.get("DISCORD_WEBHOOK")

    sent = False

    if slack_url:
        try:
            payload = json.dumps({"text": f":rotating_light: *StocksBrain Alert*\n{summary}"}).encode()
            req = urllib.request.Request(slack_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=10)
            print("ALERT POSTED to Slack")
            sent = True
        except Exception as e:
            print(f"Slack notify error: {e}")

    if discord_url:
        try:
            payload = json.dumps({"content": f"**StocksBrain Alert**\n{summary}"}).encode()
            req = urllib.request.Request(discord_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=10)
            print("ALERT POSTED to Discord")
            sent = True
        except Exception as e:
            print(f"Discord notify error: {e}")

    if not sent:
        print("ALERT POSTED (no webhook configured — check GitHub Issues)")

    return sent
