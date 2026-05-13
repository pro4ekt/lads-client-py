import time
import lads_opcua_client as lads


def find_target_value_variable(fun_unit, controller_name="VolumeController", var_name="TargetValue"):
    """
    Семантический поиск переменной TargetValue внутри контроллера объема.
    Исключает ошибки смещения индексов при изменениях на сервере.
    """
    for function in fun_unit.functions:
        func_name = getattr(function, 'name', getattr(function, 'display_name', str(function)))
        if controller_name.lower() in func_name.lower():
            for var in function.variables:
                vname = getattr(var, 'name', getattr(var, 'display_name', str(var)))
                if var_name.lower() in vname.lower():
                    return var
    return None


def find_current_state_variable(fun_unit):
    """
    Поиск системной переменной CurrentState.
    """
    if fun_unit.current_state:
        return fun_unit.current_state
    for function in fun_unit.functions:
        if hasattr(function, 'current_state') and function.current_state:
            return function.current_state
    return None


def execute_and_wait(sm, state_var, method_name, timeout=45):
    """
    Вызывает метод и блокирует выполнение скрипта до тех пор,
    пока конечный автомат сервера не завершит работу (возврат в Idle).
    """
    print(f"\n---> Initiating method: {method_name}")
    sm.call_async(sm.call_lads_method(method_name))

    start_time = time.time()
    last_state = ""

    while time.time() - start_time < timeout:
        current_state = state_var.value_str.strip()

        if current_state != last_state:
            print(f"[State Machine]: {last_state} -> {current_state}")
            last_state = current_state

        # Как только сервер вернулся в Idle после выполнения команды - шаг завершен
        if current_state == "Idle" and last_state != "":
            # Дополнительная проверка, чтобы не сработать на Idle ДО начала выполнения
            # (предполагаем, что сервер успел перейти как минимум в Running или Complete)
            if time.time() - start_time > 1.0:
                print(f"✅ Method '{method_name}' workflow completed.")
                return True

        time.sleep(0.2)

    print(f"❌ Error: Timeout waiting for method '{method_name}' to complete.")
    return False


def process_server(conn):
    print(f"\n========== Processing Server: {conn.server.name} ==========")
    server = conn.server

    if not server.devices:
        print("No devices found on this server.")
        return

    device = server.devices[0]
    fun_unit = device.functional_units[0]

    # Инициализация узлов
    target_var = find_target_value_variable(fun_unit)
    state_var = find_current_state_variable(fun_unit)
    sm = fun_unit.functional_unit_state

    if not target_var or not state_var or not sm:
        print("Критическая ошибка: Необходимые узлы (TargetValue, CurrentState или StateMachine) не найдены.")
        return

    print("Начало выполнения Workflow...")

    # ШАГ 1: Набор жидкости (Aspirate)
    aspiration_volume = 50.0
    print(f"\n[Шаг 1] Установка TargetValue для Aspirate: {aspiration_volume}")
    target_var.set_value(aspiration_volume)
    time.sleep(0.5)  # Пауза для гарантии записи подписок
    execute_and_wait(sm, state_var, "Aspirate")

    # ШАГ 2: Сброс жидкости (Dispense)
    # Сбрасываем жидкость полностью (до 0.0)
    dispense_target = 0.0
    print(f"\n[Шаг 2] Установка TargetValue для Dispense: {dispense_target}")
    target_var.set_value(dispense_target)
    time.sleep(0.5)
    execute_and_wait(sm, state_var, "Dispense")

    # ШАГ 3: Сброс наконечника (EjectTip)
    print(f"\n[Шаг 3] Вызов EjectTip")
    execute_and_wait(sm, state_var, "EjectTip")

    # ШАГ 4: Захват нового наконечника (AttachTip)
    print(f"\n[Шаг 4] Вызов AttachTip")
    execute_and_wait(sm, state_var, "AttachTip")

    print("\n========== Workflow завершен успешно ==========")


def main():
    urls = [
        "opc.tcp://eugen:62453/Pipette"
    ]

    connections = []

    print("Starting connections...")
    for url in urls:
        conn = lads.Connection(url=url)
        conn.connect()
        connections.append(conn)

    print("Waiting for connections to be initialized...")
    for conn in connections:
        while not conn.initialized:
            time.sleep(1)
        print(f"Connection initialized: True")

    for conn in connections:
        try:
            process_server(conn)
        except Exception as e:
            print(f"Error processing server: {e}")

    for conn in connections:
        conn.disconnect()


if __name__ == '__main__':
    main()