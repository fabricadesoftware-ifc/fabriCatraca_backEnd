#!/usr/bin/env python3

import argparse
import json
import os
import sys
import requests

REQUEST_TIMEOUT = 30


def build_base_url(device_url):
    if device_url.startswith(("http://", "https://")):
        return device_url.rstrip("/")
    return f"http://{device_url.rstrip('/')}"


def login(base_url, username, password):
    resp = requests.post(
        f"{base_url}/login.fcgi",
        json={"login": username, "password": password},
        timeout=REQUEST_TIMEOUT,
    )

    resp.raise_for_status()

    data = resp.json()

    if "session" not in data:
        raise RuntimeError(f"Falha no login: {data}")

    return data["session"]


def load_object(base_url, session, object_name, fields=None):
    url = f"{base_url}/load_objects.fcgi?session={session}"

    payload = {"object": object_name}

    if fields:
        payload["fields"] = fields

    resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)

    resp.raise_for_status()

    return resp.json()


def print_result(title, data):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)

    print(json.dumps(data, indent=4, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="Consulta objetos da catraca Control iD"
    )

    parser.add_argument(
        "--device-url", default=os.getenv("CATRAKA_URL", "http://191.52.62.21")
    )

    parser.add_argument("--username", default=os.getenv("CATRAKA_USER", "admin"))

    parser.add_argument("--password", default=os.getenv("CATRAKA_PASS", "admin"))

    parser.add_argument("--users", action="store_true")
    parser.add_argument("--groups", action="store_true")
    parser.add_argument("--user-groups", action="store_true")
    parser.add_argument("--user-roles", action="store_true")
    parser.add_argument("--all", action="store_true")

    args = parser.parse_args()

    try:
        base_url = build_base_url(args.device_url)

        print("Efetuando login...")
        session = login(base_url, args.username, args.password)

        if args.all:
            args.users = True
            args.groups = True
            args.user_groups = True
            args.user_roles = True

        if args.users:
            data = load_object(base_url, session, "users")
            print_result("USERS", data)

        if args.groups:
            data = load_object(base_url, session, "groups")
            print_result("GROUPS", data)

        if args.user_groups:
            data = load_object(base_url, session, "user_groups")
            print_result("USER_GROUPS", data)

        if args.user_roles:
            data = load_object(base_url, session, "user_roles")
            print_result("USER_ROLES", data)

        return 0

    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
