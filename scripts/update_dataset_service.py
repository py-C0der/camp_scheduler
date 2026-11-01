import re

with open('backend/services/dataset_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_csv_block = """        # Automatic CSV handling
        if isinstance(data, dict) and "_csv_raw" in data:
            from backend.services.csv_helper import parse_single_csv_string
            filename = data.get("_csv_filename", "rooms.csv")
            table_name = Path(filename).stem
            try:
                with open(DATA_PATH, "r", encoding="utf-8") as f:
                    base_data = json.load(f)
                parsed_items = parse_single_csv_string(data["_csv_raw"])
                base_data[table_name] = parsed_items
                base_data["dataset_id"] = f"cit-custom-{table_name}"
                data = base_data
            except Exception as e:
                errors.append(f"Failed to parse uploaded CSV: {str(e)}")"""

new_csv_block = """        # Automatic Multi-CSV or Single-CSV handling
        if isinstance(data, dict) and "_csv_files" in data:
            from backend.services.csv_helper import parse_single_csv_string
            try:
                with open(DATA_PATH, "r", encoding="utf-8") as f:
                    base_data = json.load(f)
                uploaded_names = []
                for fname, raw_txt in data["_csv_files"].items():
                    table_name = Path(fname).stem.strip()
                    uploaded_names.append(table_name)
                    parsed_items = parse_single_csv_string(raw_txt)
                    if table_name == "room_unavailability":
                        room_map = {r["id"]: r for r in base_data.get("rooms", []) if "id" in r}
                        for un in parsed_items:
                            rid = un.get("room_id")
                            if rid in room_map:
                                if "unavailable" not in room_map[rid]:
                                    room_map[rid]["unavailable"] = []
                                room_map[rid]["unavailable"].append({
                                    "day": un.get("day"),
                                    "periods": un.get("periods", []),
                                    "reason": un.get("reason", "Maintenance")
                                })
                    else:
                        base_data[table_name] = parsed_items
                names_tag = "-".join(uploaded_names[:3])
                base_data["dataset_id"] = f"cit-multi-csv-{names_tag}"
                data = base_data
            except Exception as e:
                errors.append(f"Failed to parse uploaded CSV files: {str(e)}")

        elif isinstance(data, dict) and "_csv_raw" in data:
            from backend.services.csv_helper import parse_single_csv_string
            filename = data.get("_csv_filename", "rooms.csv")
            table_name = Path(filename).stem
            try:
                with open(DATA_PATH, "r", encoding="utf-8") as f:
                    base_data = json.load(f)
                parsed_items = parse_single_csv_string(data["_csv_raw"])
                if table_name == "room_unavailability":
                    room_map = {r["id"]: r for r in base_data.get("rooms", []) if "id" in r}
                    for un in parsed_items:
                        rid = un.get("room_id")
                        if rid in room_map:
                            if "unavailable" not in room_map[rid]:
                                room_map[rid]["unavailable"] = []
                            room_map[rid]["unavailable"].append({
                                "day": un.get("day"),
                                "periods": un.get("periods", []),
                                "reason": un.get("reason", "Maintenance")
                            })
                else:
                    base_data[table_name] = parsed_items
                base_data["dataset_id"] = f"cit-custom-{table_name}"
                data = base_data
            except Exception as e:
                errors.append(f"Failed to parse uploaded CSV: {str(e)}")"""

old_import_csv_block = """        if isinstance(data, dict) and "_csv_raw" in data:
            from backend.services.csv_helper import parse_single_csv_string
            filename = data.get("_csv_filename", "rooms.csv")
            table_name = Path(filename).stem
            try:
                with open(DATA_PATH, "r", encoding="utf-8") as f:
                    base_data = json.load(f)
                parsed_items = parse_single_csv_string(data["_csv_raw"])
                base_data[table_name] = parsed_items
                base_data["dataset_id"] = f"cit-custom-{table_name}"
                data = base_data
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Failed to parse uploaded CSV: {str(e)}",
                    "errors": [str(e)],
                    "warnings": []
                }"""

new_import_csv_block = """        if isinstance(data, dict) and "_csv_files" in data:
            from backend.services.csv_helper import parse_single_csv_string
            try:
                with open(DATA_PATH, "r", encoding="utf-8") as f:
                    base_data = json.load(f)
                uploaded_names = []
                for fname, raw_txt in data["_csv_files"].items():
                    table_name = Path(fname).stem.strip()
                    uploaded_names.append(table_name)
                    parsed_items = parse_single_csv_string(raw_txt)
                    if table_name == "room_unavailability":
                        room_map = {r["id"]: r for r in base_data.get("rooms", []) if "id" in r}
                        for un in parsed_items:
                            rid = un.get("room_id")
                            if rid in room_map:
                                if "unavailable" not in room_map[rid]:
                                    room_map[rid]["unavailable"] = []
                                room_map[rid]["unavailable"].append({
                                    "day": un.get("day"),
                                    "periods": un.get("periods", []),
                                    "reason": un.get("reason", "Maintenance")
                                })
                    else:
                        base_data[table_name] = parsed_items
                names_tag = "-".join(uploaded_names[:3])
                base_data["dataset_id"] = f"cit-multi-csv-{names_tag}"
                data = base_data
            except Exception as e:
                return {"success": False, "message": f"Failed to parse uploaded CSV files: {str(e)}", "errors": [str(e)], "warnings": []}

        elif isinstance(data, dict) and "_csv_raw" in data:
            from backend.services.csv_helper import parse_single_csv_string
            filename = data.get("_csv_filename", "rooms.csv")
            table_name = Path(filename).stem
            try:
                with open(DATA_PATH, "r", encoding="utf-8") as f:
                    base_data = json.load(f)
                parsed_items = parse_single_csv_string(data["_csv_raw"])
                if table_name == "room_unavailability":
                    room_map = {r["id"]: r for r in base_data.get("rooms", []) if "id" in r}
                    for un in parsed_items:
                        rid = un.get("room_id")
                        if rid in room_map:
                            if "unavailable" not in room_map[rid]:
                                room_map[rid]["unavailable"] = []
                            room_map[rid]["unavailable"].append({
                                "day": un.get("day"),
                                "periods": un.get("periods", []),
                                "reason": un.get("reason", "Maintenance")
                            })
                else:
                    base_data[table_name] = parsed_items
                base_data["dataset_id"] = f"cit-custom-{table_name}"
                data = base_data
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Failed to parse uploaded CSV: {str(e)}",
                    "errors": [str(e)],
                    "warnings": []
                }"""

if old_csv_block in text:
    text = text.replace(old_csv_block, new_csv_block, 1)
else:
    print("Warning: old_csv_block not found directly, checking normalized...")
    # normalize newlines
    norm_text = text.replace("\r\n", "\n")
    norm_old = old_csv_block.replace("\r\n", "\n")
    if norm_old in norm_text:
        norm_text = norm_text.replace(norm_old, new_csv_block.replace("\r\n", "\n"), 1)
        text = norm_text.replace("\n", "\r\n")

if old_import_csv_block in text:
    text = text.replace(old_import_csv_block, new_import_csv_block, 1)
else:
    norm_text = text.replace("\r\n", "\n")
    norm_old = old_import_csv_block.replace("\r\n", "\n")
    if norm_old in norm_text:
        norm_text = norm_text.replace(norm_old, new_import_csv_block.replace("\r\n", "\n"), 1)
        text = norm_text.replace("\n", "\r\n")

with open('backend/services/dataset_service.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated backend/services/dataset_service.py")
