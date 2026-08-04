import os
from typing import Any
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Cambiá esta consulta según lo que quieras limpiar.
def seleccionar_consulta() -> str:
    print("\n¿Qué correos querés consultar?")
    print("1. Promociones antiguas")
    print("2. Redes sociales antiguas")
    print("3. Correos leídos antiguos")
    print("4. Correos grandes y antiguos")
    print("5. Correos de un remitente")
    print("6. Correos anteriores a una fecha")
    print("7. Escribir una consulta personalizada")

    opcion = input("\nElegí una opción del 1 al 7: ").strip()

    if opcion == "1":
        meses = input(
            "¿Con más de cuántos meses? Ejemplo: 6: "
        ).strip()

        meses = meses or "6"

        return (
            f"category:promotions older_than:{meses}m "
            "-is:starred -is:important"
        )

    if opcion == "2":
        meses = input(
            "¿Con más de cuántos meses? Ejemplo: 12: "
        ).strip()

        meses = meses or "12"

        return (
            f"category:social older_than:{meses}m "
            "-is:starred -is:important"
        )

    if opcion == "3":
        meses = input(
            "¿Con más de cuántos meses? Ejemplo: 12: "
        ).strip()

        meses = meses or "12"

        return (
            f"is:read older_than:{meses}m "
            "-is:starred -is:important"
        )

    if opcion == "4":
        tamaño = input(
            "Tamaño mínimo en MB. Ejemplo: 10: "
        ).strip()

        meses = input(
            "¿Con más de cuántos meses? Ejemplo: 12: "
        ).strip()

        tamaño = tamaño or "10"
        meses = meses or "12"

        return (
            f"larger:{tamaño}M older_than:{meses}m "
            "-is:starred -is:important"
        )

    if opcion == "5":
        remitente = input(
            "Ingresá el correo o dominio del remitente: "
        ).strip()

        meses = input(
            "¿Con más de cuántos meses? Dejalo vacío para buscar todos: "
        ).strip()

        consulta = f"from:{remitente}"

        if meses:
            consulta += f" older_than:{meses}m"

        return consulta

    if opcion == "6":
            while True:
                fecha = input(
                    "Ingresá la fecha en formato AAAA/MM/DD: "
                ).strip()

                try:
                    datetime.strptime(fecha, "%Y/%m/%d")
                    return f"before:{fecha} -is:starred -is:important"

                except ValueError:
                    print(
                        "Fecha inválida. Ejemplo correcto: 2022/01/01"
                    )
    if opcion == "7":
        consulta = input(
            "Escribí la consulta de Gmail: "
        ).strip()

        if not consulta:
            raise ValueError("La consulta no puede estar vacía.")

        return consulta

    print("Opción inválida. Se buscarán promociones de más de 6 meses.")

    return (
        "category:promotions older_than:6m "
        "-is:starred -is:important"
    )

# True: solo muestra los correos.
# False: permite enviarlos a la papelera.
MODO_PRUEBA = False


def autenticar():
    credenciales = None

    if os.path.exists("token.json"):
        credenciales = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES,
        )

    if not credenciales or not credenciales.valid:
        if (
            credenciales
            and credenciales.expired
            and credenciales.refresh_token
        ):
            credenciales.refresh(Request())
        else:
            flujo = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES,
            )

            credenciales = flujo.run_local_server(port=0)

        with open("token.json", "w", encoding="utf-8") as archivo:
            archivo.write(credenciales.to_json())

    return build(
        "gmail",
        "v1",
        credentials=credenciales,
    )


def buscar_mensajes(servicio, consulta: str) -> list[dict[str, Any]]:
    mensajes = []
    siguiente_pagina = None

    while True:
        respuesta = (
            servicio.users()
            .messages()
            .list(
                userId="me",
                q=consulta,
                maxResults=500,
                pageToken=siguiente_pagina,
            )
            .execute()
        )

        mensajes.extend(respuesta.get("messages", []))

        siguiente_pagina = respuesta.get("nextPageToken")

        if not siguiente_pagina:
            break

    return mensajes


def obtener_encabezado(
    encabezados: list[dict[str, str]],
    nombre: str,
) -> str:
    for encabezado in encabezados:
        if encabezado.get("name", "").lower() == nombre.lower():
            return encabezado.get("value", "")

    return "(sin información)"


def mostrar_mensaje(servicio, message_id: str, numero: int) -> None:
    mensaje = (
        servicio.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        )
        .execute()
    )

    encabezados = mensaje.get("payload", {}).get("headers", [])

    remitente = obtener_encabezado(encabezados, "From")
    asunto = obtener_encabezado(encabezados, "Subject")
    fecha = obtener_encabezado(encabezados, "Date")

    print(f"\n{numero}. {asunto}")
    print(f"   De: {remitente}")
    print(f"   Fecha: {fecha}")


def enviar_a_papelera(servicio, mensajes: list[dict[str, Any]]) -> None:
    total = len(mensajes)

    for indice, mensaje in enumerate(mensajes, start=1):
        servicio.users().messages().trash(
            userId="me",
            id=mensaje["id"],
        ).execute()

        print(f"\rMoviendo a papelera: {indice}/{total}", end="")

    print()


def main() -> None:
    try:
        servicio = autenticar()
        consulta = seleccionar_consulta()

        print(f"\nConsulta seleccionada: {consulta}")
        print("Buscando mensajes...")

        mensajes = buscar_mensajes(servicio, consulta)


        if not mensajes:
            print("No se encontraron mensajes.")
            return

        print(f"Se encontraron {len(mensajes)} mensajes.")

        # Mostrar como máximo 20 ejemplos para evitar demasiadas consultas.
        for numero, mensaje in enumerate(mensajes[:20], start=1):
            mostrar_mensaje(
                servicio,
                mensaje["id"],
                numero,
            )

        if len(mensajes) > 20:
            print(f"\n...y {len(mensajes) - 20} mensajes más.")

        if MODO_PRUEBA:
            print("\nMODO PRUEBA activo.")
            print("No se modificó ningún correo.")
            print("Para continuar, cambiá MODO_PRUEBA a False.")
            return

        confirmacion = input(
            f"\n¿Enviar {len(mensajes)} mensajes a la papelera? "
            "Desea continuar con el proceso (y/n) "
        )

        if confirmacion != "y":
            print("Operación cancelada.")
            return

        enviar_a_papelera(servicio, mensajes)

        print("Proceso terminado.")
        print("Los mensajes están en la papelera de Gmail.")

    except FileNotFoundError:
        print("No se encontró credentials.json.")
        print("Colocalo en la misma carpeta que gmail_cleanup.py.")

    except HttpError as error:
        print(f"Error de Gmail API: {error}")

    except Exception as error:
        print(f"Error inesperado: {error}")


if __name__ == "__main__":
    main()