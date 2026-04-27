from http import client
from asyncua import ua

import lads_opcua_client as lads
import time
import pandas as pd

def process_server(conn):
    print(f"\n========== Processing Server: {conn.server.name} ==========")
    server = conn.server

    # Идем по иерархии (Сервер -> Устройство -> Функциональный блок)
    if not server.devices:
        print("No devices found on this server.")
        return

    devices = server.devices
    fu_list = devices[0].functional_units

    if not fu_list:
        print("No functional units found on device 0.")
        return

    fun_unit = fu_list[0]
    var_list = devices[0].variables
    
    # Чтобы изменить значение переменной, нам нужно её найти.
    try:
        target_i = 6018
        found_var = None

        # 1. Поищем сначала среди переменных самого FunctionalUnit
        if hasattr(fun_unit, "variables") and var_list:
            found_var = next((v for v in var_list if v.nodeid.Identifier == target_i), None)

        # 2. Применяем значение, если нашли
        if found_var:
            print(f"Found target variable: {found_var.display_name}, current value: {found_var.value}")
            print("Setting new value...")
            found_var.set_value("TestJob_999")
            time.sleep(1)
            print(f"New value expected to be requested. Observe if it changes.")
        else:
            print(f"Variable with NodeId {target_i} not found in this FunctionalUnit or its Functions.")

    except Exception as e:
        print(f"Error accessing functions/variables: {e}")

    # --------------------- ВЫЗОВ ОПЕРАЦИИ (Метода) ---------------------
    try:
        import dataclasses
        print("KeyValueType fields:", [f.name for f in dataclasses.fields(server.KeyValueType)])
        print("SampleInfoType fields:", [f.name for f in dataclasses.fields(server.SampleInfoType)])
    except Exception as e:
        print("Error inspecting types:", e)

    if hasattr(fun_unit, 'functional_unit_state'):
        print(f"\n--- Calling StartProgram on Functional Unit: {fun_unit.unique_name} ---")
        methods = fun_unit.functional_unit_state.method_names
        print(f"Available methods on FunctionalUnit: {list(methods)}")

        try:
            properties = ua.Variant([], ua.VariantType.ExtensionObject)
            samples = ua.Variant([], ua.VariantType.ExtensionObject)

            fun_unit.functional_unit_state.call_async(
                fun_unit.functional_unit_state.call_lads_method(
                    "StartProgram"
                )
            )

            print("Successfully called StartProgram via raw parameters!")
            time.sleep(1)
        except Exception as e:
            print(f"Error calling StartProgram: {e}")

    print("\nServer details: ")
    print("Number of devices: ", len(server.devices))
    for device in server.devices:
        print("  Device: ", device.unique_name)


def main():
    urls = [
        "opc.tcp://eugen:62451/LabWorkflow",
        "opc.tcp://eugen:62452/LabWorkflow2"
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
