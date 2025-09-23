#!/usr/bin/env python3
import argparse
import os
import sys
import time
from typing import Dict, List, Tuple, Set
import requests

REQUEST_TIMEOUT = 30


def build_base_url(device_url: str) -> str:
    if device_url.startswith(("http://", "https://")):
        return device_url.rstrip("/")
    return f"http://{device_url.rstrip('/')}"


def login(base_url: str, username: str, password: str) -> str:
    url = f"{base_url}/login.fcgi"
    resp = requests.post(url, json={"login": username, "password": password}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    session = data.get("session")
    if not session:
        raise RuntimeError(f"Falha no login: resposta sem 'session': {data}")
    return session


def load_users(base_url: str, session: str) -> List[Dict]:
    url = f"{base_url}/load_objects.fcgi?session={session}"
    payload = {
        "object": "users",
        "fields": ["id", "name", "registration"],
        "order_by": ["id"],
    }
    resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"Erro load_objects users: {resp.status_code} {resp.text}")
    return resp.json().get("users", [])


def load_groups(base_url: str, session: str) -> List[Dict]:
    url = f"{base_url}/load_objects.fcgi?session={session}"
    payload = {
        "object": "groups",
        "fields": ["id", "name"],
        "order_by": ["id"],
    }
    resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"Erro load_objects groups: {resp.status_code} {resp.text}")
    return resp.json().get("groups", [])


def load_user_groups(base_url: str, session: str) -> List[Dict]:
    url = f"{base_url}/load_objects.fcgi?session={session}"
    payload = {
        "object": "user_groups",
        "fields": ["user_id", "group_id"],
        "order_by": ["user_id", "group_id"],
    }
    resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"Erro load_objects user_groups: {resp.status_code} {resp.text}")
    return resp.json().get("user_groups", [])


def create_user_group(base_url: str, session: str, user_id: int, group_id: int) -> None:
    url = f"{base_url}/create_objects.fcgi?session={session}"
    payload = {
        "object": "user_groups",
        "values": [{"user_id": int(user_id), "group_id": int(group_id)}],
    }
    resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"Erro ao criar user_group ({user_id}, {group_id}): {resp.status_code} {resp.text}")


def destroy_user_group(base_url: str, session: str, user_id: int, group_id: int) -> None:
    url = f"{base_url}/destroy_objects.fcgi?session={session}"
    payload = {
        "object": "user_groups",
        "where": {"user_groups": {"user_id": int(user_id), "group_id": int(group_id)}},
    }
    resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"Erro ao deletar user_group ({user_id}, {group_id}): {resp.status_code} {resp.text}")


def destroy_group(base_url: str, session: str, group_id: int) -> None:
    url = f"{base_url}/destroy_objects.fcgi?session={session}"
    payload = {"object": "groups", "where": {"groups": {"id": int(group_id)}}}
    resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"Erro ao deletar group {group_id}: {resp.status_code} {resp.text}")


def load_user_roles(base_url: str, session: str) -> Set[int]:
    # Opcional: evita deletar administradores (role=1)
    url = f"{base_url}/load_objects.fcgi?session={session}"
    payload = {
        "object": "user_roles",
        "fields": ["user_id", "role"],
        "order_by": ["user_id"],
    }
    try:
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return set()
        roles = resp.json().get("user_roles", [])
        return {r["user_id"] for r in roles if int(r.get("role", 0)) == 1}
    except Exception:
        return set()


def destroy_user(base_url: str, session: str, user_id: int) -> None:
    url = f"{base_url}/destroy_objects.fcgi?session={session}"
    payload = {"object": "users", "where": {"users": {"id": int(user_id)}}}
    resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"Erro ao deletar user {user_id}: {resp.status_code} {resp.text}")


def pick_keep_and_delete(ids_sorted: List[int], keep: str) -> Tuple[int, List[int]]:
    if not ids_sorted:
        return None, []
    if keep == "oldest":
        keep_id = ids_sorted[0]
        return keep_id, ids_sorted[1:]
    else:
        keep_id = ids_sorted[-1]
        return keep_id, ids_sorted[:-1]


