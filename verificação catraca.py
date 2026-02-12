import psycopg2
from datetime import datetime


DB_CONFIG = {
    "host": "localhost",
    "database": "door_db",
    "user": "postgres",
    "password": "sua_senha",
}


def conectar():
    return psycopg2.connect(**DB_CONFIG)


def dentro_do_periodo(begin, end):
    agora = datetime.now().timestamp()

    if begin and begin > 0 and agora < begin:
        return False, "Usuário ainda não está válido"
    if end and end > 0 and agora > end:
        return False, "Usuário expirado"

    return True, "Usuário dentro da validade"


def verificar_horario(conn, access_rule_id):
    cur = conn.cursor()

    cur.execute(
        """
        SELECT tz.id
        FROM access_rule_time_zones artz
        JOIN time_zones tz ON tz.id = artz.time_zone_id
        WHERE artz.access_rule_id = %s
    """,
        (access_rule_id,),
    )

    zonas = cur.fetchall()

    if not zonas:
        return True, "Regra sem restrição de horário"

    agora = datetime.now()
    segundos_dia = agora.hour * 3600 + agora.minute * 60 + agora.second
    dia_semana = agora.weekday()  # 0=segunda

    for zona in zonas:
        cur.execute(
            """
            SELECT start, "end", sun, mon, tue, wed, thu, fri, sat
            FROM time_spans
            WHERE time_zone_id = %s
        """,
            (zona[0],),
        )

        spans = cur.fetchall()

        for span in spans:
            start, end, sun, mon, tue, wed, thu, fri, sat = span

            dias = [mon, tue, wed, thu, fri, sat, sun]

            if dias[dia_semana] == 1:
                if start <= segundos_dia <= end:
                    return True, "Dentro do horário permitido"

    return False, "Fora do horário permitido"


def verificar_acesso(user_id, portal_id):
    conn = conectar()
    cur = conn.cursor()

    print("\n==== INÍCIO DA VERIFICAÇÃO ====\n")

    # 1️⃣ Buscar usuário
    cur.execute(
        """
        SELECT id, name, begin_time, end_time
        FROM users
        WHERE id = %s
    """,
        (user_id,),
    )
    user = cur.fetchone()

    if not user:
        print("Usuário não encontrado.")
        return

    print(f"Usuário: {user[1]}")

    valido, msg = dentro_do_periodo(user[2], user[3])
    print(msg)

    if not valido:
        print("\n❌ ACESSO NEGADO")
        return

    # 2️⃣ Buscar regras do portal
    cur.execute(
        """
        SELECT ar.id, ar.name, ar.type
        FROM portal_access_rules par
        JOIN access_rules ar ON ar.id = par.access_rule_id
        WHERE par.portal_id = %s
    """,
        (portal_id,),
    )

    regras = cur.fetchall()

    if not regras:
        print("Portal não possui regras.")
        return

    print("\nRegras do portal:")
    for r in regras:
        print(f"- {r[1]} (Tipo: {'BLOQUEIO' if r[2] == 0 else 'LIBERAÇÃO'})")

    # 3️⃣ Verificar regras de bloqueio primeiro
    for r in regras:
        if r[2] == 0:
            horario_ok, motivo = verificar_horario(conn, r[0])
            if horario_ok:
                print(f"\nRegra de BLOQUEIO ativada: {r[1]}")
                print("❌ ACESSO NEGADO")
                return

    # 4️⃣ Verificar regras de liberação
    for r in regras:
        if r[2] == 1:
            horario_ok, motivo = verificar_horario(conn, r[0])
            print(f"\nAnalisando regra {r[1]} → {motivo}")
            if horario_ok:
                print("✔ ACESSO CONCEDIDO")
                return

    print("\n❌ Nenhuma regra de liberação válida encontrada.")
    print("❌ ACESSO NEGADO")


if __name__ == "__main__":
    user_id = int(input("User ID: "))
    portal_id = int(input("Portal ID: "))
    verificar_acesso(user_id, portal_id)
