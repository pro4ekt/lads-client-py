from http import client
from asyncua import ua

import lads_opcua_client as lads
import time
import pandas as pd


def find_current_state_variable(fun_unit):
    """
    Пытается найти переменную CurrentState в функциональном юните.
    Сначала ищет в корне, затем в контроллерах (functions).
    """
    # 1. Проверяем корень самого юнита (через свойство библиотеки)
    if fun_unit.current_state:
        return fun_unit.current_state

    # 2. Если в корне нет, ищем во вложенных функциях (контроллерах)
    for function in fun_unit.functions:
        # У многих LADS-функций есть свойство current_state (BaseStateMachineFunction)
        if hasattr(function, 'current_state') and function.current_state:
            return function.current_state

    return None


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
        var = fun_unit.functions[3].variables[2]
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
            target_state = "Complete"

            sm = fun_unit.functional_unit_state
            state_var = find_current_state_variable(fun_unit)

            if sm and state_var:
                initial_state = state_var.value_str.strip()
                last_seen_state = initial_state

                # Вызываем метод
                sm.call_async(sm.call_lads_method(method_to_call))
                print(f"✅ Method '{method_to_call}' initiated. Initial state: '{initial_state}'")

                start_time = time.time()
                timeout = 30

                while True:
                    current_state = state_var.value_str.strip()

                    # Печатаем при изменении состояния
                    if current_state != last_seen_state:
                        print(f"🔄 State changed: '{last_seen_state}' ➔ '{current_state}'")
                        last_seen_state = current_state

                    # Проверка завершения
                    if current_state == target_state:
                        print(f"✨ COMPLETED! (State: {current_state})")
                        break

                    if time.time() - start_time > timeout:
                        print(f"⚠️ Timeout! Last state: '{current_state}'")
                        break

                    time.sleep(0.2)
            else:
                print(f"❌ Error: StateMachine or CurrentState not found")

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