def find_duplicates_by_registration(users: List[Dict], keep: str) -> Tuple[Set[int], Set[int]]:
    kept, to_delete = set(), set()
    groups: Dict[str, List[int]] = {}
    for u in users:
        reg = (u.get("registration") or "").strip()
        if not reg:
            continue
        uid = int(u["id"])
        groups.setdefault(reg, []).append(uid)
    for reg, ids in groups.items():
        if len(ids) <= 1:
            kept.update(ids)
            continue
        ids_sorted = sorted(ids)
        keep_id, delete_ids = pick_keep_and_delete(ids_sorted, keep)
        kept.add(keep_id)
        to_delete.update(delete_ids)
    return kept, to_delete


def find_duplicates_by_name(users: List[Dict], keep: str, ignore_if_registration_diff: bool) -> Tuple[Set[int], Set[int]]:
    kept, to_delete = set(), set()
    groups: Dict[str, List[Tuple[int, str]]] = {}
    for u in users:
        name = (u.get("name") or "").strip()
        if not name:
            continue
        uid = int(u["id"])
        reg = (u.get("registration") or "").strip()
        groups.setdefault(name, []).append((uid, reg))

    for name, pairs in groups.items():
        if len(pairs) <= 1:
            kept.update(uid for uid, _ in pairs)
            continue

        if ignore_if_registration_diff:
            # Subagrupa por registration: só deduplica quando a registration é igual (ou ambas vazias)
            subgroups: Dict[str, List[int]] = {}
            for uid, reg in pairs:
                subgroups.setdefault(reg, []).append(uid)
            for reg, ids in subgroups.items():
                if len(ids) <= 1:
                    kept.update(ids)
                    continue
                ids_sorted = sorted(ids)
                keep_id, delete_ids = pick_keep_and_delete(ids_sorted, keep)
                kept.add(keep_id)
                to_delete.update(delete_ids)
        else:
            # Deduplica apenas por nome (atenção: pode apagar homônimos)
            ids = [uid for uid, _ in pairs]
            ids_sorted = sorted(ids)
            keep_id, delete_ids = pick_keep_and_delete(ids_sorted, keep)
            kept.add(keep_id)
            to_delete.update(delete_ids)
    return kept, to_delete


