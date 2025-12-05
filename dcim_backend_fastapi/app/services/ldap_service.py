from app.core.logger import app_logger


def ldap_authenticate(
    server_uri: str,
    base_dn: str,
    username: str,
    password: str,
    bind_dn: str,
    bind_password: str,
):
    # Lazy import - ldap3 is heavy and slows down startup
    from ldap3 import Server, Connection, ALL, SIMPLE
    from ldap3.core.exceptions import LDAPException
    
    try:
        # Connect to AD server
        server = Server(server_uri, get_info=ALL)

        # Bind using service account
        conn = Connection(
            server,
            user=bind_dn,
            password=bind_password,
            authentication=SIMPLE,
            auto_bind=True
        )

        #  AD-style search using sAMAccountName
        search_filter = f"(sAMAccountName={username})"

        conn.search(
            search_base=base_dn,
            search_filter=search_filter,
            attributes=["distinguishedName"]
        )

        if len(conn.entries) == 0:
            return False, None  # No user found

        user_dn = conn.entries[0].entry_dn

        # Bind as the actual user with the entered password
        user_conn = Connection(
            server,
            user=user_dn,
            password=password,
            authentication=SIMPLE
        )

        if not user_conn.bind():
            return False, None  # Wrong password

        return True, user_dn

    except LDAPException as exc:
        app_logger.exception(
            "LDAP authentication error",
            extra={"username": username, "server": server_uri, "base_dn": base_dn},
        )
        return False, None
