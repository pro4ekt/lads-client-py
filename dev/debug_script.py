from http import client
from asyncua import ua

import lads_opcua_client as lads
import time

def call_device_method(conn, device_name, method_name, delay=2):
    print(f"\n[{device_name}] Initiating '{method_name}'...")
    try:
        server = conn.server
        # Получаем первый функциональный блок первого устройства
        fun_unit = server.devices[0].functional_units[0]

        if hasattr(fun_unit, 'functional_unit_state'):
            fun_unit.functional_unit_state.call_async(
                fun_unit.functional_unit_state.call_lads_method(method_name)
            )
            print(f"[{device_name}] ✅ Successfully called '{method_name}'!")
        else:
            print(f"[{device_name}] ❌ Device doesn't have functional_unit_state to call methods.")
    except Exception as e:
        print(f"[{device_name}] ❌ Error calling '{method_name}': {e}")

    # Имитируем время выполнения действия
    time.sleep(delay)

def main():
    server_urls = {
        "Centrifuge": "opc.tcp://eugen:62452/Centrifuge",
        "Pipette": "opc.tcp://eugen:62453/Pipette",
        "RobotArm": "opc.tcp://eugen:62454/RobotArm"
    }

    connections = {}

    # 1. Стартуем подключения одновременно
    print("Starting connections to servers...")
    for name, url in server_urls.items():
        conn = lads.Connection(url=url)
        conn.connect()
        connections[name] = conn

    # 2. Ждем инициализации всех серверов
    print("Waiting for all connections to be initialized...")
    for name, conn in connections.items():
        while not conn.initialized:
            time.sleep(1)
        print(f"[{name}] Connection initialized!")

    print("\n==================================")
    print("      STARTING WORKFLOW")
    print("==================================")

    # 3. Выполняем шаги по порядку
    # 1. RobotArm - MoveToA
    call_device_method(connections["RobotArm"], "RobotArm", "MoveToA")
    # 2. RobotArm - MoveStop
    call_device_method(connections["RobotArm"], "RobotArm", "MoveStop")

    # 3. Pipette - StartPipetting
    call_device_method(connections["Pipette"], "Pipette", "StartPipetting")
    # 4. Pipette - StopPipetting
    call_device_method(connections["Pipette"], "Pipette", "StopPipetting")

    # 5. RobotArm - MoveToCentrifuge
    call_device_method(connections["RobotArm"], "RobotArm", "MoveToCentrifuge")

    # 6. Centrifuge - StartSpinning
    call_device_method(connections["Centrifuge"], "Centrifuge", "StartSpinning")
    # 7. Centrifuge - StopSpinning
    call_device_method(connections["Centrifuge"], "Centrifuge", "StopSpinning")

    # 8. RobotArm - MoveToB
    call_device_method(connections["RobotArm"], "RobotArm", "MoveToB")
    # 9. RobotArm - MoveStop
    call_device_method(connections["RobotArm"], "RobotArm", "MoveStop")

    print("\n==================================")
    print("      WORKFLOW COMPLETED")
    print("==================================")

    # 4. Отключаемся корректно
    for name, conn in connections.items():
        print(f"Disconnecting {name}...")
        conn.disconnect()

if __name__ == '__main__':
    main()
