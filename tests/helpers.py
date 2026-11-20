"""Small helpers shared by the API tests."""

import json


def post_json(client, url, body):
    data = body if isinstance(body, str) else json.dumps(body)
    return client.post(url, data, content_type="application/json")


def put_json(client, url, body):
    return client.put(url, json.dumps(body), content_type="application/json")


def set_mode(client, target, mode):
    return put_json(client, f"/api/training/modes/{target}", {"mode": mode})