def main():
    parser = argparse.ArgumentParser(description="Remoção de usuários duplicados na catraca (Control iD)")
    parser.add_argument("--device-url", default=os.getenv("CATRAKA_URL", "http://localhost:8080"), help="URL/IP da catraca (ex: http://192.168.0.10)")
    parser.add_argument("--username", default=os.getenv("CATRAKA_USER", "admin"), help="Usuário de login na catraca")
    parser.add_argument("--password", default=os.getenv("CATRAKA_PASS", "admin"), help="Senha de login na catraca")

    parser.add_argument("--mode", choices=["registration", "name", "both"], default="both", help="Critério de deduplicação de usuários")
    parser.add_argument("--keep", choices=["oldest", "newest"], default="oldest", help="Qual manter dentro de cada grupo")
    parser.add_argument("--dry-run", action="store_true", help="Apenas mostra o que seria deletado")

    parser.add_argument("--safe-name-mode", action="store_true",
                        help="Deduplicar por nome somente quando a registration for igual (ou vazia em ambos). Recomendado.")
    parser.add_argument("--exclude-admins", action="store_true", help="Não apagar usuários administradores (user_roles.role = 1)")
    parser.add_argument("--dedupe-groups", action="store_true", help="Deduplicar grupos por nome (move user_groups e remove grupos duplicados)")

    args = parser.parse_args()

    base_url = build_base_url(args.device_url)

    try:
        print("> Efetuando login...")
        session = login(base_url, args.username, args.password)

        # Usuários
        print("> Carregando usuários...")
        users = load_users(base_url, session)
        print(f"> {len(users)} usuários carregados")

        admin_ids: Set[int] = set()
        if args.exclude_admins:
            print("> Carregando roles para excluir admins...")
            admin_ids = load_user_roles(base_url, session)
            print(f"> {len(admin_ids)} administradores detectados (excluídos da remoção)")

        ids_all = {int(u["id"]) for u in users if "id" in u}
        to_delete_final: Set[int] = set()
        kept_global: Set[int] = set()

        if args.mode in ("registration", "both"):
            kept_r, del_r = find_duplicates_by_registration(users, args.keep)
            kept_global |= kept_r
            to_delete_final |= del_r

        if args.mode in ("name", "both"):
            kept_n, del_n = find_duplicates_by_name(
                users,
                args.keep,
                ignore_if_registration_diff=args.safe_name_mode or True  # por segurança, default True
            )
            kept_global |= kept_n
            to_delete_final |= del_n

        # Nunca apaga administradores se solicitado
        if admin_ids:
            to_delete_final -= admin_ids

        # Segurança: não apaga o que não existe
        to_delete_final &= ids_all

        print(f"> Total a remover: {len(to_delete_final)} usuário(s)")
        if args.dry_run:
            preview = sorted(list(to_delete_final))[:50]
            print(f"> Dry-run: primeiros IDs a remover: {preview}{' ...' if len(to_delete_final) > 50 else ''}")
            # Continua para opcionalmente deduplicar grupos em dry-run

        # Execução usuários
        if not args.dry_run:
            errors = 0
            processed = 0
            for uid in sorted(to_delete_final):
                try:
                    destroy_user(base_url, session, uid)
                    processed += 1
                    if processed % 50 == 0:
                        print(f"> Removidos {processed} usuários...")
                except Exception as e:
                    print(f"! Erro removendo {uid}: {e}", file=sys.stderr)
                    errors += 1
                    time.sleep(0.1)
            print(f"> Remoção de usuários concluída. Sucesso: {processed}, Erros: {errors}")

        # Grupos
        if args.dedupe_groups:
            print("> Carregando grupos e vínculos usuário-grupo...")
            groups = load_groups(base_url, session)
            user_groups = load_user_groups(base_url, session)
            print(f"> {len(groups)} grupos, {len(user_groups)} vínculos")

            # Agrupa por nome
            groups_by_name: Dict[str, List[int]] = {}
            for g in groups:
                if not g.get("name"):
                    continue
                groups_by_name.setdefault(g["name"], []).append(int(g["id"]))

            total_groups_deleted = 0
            total_links_moved = 0

            for name, ids in groups_by_name.items():
                if len(ids) <= 1:
                    continue
                ids_sorted = sorted(ids)
                keep_id, delete_ids = pick_keep_and_delete(ids_sorted, args.keep)
                # Remapeia vínculos dos grupos duplicados para o keep_id
                for del_gid in delete_ids:
                    links = [ug for ug in user_groups if int(ug.get("group_id", -1)) == int(del_gid)]
                    for ug in links:
                        uid = int(ug.get("user_id"))
                        # evita duplicar vínculo
                        already = any((int(x.get("user_id")) == uid and int(x.get("group_id")) == keep_id) for x in user_groups)
                        if not args.dry_run:
                            try:
                                if not already:
                                    create_user_group(base_url, session, uid, keep_id)
                                    total_links_moved += 1
                                # remove vínculo antigo
                                destroy_user_group(base_url, session, uid, del_gid)
                            except Exception as e:
                                print(f"! Erro remapeando vínculo ({uid}, {del_gid})->({uid}, {keep_id}): {e}", file=sys.stderr)
                        user_groups = [x for x in user_groups if not (int(x.get("user_id")) == uid and int(x.get("group_id")) == del_gid)]
                        if not already:
                            user_groups.append({"user_id": uid, "group_id": keep_id})
                    # Remove o grupo duplicado
                    if not args.dry_run:
                        try:
                            destroy_group(base_url, session, del_gid)
                            total_groups_deleted += 1
                        except Exception as e:
                            print(f"! Erro deletando grupo {del_gid}: {e}", file=sys.stderr)

            print(f"> Grupos deduplicados: removidos {total_groups_deleted}, vínculos movidos {total_links_moved}")

        return 0

    except Exception as e:
        print(f"! Falha: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())