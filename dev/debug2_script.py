from http import client
from asyncua import ua

import lads_opcua_client as lads
import time
import pandas as pd


def process_server(conn):
    print(f"\n========== Processing Server: {conn.server.name} ==========")
    server = conn.server

    if not server.devices:
        print("No devices found on this server.")
        return

    device = server.devices[0]
    fun_unit = device.functional_units[0]

    # Исправленный момент с переменной
    # Используем .value для записи, чтобы библиотека синхронизировала значение с сервером
    try:
        var = fun_unit.functions[3].variables[3]
        print(f"\n--- Testing variable change on: {var.display_name} ---")

        a = var.value
        print(f"Old value: {a}")

        # Присваивание через .value вызывает автоматическую запись на сервер
        var.set_value(25.5)
        print(f"Set value requested: 25.5")

        # Небольшая пауза для завершения сетевой операции
        time.sleep(0.5)

        b = var.value
        print(f"New confirmed value: {b}")
    except Exception as e:
        print(f"Error changing variable: {e}")

    # --------------------- ВЫЗОВ ОПЕРАЦИИ (Метода) ---------------------
    if hasattr(fun_unit, 'functional_unit_state'):
        print(f"\n--- Calling method by name on: {fun_unit.unique_name} ---")

        try:
            method_to_call = "Aspirate" # Имя метода для вызова

            sm = fun_unit.functional_unit_state
            sm.call_async(sm.call_lads_method(method_to_call))

            print(f"✅ Found method '{method_to_call}'. Called successfully.")

            time.sleep(1)
        except Exception as e:
            print(f"Error calling {method_to_call}: {e}")

    print("\nServer details: ")
    print("Number of devices: ", len(server.devices))
    for device in server.devices:
        print("  Device: ", device.unique_name)


def main():
    urls = [
        "opc.tcp://eugen:62453/Pipette"
    ]

    connections = []

    # 1. Стартуем подключения одновременно
    print("Starting connections...")
    for url in urls:
        conn = lads.Connection(url=url)
        conn.connect()
        connections.append(conn)

    # 2. Ждем, пока оба инициализируются
    print("Waiting for connections to be initialized...")
    for conn in connections:
        while not conn.initialized:
            time.sleep(1)
        print(f"Connection initialized: True")

    # 3. Обрабатываем каждый сервер
    for conn in connections:
        try:
            process_server(conn)
        except Exception as e:
            print(f"Error processing server: {e}")

    # 4. Отключаемся
    for conn in connections:
        conn.disconnect()


if __name__ == '__main__':
    main()