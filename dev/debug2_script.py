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
    a = fun_unit.functions[1].current_state.data_value.Value
    print("\n--- Searching for 'Speed' variable ---")
    speed_var = None

    def find_in(obj, name, context_name):
        if hasattr(obj, "variables") and obj.variables:
            for v in obj.variables:
                if v.display_name == name:
                    print(f"Found '{name}' in {context_name}!")
                    return v
        return None

    speed_var = speed_var or find_in(devices[0], "Speed", "Device")
    speed_var = speed_var or find_in(fun_unit, "Speed", "FunctionalUnit")
    if hasattr(fun_unit, "functional_unit_state") and fun_unit.functional_unit_state:
        speed_var = speed_var or find_in(fun_unit.functional_unit_state, "Speed", "FunctionalUnitState")

    if hasattr(fun_unit, "function_set") and fun_unit.function_set and fun_unit.function_set.functions:
        for f in fun_unit.function_set.functions:
            speed_var = speed_var or find_in(f, "Speed", f"Function '{f.unique_name}'")

    if speed_var:
        print(f"SUCCESS: Speed variable loaded by LADS client! Current value: {speed_var.value}")
    else:
        print("FAILURE: Speed variable is NOT in any high-level LADS object's '.variables' list.")
        # Попытка достать напрямую
        try:
            raw_node = conn.server.client.get_node("ns=5;i=6164")
            val = raw_node.get_value() # This might be async, let's be careful. Wait, conn is sync wrapper in your client?
            # In your script, conn.server.client is likely standard asyncua. We need to be careful with async.
            print(f"But raw OPC UA node ns=5;i=6164 exists! (Raw read skipped to avoid async context errors)")
        except Exception as e:
            pass

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
                    "StartSpinning"
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
        "opc.tcp://eugen:62454/RobotArm"
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