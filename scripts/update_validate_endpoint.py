with open("backend/api/dashboard_routes.py", "r", encoding="utf-8") as f:
    text = f.read()

# Add Request to fastapi import if needed
if "from fastapi import APIRouter," in text:
    text = text.replace("from fastapi import APIRouter,", "from fastapi import APIRouter, Request,")

old_func = """@dashboard_router.post("/api/admin/dataset/validate")
async def validate_dataset_upload(
    file: Optional[UploadFile] = File(None),
    payload: Optional[Dict[str, Any]] = Body(None)
):
    \"\"\"
    Validates uploaded JSON dataset for structural, schema, and relational integrity.
    Does not modify database records.
    \"\"\"
    data = None
    if file:
        content = await file.read()
        try:
            data = json.loads(content.decode("utf-8"))
        except Exception as ex:
            raise HTTPException(status_code=400, detail=f"Invalid JSON file format: {str(ex)}")
    elif payload:
        data = payload.get("dataset", payload)

    if not data or not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Missing or invalid dataset payload.")

    result = DatasetService.validate_dataset_structure(data)
    return result"""

new_func = """@dashboard_router.post("/api/admin/dataset/validate")
async def validate_dataset_upload(
    request: Request,
    file: Optional[UploadFile] = File(None)
):
    \"\"\"
    Validates uploaded JSON or CSV dataset for structural, schema, and relational integrity.
    Does not modify database records.
    \"\"\"
    data = None
    if file:
        content = await file.read()
        try:
            data = json.loads(content.decode("utf-8"))
        except Exception as ex:
            raise HTTPException(status_code=400, detail=f"Invalid JSON file format: {str(ex)}")
    else:
        try:
            body = await request.json()
            if isinstance(body, dict):
                data = body.get("dataset", body)
        except Exception:
            pass

    if not data or not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Missing or invalid dataset payload.")

    result = DatasetService.validate_dataset_structure(data)
    return result"""

norm_text = text.replace("\r\n", "\n")
norm_old = old_func.replace("\r\n", "\n")
assert norm_old in norm_text, "old_func not found"
norm_text = norm_text.replace(norm_old, new_func.replace("\r\n", "\n"), 1)

with open("backend/api/dashboard_routes.py", "w", encoding="utf-8") as f:
    f.write(norm_text.replace("\n", "\r\n"))

print("Updated backend/api/dashboard_routes.py successfully")
