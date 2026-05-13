import time
import lads_opcua_client as lads


def find_target_value_variable(fun_unit, controller_name="VolumeController", var_name="TargetValue"):
    for function in fun_unit.functions:
        func_name = getattr(function, 'name', getattr(function, 'display_name', str(function)))
        if controller_name.lower() in func_name.lower():
            for var in function.variables:
                vname = getattr(var, 'name', getattr(var, 'display_name', str(var)))
                if var_name.lower() in vname.lower():
                    return var
    return None


def find_current_state_variable(fun_unit):
    if fun_unit.current_state:
        return fun_unit.current_state
    for function in fun_unit.functions:
        if hasattr(function, 'current_state') and function.current_state:
            return function.current_state
    return None


def execute_and_wait(sm, state_var, method_name, timeout=45):
    print(f"\n---> Initiating method: {method_name}")
    sm.call_async(sm.call_lads_method(method_name))

    start_time = time.time()
    last_state = ""

    while time.time() - start_time < timeout:
        current_state = state_var.value_str.strip()

        if current_state != last_state:
            print(f"[State Machine]: {last_state} -> {current_state}")
            last_state = current_state

        if current_state == "Idle" and last_state != "":
            if time.time() - start_time > 1.0:
                print(f"[OK] Method '{method_name}' workflow completed.")
                return True

        time.sleep(0.2)

    print(f"[ERROR] Timeout waiting for method '{method_name}' to complete.")
    return False


def get_float_input(prompt_text):
    """
    Блокирующий запрос пользовательского ввода со строгой типизацией в float.
    """
    while True:
        try:
            user_input = input(prompt_text)
            return float(user_input)
        except ValueError:
            print("[ERROR] Введено нечисловое значение. Требуется тип Float (например, 25.5). Повторите ввод.")


def process_server(conn):
    print(f"\n========== Processing Server: {conn.server.name} ==========")
    server = conn.server

    if not server.devices:
        print("No devices found on this server.")
        return

    device = server.devices[0]
    fun_unit = device.functional_units[0]

    target_var = find_target_value_variable(fun_unit)
    state_var = find_current_state_variable(fun_unit)
    sm = fun_unit.functional_unit_state

    if not target_var or not state_var or not sm:
        print("Критическая ошибка: Необходимые узлы (TargetValue, CurrentState или StateMachine) не найдены.")
        return

    print("Начало выполнения Workflow...")

    # ШАГ 1: Набор жидкости (Aspirate)
    print("\n[Шаг 1] Подготовка к Aspirate")
    aspiration_volume = get_float_input("Введите объем для Aspirate (TargetValue): ")
    print(f"Установка TargetValue: {aspiration_volume}")
    target_var.set_value(aspiration_volume)
    time.sleep(0.5)
    execute_and_wait(sm, state_var, "Aspirate")

    # ШАГ 2: Сброс жидкости (Dispense)
    print("\n[Шаг 2] Подготовка к Dispense")
    dispense_target = get_float_input("Введите целевой объем для Dispense (TargetValue): ")
    print(f"Установка TargetValue: {dispense_target}")
    target_var.set_value(dispense_target)
    time.sleep(0.5)
    execute_and_wait(sm, state_var, "Dispense")

    # ШАГ 3: Сброс наконечника (EjectTip)
    print(f"\n[Шаг 3] Вызов EjectTip")
    execute_and_wait(sm, state_var, "EjectTip")

    # ШАГ 4: Захват нового наконечника (AttachTip)
    print(f"\n[Шаг 4] Вызов AttachTip")
    execute_and_wait(sm, state_var, "AttachTip")

    print("\n========== Workflow завершен ==========")


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