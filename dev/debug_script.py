from http import client
from asyncua import ua

import lads_opcua_client as lads
import time
import pandas as pd

def main():
    conn = lads.Connection(url="opc.tcp://eugen:62451/LabWorkflow")
    conn.connect()

    print("Waiting for connection to be initialized...")
    while not conn.initialized:
        time.sleep(1)
    print(f"Connection initialized: {conn.initialized}")

    server = conn.server

    # Идем по иерархии (Сервер -> Устройство -> Функциональный блок)
    devices = server.devices
    fu_list = devices[0].functional_units
    fun_unit = fu_list[0]
    var_list = devices[0].variables
    
    # Чтобы изменить значение переменной, нам нужно её найти.
    # В LADS переменная (например, SupervisoryJobId) может лежать либо в самом функциональном блоке,
    # либо внутри одной из его функций.
    try:
        target_i = 6018
        found_var = None

        # 1. Поищем сначала среди переменных самого FunctionalUnit
        if hasattr(fun_unit, "variables") and var_list:
            found_var = next((v for v in var_list if v.nodeid.Identifier == target_i), None)


        # 2. Применяем значение, если нашли
        if found_var:
            print(f"Found target variable: {found_var.display_name}, current value: {found_var.value}")
            # Изменяем значение
            print("Setting new value...")
            found_var.set_value("TestJob_999")
            time.sleep(1)
            print(f"New value expected to be requested. Observe if it changes.")
        else:
            print(f"Variable with NodeId {target_i} not found in this FunctionalUnit or its Functions.")

    except Exception as e:
        print(f"Error accessing functions/variables: {e}")

    # --------------------- ВЫЗОВ ОПЕРАЦИИ (Метода) ---------------------
    # Согласно стандарту LADS, методы типа Start или StartProgram
    # вызываются на уровне стейт-машины FunctionalUnit (или всего Device), а не отдельной функции.

    # 0. Let's inspect the dataclasses
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
            # 3. Вызов метода StartProgram (Сырой OPC UA вызов в обход библиотеки)

            # Получаем конструкторы для типов через asyncua uaclient (мы обращаемся к lower-level API)
            # В asyncua NodeId генерируется так: client.get_node(NodeId)
            # Если у нас уже есть созданные dataclass'ы в server.KeyValueType:

            # 1. properties
            prop_obj = server.KeyValueType(Key="MyKey", Value="MyValue")
            properties_list = [prop_obj]
            # ОБЯЗАТЕЛЬНО: упаковываем весь список как один вариант типа Array of ExtensionObject
            props_variant = ua.Variant(properties_list, ua.VariantType.ExtensionObject)

            # 2. samples
            sample_obj = server.SampleInfoType(ContainerId="Plate_1", SampleId="S_01", Position="A1", CustomData="")
            samples_list = [sample_obj]
            # ОБЯЗАТЕЛЬНО: упаковываем весь список как один вариант типа Array of ExtensionObject
            samples_variant = ua.Variant(samples_list, ua.VariantType.ExtensionObject)

            properties = ua.Variant([], ua.VariantType.ExtensionObject)
            samples = ua.Variant([], ua.VariantType.ExtensionObject)

            """# 3. Вызов. Передаем ровно 5 вариантов!
            fun_unit.functional_unit_state.call_async(
                fun_unit.functional_unit_state.call_lads_method(
                    "StartProgram",
                    properties,
                    ua.Variant("MyTestVariable1", ua.VariantType.String),
                    ua.Variant("MyTestVariable2", ua.VariantType.String),
                    samples,
                    ua.Variant("MyTestVariable3", ua.VariantType.String)
                )
            )
            """

            fun_unit.functional_unit_state.call_async(
                fun_unit.functional_unit_state.call_lads_method(
                    "StartProgram"
                )
            )

            print("Successfully called StartProgram via raw parameters!")

            # Wait for the async task to be evaluated
            time.sleep(1)

        except Exception as e:
            print(f"Error calling StartProgram: {e}")

    print("\nServer details: ")
    print(server.name)
    print("Number of devices: ", len(server.devices))
    for device in server.devices:
        print("  Device: ", device.unique_name)
    """
    functional_units = server.functional_units
    print("  Number of functional_units: ", len(functional_units))
    for fu in functional_units:
        print("    Name of functional_unit: ", fu.unique_name)
        print("    Other name of functional_unit: ", fu.at_name)
        functions = fu.functions
        print("    Number of functions: ", len(functions))
        for func in functions:
            print("      Name of function: ", func.unique_name)
            variables = func.variables
            print("      Number of variables: ", len(variables))
            for var in variables:
                print("        Name of variable: ", var.display_name)
                print("        Value of variable: ", var.value_str)
    """

    conn.disconnect()

if __name__ == '__main__':
    main()
