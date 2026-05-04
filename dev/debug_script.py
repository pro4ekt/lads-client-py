import lads_opcua_client as lads
import time


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


def call_device_method_and_wait(conn, device_name, method_name, target_state="Idle", timeout=60):
    print(f"\n[{device_name}] 🚀 Initiating '{method_name}'...")
    try:
        server = conn.server
        fun_unit = server.devices[0].functional_units[0]

        # Объект с методами (Start, Stop, MoveToA и т.д.)
        sm = fun_unit.functional_unit_state
        # Находим переменную состояния с помощью нашей новой функции
        state_var = find_current_state_variable(fun_unit)

        if sm and state_var:
            initial_state = state_var.value_str.strip()

            # Вызываем метод
            sm.call_async(sm.call_lads_method(method_name))
            print(f"[{device_name}] ✅ Method called. Tracking state on: {state_var.browse_name.Name}")
            print(f"[{device_name}] ⏳ Initial state: '{initial_state}'. Waiting for '{target_state}'...")

            start_time = time.time()
            # Ждем начала движения (смены состояния)
            while state_var.value_str.strip() == initial_state:
                if time.time() - start_time > 5: break
                time.sleep(0.2)

            # Ждем завершения
            while True:
                current_state = state_var.value_str.strip()
                if current_state == target_state:
                    print(f"[{device_name}] ✨ COMPLETED! (State: {current_state})")
                    break
                if time.time() - start_time > timeout:
                    print(f"[{device_name}] ⚠️ Timeout! Last state: '{current_state}'")
                    break
                time.sleep(0.5)
        else:
            # Дебаг информация, если не нашли
            sm_info = "Found" if sm else "Missing"
            sv_info = "Found" if state_var else "Missing"
            print(f"[{device_name}] ❌ Error: StateMachine={sm_info}, CurrentState={sv_info}")

    except Exception as e:
        print(f"[{device_name}] ❌ Runtime Error: {e}")

def main():
    server_urls = {
        "Centrifuge": "opc.tcp://eugen:62452/Centrifuge",
        "Pipette": "opc.tcp://eugen:62453/Pipette",
        "RobotArm": "opc.tcp://eugen:62454/RobotArm"
    }

    connections = {}

    print("Starting connections to servers...")
    for name, url in server_urls.items():
        conn = lads.Connection(url=url)
        conn.connect()
        connections[name] = conn

    print("Waiting for all connections to be initialized...")
    for name, conn in connections.items():
        while not conn.initialized:
            time.sleep(1)
        print(f"[{name}] Connection initialized!")

    print("\n" + "=" * 40)
    print("      STARTING COMPLEX WORKFLOW")
    print("=" * 40)

    # --- Цепочка операций с ожиданием завершения ---

    # 1. RobotArm едет к точке А
    call_device_method_and_wait(connections["RobotArm"], "RobotArm", "MoveToA")

    # 2. Pipette начинает и заканчивает работу
    call_device_method_and_wait(connections["Pipette"], "Pipette", "StartPipetting")
    # Предполагаем, что StopPipetting возвращает в Idle
    call_device_method_and_wait(connections["Pipette"], "Pipette", "StopPipetting")

    # 3. RobotArm переносит образец в центрифугу
    call_device_method_and_wait(connections["RobotArm"], "RobotArm", "MoveToCentrifuge")

    # 4. Centrifuge выполняет цикл
    call_device_method_and_wait(connections["Centrifuge"], "Centrifuge", "StartSpinning")
    call_device_method_and_wait(connections["Centrifuge"], "Centrifuge", "StopSpinning")

    # 5. RobotArm забирает результат в точку Б
    call_device_method_and_wait(connections["RobotArm"], "RobotArm", "MoveToB")
    # Финальная остановка
    call_device_method_and_wait(connections["RobotArm"], "RobotArm", "MoveStop")

    print("\n" + "=" * 40)
    print("      WORKFLOW COMPLETED SUCCESSFULLY")
    print("=" * 40)

    for name, conn in connections.items():
        print(f"Disconnecting {name}...")
        conn.disconnect()


if __name__ == '__main__':
    main()